# dsh-ontology（Python 平台）v0.2.2 对齐设计文档

> 版本：`v0.2.2`（拟） ｜ 对应需求：[spec.md](./spec.md) ｜ 对齐：Java `dsh-java-ontology` 0.2.2
>
> 本文件只写 Python 侧对齐增量设计；72 条 PLT 的完整架构见 `ai-pilot/poc/TASK-202611-001/design.md`（v0.3.1）。

---

## 1. 现状与差距

| 能力 | Java 0.2.2 | Python 现状 | 差距 |
|---|---|---|---|
| 七模型加载/注册表 | 有 | 无 | 需实现 |
| 完整性检查 | 有 | 无 | 需实现 |
| `/api/model/*` | 4 个 | 0 | 需新增 |
| `/api/ontology/discovered` | 1 个 | 0 | 需新增 |
| 写入 Schema 校验 | 服务层 | 无 | 需新增 |
| 晋升 9 类 + 名称列 | 有（待改造） | 无 | 需新增 |
| 匹配 9 类 | 有 | 无 | 需新增 |
| 响应 `{code,msg,data}` | 有 | `result.py` 已定义但未用于成功响应 | 需统一 |
| CORS | 产品层有效 | 无 | 需新增 |
| 测试 | 144（Java 双仓） | 0 | 需建立 |

## 2. 模块落位

```text
packages/base/src/dsh_onto_base/
├── config.py                 # 已有：新增模型/校验/CORS 配置项
├── result.py                 # 已有：ok/fail，统一包装复用
├── middleware.py             # 已有：追加响应包装与 CORS 装配
└── ontology/
    ├── __init__.py
    └── engine/
        ├── model.py          # ModelManifest / AggregateDescriptor / AttributeDescriptor
        ├── loader.py         # YAML 加载（SafeLoader）+ 裸块/重复 alias 检测
        ├── registry.py       # alias/category/tag 三索引，只读
        ├── integrity.py      # IntegrityReport / 悬空引用/空属性检查
        ├── catalog.py        # TypeCatalog：14 类 + 9 可晋升 + 名称列
        └── config.py         # 启动装配，失败即阻断

packages/flow/src/dsh_onto_flow/
├── model_router.py           # /api/model 4 端点
├── promotion.py              # 晋升服务（9 类 + 名称列 + 幂等）
├── match.py                  # 匹配服务（9 类）
└── ontology_router.py        # 追加 /api/ontology/discovered
```

## 3. 模型引擎

### 3.1 数据结构

| 类型 | 字段 |
|---|---|
| `ModelManifest` | `model_type/version/platform/base_models/projects/name/description` |
| `AggregateDescriptor` | `id/name/alias/category/domain/aggregate_type/lifecycle/tags/attributes/source_file/source_path` |
| `AttributeDescriptor` | `name/type/required/enum_values/description` |

### 3.2 加载

1. 读取 `packages/base` 资源目录下 `ontology-models/manifest.json` 与 7 个 YAML。
2. 项目层清单可选（`siis-models/manifest.json`），缺失不阻断。
3. `yaml.safe_load`；仅允许基础类型，禁止任意类反序列化。
4. 裸属性块（无实体头的 `- name: ...`）记录文件 + 行号；重复 alias 记录双方文件。
5. 加载顺序：基座 → 项目层；项目层同名 alias 报错，不静默覆盖。

### 3.3 注册表与完整性

- `OntologyRegistry`：`alias`/`category` 双索引 + `by_tag()`；全部返回副本或只读视图。
- `IntegrityChecker`：空属性、重复 alias、重复字段、枚举空值、M7/M2 悬空引用、基线计数。
- 报告为纯数据类，可序列化为 JSON；不含绝对路径。

### 3.4 启动装配

```python
# 伪代码
if settings.model_enabled:
    registry = ModelLoader(...).load()
    report = IntegrityChecker(registry).check()
    app.state.ontology_registry = registry
    app.state.integrity_report = report
```

失败抛 `ModelLoadError`，由 `create_app` 抛出终止启动；异常信息经 `result.fail` 转换后对外隐藏路径。

## 4. 模型 API（4 端点）

| 端点 | 实现 |
|---|---|
| `GET /api/model/manifest` | `ok(manifest.to_dict())` |
| `GET /api/model/aggregates` | 按 `domain` 分组，返回 `[{domain, aggregates:[...]}]` |
| `GET /api/model/aggregates/{alias}` | 未命中抛 404；命中返回明细 |
| `GET /api/model/integrity` | 返回启动缓存 `integrity_report.to_dict()` |

- 路由：`model_router = APIRouter(prefix="/api/model", dependencies=[Depends(require_role(1))])`。
- 不返回 `source_path`；只返回文件名。

## 5. Schema 校验

1. 从 `AggregateDescriptor.attributes` 生成 Pydantic 模型（缓存）。
2. 写入前调用 `validate_payload(category, payload, partial)`：
   - `create`：`partial=False`（必填校验）。
   - `update`：`partial=True`（只校验出现的字段）。
