# dsh-ontology（Python 平台）v0.2.2 对齐需求规格

> 版本：`v0.2.2`（拟，当前 `0.2.0`） ｜ 对齐：Java `dsh-java-ontology` 0.2.2 ｜ 归属：`dsh-ontology`
>
> 目录名 `0.2.2` 指**对齐的 Java 里程碑**；本仓包版本按自身节奏推进至 `0.2.2`。
>
> 本文件定义 Python 产品层基座对 Java 0.2.2 的**对齐增量**，不重复 ai-pilot 的 72 条 PLT 全量需求。产品层需求基线见 `ai-pilot/poc/TASK-202611-001/01-平台层需求规格.md`，Python 架构见 `ai-pilot/poc/TASK-202611-001/design.md`（v0.3.1）。

---

## 1. 定位

1. `dsh-ontology` 是 Python 产品层基座，与 `dsh-java-ontology` 同契约、同表结构、不同技术栈。
2. Java 0.2.2 的能力（静态本体引擎化、模型元数据 API、晋升 9 类）在 Python 侧**尚未实现**；本版本补齐与 Java 0.2.2 对等的 D0 能力。
3. Python 独有、Java 0.2.2 不包含的能力（OWL2 RL/SHACL、Qdrant、19 张新增表）**不在本版本**。

## 2. 基线事实（实测）

| 项 | 事实 |
|---|---|
| 仓库版本 | `0.2.0`（根与 5 个包一致） |
| 应用端口 | 8093（`dsh_onto_base/config.py`，`DSH_PLATFORM_PORT`） |
| 包结构 | `packages/base`、`flow`、`qa`、`viz`、`metric` + `apps/platform` |
| 数据库 | 双引擎 `dsh_java_siisdb` + `dsh_java_ontodb`，延迟创建 |
| 表模型 | 37 张 SQLAlchemy `__tablename__` |
| HTTP 端点 | 107 个（base/flow/sys/metric/qa/viz/ontologies） |
| 模型引擎 | 无 YAML 加载器、无注册表、无完整性检查 |
| 模型 API | 无 `/api/model/*` |
| 晋升 / 匹配 | 无 `promote`；无 `/api/ontology/match`、无 `/api/ontology/discovered` |
| 响应包装 | 仅异常处理为 `{code,msg,data}`，成功响应为裸结构 |
| CORS | 未配置（仅租户/身份中间件） |
| 迁移 | 无 Alembic |
| 测试 | 0 个 pytest 文件 |

## 3. 对齐需求

### P-01（Ubiquitous）静态本体模型引擎

系统应加载基座与项目层七模型 YAML，构建运行时注册表，并输出完整性报告：

- 清单：`ontology-models/manifest.json`；YAML 类型 M1/M2/M3/M5/M6/M7/MU。
- 能力：按 `alias`、`category`、`tag` 查询聚合根；检测重复 alias、裸属性块、悬空引用、空属性。
- 失败策略：启动即加载，坏模型阻断启动（`DSH_ONTOLOGY_MODEL_ENABLED=true` 时）。

### P-02（Ubiquitous）模型元数据 API（4 个）

系统应提供与 Java 0.2.2 同路径、同结构的只读端点：

| 端点 | 要求 |
|---|---|
| `GET /api/model/manifest` | 返回模型版本、平台、模型数、聚合根数 |
| `GET /api/model/aggregates` | 按域分组返回聚合根摘要 |
| `GET /api/model/aggregates/{alias}` | 未知 alias 返回 404 |
| `GET /api/model/integrity` | 返回启动期完整性报告；不含绝对路径、堆栈、YAML 原文 |

鉴权：`require_role(1)`（研究员及以上）。

### P-03（Event-driven）发现实体只读端点

系统应提供 `GET /api/ontology/discovered?status=DISCOVERED&limit=20`，与 Java 0.2.2 参数、字段、排序一致；`limit` 上限 100。

### P-04（Ubiquitous）写入 Schema 校验

系统应在创建/更新本体实体前，按 YAML 字段定义校验必填、类型、枚举与未知字段：

- 校验失败返回 HTTP 400 + `{code:400,msg,data:[FieldViolation]}`。
- 未知字段策略由 `DSH_ONTOLOGY_UNKNOWN_FIELD_POLICY=warn|reject` 控制，默认 `warn`。
- 关闭开关 `DSH_ONTOLOGY_SCHEMA_VALIDATION_ENABLED=false` 时行为与既有完全一致。

