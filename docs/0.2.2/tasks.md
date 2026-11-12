# dsh-ontology（Python 平台）v0.2.2 对齐任务清单

> 版本：`v0.2.2`（拟） ｜ 对应需求：[spec.md](./spec.md) ｜ 对应设计：[design.md](./design.md)
>
> 状态：**待实施**（2026-11-08 未开始编码）。完成后勾选 `[x]`，并回写 [release-v0.2.2-development-notes.md](./release-v0.2.2-development-notes.md)。

---

## 任务总览

| 组 | 名称 | 任务数 | 前置 | 风险 |
|---|---|---|---|---|
| TP0 | 工程与配置前置 | 4 | 无 | 低 |
| TP1 | 模型引擎 | 8 | TP0 | 高 |
| TP2 | 模型 API | 4 | TP1 | 低 |
| TP3 | Schema 校验 | 5 | TP1 | 中 |
| TP4 | 晋升与匹配 | 6 | TP0 | 高 |
| TP5 | discovered 端点 | 3 | TP4 | 低 |
| TP6 | 响应包装与 CORS | 5 | TP0 | 高（兼容） |
| TP7 | 测试与契约 | 5 | TP1-TP6 | 中 |

**执行顺序**：TP0 → TP1 → TP2 → TP3 → TP4 → TP5 → TP6 → TP7。TP4 可与 TP1 并行；TP6 需在 TP2 前完成中间件骨架以复用。

**范围外**：M2-M5 元模型、OWL2 RL/SHACL、Qdrant/Redis/arq、19 张新增表、Alembic 基线、管理台页面。

---

## TP0 工程与配置前置（P0）

- [ ] **TP0.1 版本号统一**
  - 根 `pyproject.toml` 与 `apps/platform`、`packages/{base,flow,qa,viz,metric}` 的 `0.2.0` → `0.2.2`。
  - `Settings.version` 与 `__version__` 同步。
  - 验收：全仓库无 `0.2.0` 业务残留（`uv.lock` 除外）。

- [ ] **TP0.2 新增配置项**
  - `model_enabled`、`schema_validation_enabled`、`unknown_field_policy`、`cors_allowed_origins`、`response_envelope_enabled`。
  - 验收：环境变量可覆盖；默认值与 `spec.md` 一致。

- [ ] **TP0.3 测试脚手架**
  - 根 `pyproject.toml` 增加 `pytest`、`httpx`、`pytest-asyncio` 开发依赖；建立 `tests/`。
  - 验收：`uv run pytest` 可执行；空测试集返回 0。

- [ ] **TP0.4 模型资产归位**
  - 将七模型 YAML 与 `manifest.json` 放入 `packages/base/src/dsh_onto_base/resources/ontology-models/`（以 Java 0.2.2 为源）。
  - 验收：`importlib.resources` 可读取；不依赖文件系统绝对路径。

---

## TP1 模型引擎（P0）

- [ ] **TP1.1 数据模型**
  - `ModelManifest`、`AggregateDescriptor`、`AttributeDescriptor`（dataclass，集合只读）。
  - 验收：不可变；字段与 Java 0.2.2 对齐。

- [ ] **TP1.2 YAML 加载器**
  - `yaml.safe_load`；支持基座 + 项目层；裸块与重复 alias 检测。
  - 验收：坏 YAML 报文件 + 行号。

- [ ] **TP1.3 注册表**
  - `alias` / `category` 双索引 + `by_tag()`；未知键返回 `None`。
  - 验收：查询 O(1)。

- [ ] **TP1.4 完整性检查**
  - 空属性、重复字段、枚举空值、M7/M2 悬空引用、基线计数。
  - 验收：报告可 JSON 序列化。

- [ ] **TP1.5 类型目录**
  - 14 类常量；`promotable_types()`、`name_columns()`、`data_source()`。
  - 验收：9 类晋升、名称列与 DDL 一致。

- [ ] **TP1.6 启动装配**
  - `create_app` 中按开关加载；失败抛 `ModelLoadError`。
  - 验收：正常启动；坏模型阻断；`MODEL_ENABLED=false` 可降级。

- [ ] **TP1.7 异常类型**
  - `ModelLoadError` / `ModelIntegrityError`，携带文件与节点。
  - 验收：对外不泄露绝对路径。

- [ ] **TP1.8 引擎单测**
  - 覆盖成功、缺失、语法错误、重复 alias、裸块、悬空引用。
  - 验收：≥10 用例全绿。

---

## TP2 模型 API（P0）

- [ ] **TP2.1 路由骨架**
  - `model_router` 前缀 `/api/model`，`require_role(1)`。
  - 验收：未登录 401、角色不足 403。

- [ ] **TP2.2 manifest 与 aggregates**
  - 返回版本、平台、模型数、聚合根数；按域分组。
  - 验收：字段与 Java 一致。

- [ ] **TP2.3 单聚合根**
  - `GET /api/model/aggregates/{alias}`；未知 404。
  - 验收：不返回 `source_path`。