3. 错误聚合为 `List[FieldViolation]`，抛 `SchemaValidationError`，由异常处理器转为 400。
4. 开关：`DSH_ONTOLOGY_SCHEMA_VALIDATION_ENABLED`（默认 true）；关闭时直接返回空结果。
5. 未知字段：`warn` 写日志放行 / `reject` 返回 400。

挂载点：`OntologyService.create/update` 与 `ProjectTableRepository` 写入前；不侵入 SQLAlchemy 模型。

## 6. 晋升与匹配

### 6.1 类型目录

`TypeCatalog` 统一提供：

| 类型 | 数据源 | 表 | 名称列 | 可晋升 |
|---|---|---|---|---|
| country | siis | `gwy_ontology_country` | `name` | 是 |
| organization | siis | `gwy_ontology_organization` | `name` | 是 |
| person | siis | `gwy_ontology_person` | `name` | 是 |
| hotspot | siis | `gwy_ontology_hotspot` | `hotspot_name` | 是 |
| media | siis | `gwy_ontology_media` | `name` | 是 |
| book | siis | `gwy_ontology_book` | `title` | 是 |
| paper | siis | `gwy_ontology_paper` | `title` | 是 |
| term | onto | `onto_ontology_term` | `term_name` | 是 |
| location | onto | `onto_ontology_location` | `name` | 是 |
| bilateralRelation | siis | `gwy_ontology_bilateral_relation` | — | 否 |

### 6.2 晋升流程

```text
promote(discoveredEntityId, targetType)
  → 读 onto_common_discovered_entity
  → normalized = targetType or entity_type
  → 显式未知 → 400；bilateralRelation → 400
  → match(name, normalized)
      ├─ 命中：回写 ontology_entity_id，ALREADY_EXISTS
      └─ 未命中：按 TypeCatalog 取 (数据源, 表, 名称列)，写 {nameColumn: name}
  → UPDATE ... WHERE id=? AND status='DISCOVERED'
```

- 事务：同一 engine 内写目标表 + 回写状态；跨 engine 先写目标表再回写。
- 幂等：`ontology_entity_id` + `status='DISCOVERED'` 条件更新。
- 名称列由目录决定，禁止硬编码 `name`。

### 6.3 匹配

`match(name, type)`：按 `TypeCatalog` 取表与名称列；大小写、全半角归一；返回 `{id, _entity_type, _matched_column}`。

## 7. 响应包装

1. 在 `install_middlewares` 中新增 `ResponseEnvelopeMiddleware`。
2. 仅包装 `application/json` 且状态码 2xx 的响应；`/health`、`/api/*/health`、SSE、文件下载跳过。
3. 已含 `code/msg/data` 的响应不二次包装。
4. 异常路径继续使用现有 `HTTPException` 处理器。
5. 该中间件是唯一破坏性变更，需对 107 个端点做回归清单。

## 8. CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

- `DSH_CORS_ALLOWED_ORIGINS` 逗号分隔；空则不启用跨域。
- 禁止 `["*"]` + `allow_credentials=True`；启动时校验并抛错。

## 9. 配置新增

| 键 | 默认 | 说明 |
|---|---|---|
| `DSH_ONTOLOGY_MODEL_ENABLED` | `true` | 引擎启动开关 |
| `DSH_ONTOLOGY_SCHEMA_VALIDATION_ENABLED` | `true` | 写入校验开关 |
| `DSH_ONTOLOGY_UNKNOWN_FIELD_POLICY` | `warn` | `warn` / `reject` |
| `DSH_CORS_ALLOWED_ORIGINS` | 空 | 逗号分隔白名单 |
| `DSH_RESPONSE_ENVELOPE` | `true` | 统一包装开关 |

## 10. 测试设计

| 文件 | 覆盖 |
|---|---|
| `tests/test_engine.py` | 加载、坏 YAML、重复 alias、裸块、悬空引用 |
| `tests/test_model_api.py` | 4 端点、404、401/403 |
| `tests/test_validation.py` | 必填/类型/枚举/未知字段/开关 |
| `tests/test_promotion.py` | 9 类、名称列、未知类型、幂等 |
| `tests/test_discovered.py` | 参数、字段、排序、上限 |
| `tests/test_envelope.py` | JSON 包装、SSE/health 例外 |
| `tests/test_cors.py` | 白名单/非白名单 |

数据库不可用时用 mock/内存替身；不强依赖 MySQL。

## 11. 风险

| 风险 | 缓解 |
|---|---|
| 响应包装破坏既有前端 | 开关 `DSH_RESPONSE_ENVELOPE`，灰度开启；逐端点回归 |
| 引擎加载阻断启动 | 提供 `MODEL_ENABLED=false` 降级；坏 YAML 先修 |
| 跨数据源晋升不一致 | 先写目标表、后回写；幂等重试 |
| Python 与 Java 表数差异（37 vs 38） | 以 Java 迁移脚本为准，补齐差异表另立任务 |