### P-05（Ubiquitous）晋升 9 类

系统应支持 9 类晋升目标，并按目标表名称列写入：

| 类型 | 目标表 | 名称列 |
|---|---|---|
| country / organization / person / media / location | `onto_ontology_*` / 对应业务表 | `name` |
| hotspot | `gwy_ontology_hotspot`（SIIS 数据源） | `hotspot_name` |
| book / paper | `gwy_ontology_book` / `gwy_ontology_paper` | `title` |
| term | `onto_ontology_term` | `term_name` |

- `bilateralRelation` 不可晋升，返回 400。
- 显式未知类型返回 400；空目标 + 非 9 类按兼容分支落 `onto_ontology_entity`。

> 说明：Python 平台与 Java 平台一致，晋升落库目标是“共享层/项目层本体表”，因此 hotspot/book/paper 走 `gwy_*` 数据源。平台与项目层各自部署，共用 `TypeCatalog` 与路由算法，不要求跨进程调用。

### P-06（Ubiquitous）匹配映射一致

匹配预览与晋升共用同一类型目录：9 类、同一名称列、同一数据源；大小写归一一致。

### P-07（Ubiquitous）统一响应包装

系统应对 JSON 响应统一为 `{code, msg, data}`：

- 成功 `code=200`。
- 例外：`/health`、`/api/*/health`、SSE（`text/event-stream`）、文件下载不包装。
- 该变更需逐端点回归，避免破坏 107 个既有端点。

### P-08（Ubiquitous）CORS

系统应支持前端跨域：允许来源由 `DSH_CORS_ALLOWED_ORIGINS` 注入；方法 GET/POST/PUT/DELETE/OPTIONS；头 `Authorization`、`Content-Type`；禁止 `*` + 凭据组合。

### P-09（Ubiquitous）测试基线

系统应建立 pytest + httpx 基线：

- 覆盖引擎加载、4 个模型端点、discovered、Schema 校验、晋升 9 类、响应包装、CORS。
- 目标：新增用例 ≥ 60，全部通过；不引入数据库强依赖（用 SQLite/内存或 mock）。

### P-10（Ubiquitous）版本与契约基线

- 版本 `0.2.0` → `0.2.2`（根与 5 个包同步）。
- 生成/维护 `ai-pilot/contract/openapi-baseline.yaml` 的 Python 侧片段，5 个新增端点进基线。
- 与 Java 0.2.2 做字段级 diff。

### P-11（Ubiquitous）不新增表

v0.2.2 对齐期不改表结构；Python 新增 19 表属 M2-M4，不在本版本。

## 4. DFX 约束

| 维度 | 约束 |
|---|---|
| 性能 | 引擎启动加载 ≤ 2s（本地 SSD）；模型 API P95 ≤ 100ms（内存注册表） |
| 安全 | 模型 API 不返回绝对路径、堆栈、YAML 原文；CORS 不通配凭据 |
| 兼容 | 既有 107 端点路径不变；响应包装为唯一显式破坏性变更，需全量回归 |
| 依赖 | 复用 FastAPI/Pydantic/SQLAlchemy；不引入图数据库、规则引擎或新前端框架 |

## 5. 验收标准

| 编号 | 验收 |
|---|---|
| AC-1 | 七模型加载成功；坏 YAML 启动失败并给出文件/节点 |
| AC-2 | 4 个 `/api/model/*` 端点字段与 Java 0.2.2 一致；未知 alias 404 |
| AC-3 | `GET /api/ontology/discovered` 参数/字段/排序与 Java 一致 |
| AC-4 | 非法写入返回 400 + 字段级 `data` |
| AC-5 | 9 类晋升成功；hotspot/book/paper 写 `hotspot_name`/`title` |
| AC-6 | 显式未知类型 400；空目标兼容分支有覆盖 |
| AC-7 | JSON 响应统一 `{code,msg,data}`；SSE/health 例外 |
| AC-8 | CORS 白名单生效 |
| AC-9 | pytest ≥ 60 用例全绿 |
| AC-10 | 版本 0.2.2；契约基线含 5 端点 |

## 6. 范围外

- M2 行为、M3 规则、M4 场景、M5 权限元模型。
- OWL2 RL 序列化、SHACL 校验、Qdrant 向量检索、Redis、arq。
- 19 张新增表与 Alembic 基线迁移。
- 管理台页面（由 Java 侧承载）。