- [ ] **TP2.4 integrity**
  - 返回启动缓存报告。
  - 验收：无绝对路径、无堆栈。

---

## TP3 Schema 校验（P1）

- [ ] **TP3.1 校验器**
  - 由 `AggregateDescriptor` 生成校验规则；`partial` 支持。
  - 验收：必填/类型/枚举/未知字段四类用例。

- [ ] **TP3.2 字段错误结构**
  - `FieldViolation(field, rule, expected, actual, message)`。
  - 验收：可序列化。

- [ ] **TP3.3 挂载写入路径**
  - `OntologyService.create/update`；开关关闭时跳过。
  - 验收：既有行为不变。

- [ ] **TP3.4 异常映射**
  - `SchemaValidationError` → HTTP 400 + `{code,msg,data:[...]}`。
  - 验收：前端可渲染字段级错误。

- [ ] **TP3.5 日志与隐私**
  - 只记录 category/字段/规则；不记录完整 payload。
  - 验收：抽查无敏感值。

---

## TP4 晋升与匹配（P0）

- [ ] **TP4.1 晋升服务**
  - 新增 `promotion.py`；读 `onto_common_discovered_entity`。
  - 验收：不存在返回 400。

- [ ] **TP4.2 9 类路由**
  - 按 `TypeCatalog` 取数据源/表/名称列。
  - 验收：hotspot/book/paper 分别写 `hotspot_name`/`title`。

- [ ] **TP4.3 未知类型与排除项**
  - 显式未知 → 400；`bilateralRelation` → 400；空目标兼容 → `onto_ontology_entity`。
  - 验收：三分支有测试。

- [ ] **TP4.4 事务与幂等**
  - `UPDATE ... WHERE id=? AND status='DISCOVERED'`。
  - 验收：重复调用无重复实体。

- [ ] **TP4.5 匹配服务**
  - `match()` 覆盖 9 类；与晋升共用目录。
  - 验收：预览与晋升口径一致。

- [ ] **TP4.6 单测**
  - 9 类、特殊名称列、未知类型、空目标、幂等、匹配。
  - 验收：≥10 用例。

---

## TP5 discovered 端点（P1）

- [ ] **TP5.1 新增端点**
  - `GET /api/ontology/discovered?status=DISCOVERED&limit=20`，`require_role(1)`。
  - 验收：参数与 Java 一致。

- [ ] **TP5.2 字段白名单**
  - `id/entityName/entityType/mentionCount/status/createdAt`；`limit` 上限 100。
  - 验收：不暴露内部字段。

- [ ] **TP5.3 排序与过滤**
  - `del_flag=0`，`updated_at DESC`。
  - 验收：与晋升工作台一致。

---

## TP6 响应包装与 CORS（P1）

- [ ] **TP6.1 包装中间件**
  - 仅 JSON 2xx；已有 `code/msg/data` 不重复包装。
  - 验收：单测覆盖。

- [ ] **TP6.2 例外路径**
  - `/health`、`/api/*/health`、SSE、文件下载不包装。
  - 验收：SSE 流不被缓冲。

- [ ] **TP6.3 107 端点回归**
  - 逐路由记录包装前后结构差异；前端可见变化写入说明。
  - 验收：无遗漏、无二次包装。

- [ ] **TP6.4 CORS 装配**
  - `CORSMiddleware` + 白名单；启动校验禁止 `*` + 凭据。
  - 验收：预检 200。

- [ ] **TP6.5 开关与回滚**
  - `DSH_RESPONSE_ENVELOPE=false` 可恢复原始响应。
  - 验收：灰度可控。

---

## TP7 测试与契约（P0）

- [ ] **TP7.1 端到端测试**
  - httpx ASGI 进程内调用 4 模型端点 + discovered + 晋升。
  - 验收：不依赖真实 MySQL。

- [ ] **TP7.2 用例总数**
  - 全仓 ≥ 60 用例。
  - 验收：`uv run pytest` 全绿。

- [ ] **TP7.3 契约基线**
  - 生成 Python 侧 OpenAPI 片段，落盘 `ai-pilot/contract/openapi-baseline.yaml`（与 Java 合并）。
  - 验收：5 端点字段/错误码一致。

- [ ] **TP7.4 双栈 diff**
  - 与 Java 0.2.2 做路径/字段/错误码 diff。
  - 验收：无 breaking 差异。

- [ ] **TP7.5 文档同步**
  - 更新 `ai-pilot/poc/TASK-202611-001/design.md` 的 Python 侧实现状态。
  - 验收：状态与代码一致。

---

## 完成标准

1. 引擎可加载、可查询、可诊断；坏模型阻断启动。
2. 4 个模型端点 + 1 个 discovered 端点与 Java 0.2.2 一致。
3. 9 类晋升、名称列、未知类型分支全部可用。
4. Schema 校验可开关，错误字段级可读。
5. 响应包装与 CORS 生效且可回滚。
6. pytest ≥ 60 全绿；契约基线含 5 端点；版本 0.2.2。
