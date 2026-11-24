# dsh-ontology（Python 平台）v0.2.3 问数（QA）设计文档

> 版本：`v0.2.3`（拟） ｜ 状态：**设计输入（待评审，未实施）** ｜ 归属：`dsh-ontology`
>
> 本文件把 `packages/qa` 从「问数记录持久化」推进为「可执行的问数链路」，并吸收 Gitee 项目 `weedlu/tangdou-data`（糖豆）的工程化设计。
>
> 原则：**采纳工程护栏，不采纳框架绑定**。糖豆基于 LangChain/LangGraph；本设计保持框架无关，只复用其链路与治理模式。

---

## 1. 背景与现状

### 1.1 定位

`packages/qa` 是 dsh-ontology 的问数（NL2SQL）与报告包。当前只提供会话/查询记录与报告 CRUD：

| 能力 | 现状 | 文件 |
|---|---|---|
| 问数会话 | 可创建/查询，默认 `ACTIVE` | [service.py](../../packages/qa/src/dsh_onto_qa/service.py) |
| 问数查询记录 | 可创建/查询，默认 `PENDING` | [service.py](../../packages/qa/src/dsh_onto_qa/service.py) |
| 结果字段 | `translated_sql` / `result_data` / `chart_suggestion` / `process_status` | [models.py](../../packages/qa/src/dsh_onto_qa/models.py) |
| HTTP 端点 | `POST/GET /api/report/qa/sessions`、`.../queries` | [router.py](../../packages/qa/src/dsh_onto_qa/router.py) |
| NL2SQL 引擎 | **无** | — |
| 本体参与 | **无** | — |
| SQL 校验/执行 | **无** | — |
| 图表生成 | **无**（仅字段占位） | — |

### 1.2 参考对象

`tangdou-data` 的链路为：SSE 入口 → 本体规则拼 system prompt → Agent 调 SQL 工具 → 结果落库 + 图表 → 流式返回。

可借鉴的是其中的**工程护栏**：本体提示词编译与热重载、按轮上下文裁剪、显式 token 预算、SQL 只读校验、结果真实性约束、图表兜底、SSE 事件协议。

不可照搬的是：LangChain/LangGraph 绑定、本体全量静态塞入提示词、删除 schema 工具后靠报错猜字段、校验与执行分离导致 SQL 跑两遍。

---

## 2. 目标与非目标

### 2.1 目标

1. 建立「问题 → 计划 → SQL → 校验 → 执行 → 结果/图表」的最小闭环，结果写入现有 `ReportQaQuery`。
2. 本体（表、字段、关系、业务规则）参与 SQL 生成，且支持规则热重载。
3. SQL 只读、单条、可限制行数、可超时、可取消；**所有执行走同一入口**。
4. 数据库结果是唯一事实来源，禁止模型改写/编造结果。
5. 通过 SSE 分事件输出 `status / thinking / sql / data / result / done`。
6. 建立可评测基线：golden set + 执行成功率 + 结果一致率。

### 2.2 非目标

- 不引入 LangChain/LangGraph 作为运行时依赖。
- 不做跨库联邦查询、复杂多轮 SQL 事务。
- 不做行级数据权限（本版本只做租户 + 会话归属校验）。
- 不做文本到图表的端到端训练模型。
- 不新增数据库表；仅使用现有字段与 JSON 结构（必要时在 0.2.4 再做 DDL）。

---

## 3. 待明确需求（采纳候选）

> 以下条目来自 `tangdou-data` 的可借鉴设计，先作为**待明确需求**登记。每条给出「采纳理由 / 待明确点 / 建议默认值」，评审后再进入实施。

### D1 本体参与方式：静态全量提示词 vs 按问题检索

- **采纳理由**：糖豆把 `ontology/*.md` 全量拼入 system prompt，实现简单、规则生效直接；但固定 token 成本高，多库时不可扩展。
- **待明确点**：本版本是否必须做 schema linking？检索用关键词/别名，还是向量？
- **建议默认**：混合模式。先按问题命中**域/主题**，再取该域的表、字段、关系与规则；未命中时回退全量精简清单。检索先用「别名 + 中文名 + 关键词」，不引入向量库。
- **影响面**：`OntologyPromptCompiler`、`SchemaLinker`、token 预算。

### D2 本体规则的版本与热重载

- **采纳理由**：糖豆用文件 mtime + 5s TTL 检查，规则改动无需重启；对本项目「本体经常调整」的现状很实用。
- **待明确点**：规则来源是文件、数据库，还是两者合并？版本号如何暴露给前端/评测？
- **建议默认**：以数据库本体为事实源，渲染为内存快照；`DSH_QA_ONTOLOGY_TTL_SECONDS=5`，用 `updated_at`/mtime 判定失效；快照带 `ontology_version`，写入查询记录便于回溯。
- **影响面**：`OntologyPromptCompiler`、`ReportQaSession.context`。

### D3 数据源与只读账号

- **采纳理由**：问数必须默认只读；糖豆的 `sqlglot` AST 校验方向正确。
- **待明确点**：本版本接哪些数据源（演示库/业务库）？是否必须独立只读账号？
- **建议默认**：单数据源起步；连接串单独配置 `DSH_QA_DATASOURCE_URL`，要求只读账号；本地开发允许 SQLite/只读副本。
- **影响面**：`SqlExecutor`、配置、部署文档。

### D4 SQL 方言与校验依赖

- **采纳理由**：AST 级校验比关键字黑名单可靠；糖豆用 `sqlglot` 实现单条 SELECT/UNION、拒绝写操作、自动 LIMIT。
- **待明确点**：是否接受新增 `sqlglot` 依赖？需要支持 MySQL/PostgreSQL/SQLite 哪些方言？
- **建议默认**：引入 `sqlglot`；按数据源方言解析；只允许 `SELECT`/`UNION`/`WITH`，禁止多语句、DDL/DML、`INTO OUTFILE`。
- **影响面**：`SqlGuard`、依赖清单。

### D5 结果集契约与截断

- **采纳理由**：糖豆自动 `LIMIT 1000`，并把真实结果作为唯一数据来源；但 `result_data` 若直接换结构会影响既有前端。
- **待明确点**：`result_data` 用裸行数组还是带 `columns/rows/row_count/truncated` 的信封？上限多少行？
- **建议默认**：使用带 `schema_version` 的信封；执行上限 1000 行，返回上限 200 行，超出标记 `truncated=true`；保留旧裸数组的读取兼容。
- **影响面**：`ReportQaQuery.result_data`、前端契约、测试。

### D6 查询状态机

- **采纳理由**：现有 `process_status` 只有 `PENDING`，无法表达规划/执行/失败；糖豆用流式事件 + 落库状态。
- **待明确点**：状态枚举是否与 Java 侧统一？失败是否区分「生成失败 / 校验失败 / 执行失败」？
- **建议默认**：`PENDING → PLANNING → SQL_READY → EXECUTING → SUCCEEDED / FAILED / CANCELLED`；失败原因写入 `result_data.error{code,message,stage}`；未知旧值按 `PENDING` 处理。
- **影响面**：`QaStateMachine`、`service.py`、前端轮询/SSE。

### D7 图表契约

- **采纳理由**：糖豆的「显式指定 → LLM 意图 → 关键词 → 结构兜底」和「饼图失败退表格」能显著降低空图率。
- **待明确点**：`chart_suggestion` 存 ECharts option，还是只存 `{type, mapping}` 由前端生成？
- **建议默认**：存 `{type, title, x_field, y_fields, series, option?, reason}`；`option` 可选，前端优先用结构化字段生成，失败再退表格。
- **影响面**：`ChartPlanner`、`chart_suggestion`、前端渲染。

### D8 流式协议

- **采纳理由**：糖豆按 `status/thinking/sql/data/result/done` 分事件推送，SQL、推理、数据、答案解耦，前端可分别渲染，且便于断连取消。
- **待明确点**：复用现有轮询接口还是新增 SSE？SSE 与既有 `{code,msg,data}` 包装如何共存？
- **建议默认**：新增 `GET /api/report/qa/queries/{queryId}/stream`；SSE 事件不套响应包装；保留轮询接口作为降级。
- **影响面**：`router.py`、`events.py`、前端。

### D9 上下文与 token 预算

- **采纳理由**：糖豆按「整轮删除 + 保留 tool_call/result 配对 + 超长工具消息原位截断」控制历史，并显式扣除 system/tools/回复预留。
- **待明确点**：本版本是否支持多轮追问？模型上下文窗口与预留值如何配置？
- **建议默认**：支持多轮；`DSH_QA_CONTEXT_WINDOW`、`DSH_QA_REPLY_RESERVE`、`DSH_QA_MIN_HISTORY_TOKENS` 可配；无摘要，超限时整轮裁剪并给出友好提示。
- **影响面**：`ContextBudget`、会话上下文存储。

### D10 权限与租户隔离

- **采纳理由**：糖豆做 JWT + 会话归属校验，但无行级权限。
- **待明确点**：是否需要按本体域/数据源授权？是否需要 SQL 结果脱敏？
- **建议默认**：本版本只做租户 + 会话归属 + 角色校验；行级权限与脱敏列入 0.2.4。
- **影响面**：`router.py` 依赖、`SqlExecutor` 会话变量。

### D11 评测集与指标

- **采纳理由**：问数系统必须可回归；糖豆有提示词约束但缺系统评测。
- **待明确点**：golden set 由谁维护？指标口径？
- **建议默认**：30–50 条覆盖单表/多表/聚合/时间/比率的问题；指标为执行成功率、结果一致率、图表有效率、P95 延迟；评测脚本放 `packages/qa/tests/eval/`。
- **影响面**：测试基线、CI。

### D12 是否引入 Agent 框架

- **采纳理由**：糖豆用 `create_react_agent` 快速成型，但带来框架生命周期、checkpoint、版本升级成本。
- **待明确点**：本版本是否需要多步自主规划，还是一次计划 + 允许一次修复？
- **建议默认**：**不引入框架**。用显式阶段编排；最多一次「校验/执行失败 → 修正 SQL」重试；总工具调用上限 6 次。
- **影响面**：`pipeline.py`、依赖、可观测性。

---

## 4. 总体设计

### 4.1 链路

```text
POST /queries
  → 创建 ReportQaQuery(PENDING)
  → SSE 订阅 /stream
  → 状态机推进
      1) 意图判定：数据查询 / 元数据 / 上下文 / 闲聊
      2) OntologyPromptCompiler：取本体快照 → 规则 + 精简 schema
      3) SchemaLinker：问题 → 候选域/表/字段/指标
      4) Planner：生成 SQL 计划（单条 SQL + 解释）
      5) SqlGuard：AST 校验、只读、单条、自动 LIMIT
      6) SqlExecutor：只读连接执行、超时、取消
      7) ResultBuilder：DB 结果 → columns/rows/row_count/truncated
      8) ChartPlanner：显式 > 意图 > 规则 > 表格兜底
      9) 落库：translated_sql/result_data/chart_suggestion/process_status
     10) SSE：result + done
```

### 4.2 关键原则

1. **单一执行入口**：校验与执行必须在同一服务内串联，禁止出现「校验过的 SQL 与实际执行的 SQL 不是同一条」。
2. **结果只读**：连接层只读账号 + AST 只读双保险。
3. **结果即事实**：模型只负责生成 SQL/解释；行数据只能来自数据库。
4. **可回退**：任何阶段失败都落 `FAILED` 并带阶段与错误码，不吞异常。
5. **可观测**：每个阶段记录耗时、token、SQL 指纹、重试次数。

---

## 5. 模块落位

```text
packages/qa/src/dsh_onto_qa/
├── router.py                 # 既有 CRUD；新增 stream/cancel
├── service.py                # 会话/查询编排；调用 pipeline
├── models.py                 # 既有 ORM（本版本不改表）
├── schemas.py                # 请求/响应；新增 QueryOptions / QaEvent
├── repository.py             # 既有查询
└── qa/
    ├── __init__.py
    ├── pipeline.py           # QaPipeline：阶段编排与重试
    ├── state.py              # QaStateMachine
    ├── prompt.py             # OntologyPromptCompiler（快照 + TTL）
    ├── linker.py             # SchemaLinker（域/表/字段/指标）
    ├── planner.py            # SqlPlanner（LLM 调用与输出解析）
    ├── guard.py              # SqlGuard（sqlglot AST）
    ├── executor.py           # SqlExecutor（只读、超时、取消）
    ├── result.py             # ResultBuilder（信封、截断、错误结构）
    ├── chart.py              # ChartPlanner
    ├── context.py            # ContextBudget（预算/整轮裁剪）
    └── events.py             # SSE 事件模型与序列化
```

配置：复用 `dsh_onto_base/config.py` 模式，新增 `DSH_QA_*` 环境变量。

---

## 6. 关键设计

### 6.1 OntologyPromptCompiler

输入：`ontology_snapshot`（表、字段、关系、业务规则、指标口径）。

输出：结构化提示词片段：

```text
[本体版本] v2026-11-16
[可用域] 区域 / 部门 / 人员 / 事件
[表] dept(id, name, parent_id, ...)
[关系] dept.id = person.dept_id
[业务规则] 区/部门统计直接使用 DEPT_ID_TEXT，无需 join SYS_DEPT
[指标] 活跃人员数 = count(distinct person.id) where status='ACTIVE'
```

- 规则来源：数据库本体；渲染后缓存为不可变快照。
- 失效：`DSH_QA_ONTOLOGY_TTL_SECONDS`（默认 5s）+ 版本号变化。
- 禁止把绝对路径、连接串、样例数据写入提示词。

### 6.2 SchemaLinker

- 输入：问题、本体快照。
- 步骤：别名/中文名匹配 → 域过滤 → 关系扩展一跳 → 输出候选表/字段。
- 未命中：回退到「精简全量表清单」并提示模型先选表。
- 输出：`LinkedSchema{tables, columns, relations, metrics, confidence}`。
- 本版本不引入向量检索；保留接口以便 0.2.4 切换。

### 6.3 SqlGuard

1. `sqlglot.parse`，必须恰好 1 条语句。
2. 根节点仅允许 `Select` / `Union` / `With`；遍历 AST 拒绝 `Insert/Update/Delete/Create/Drop/Alter/Command`。
3. 禁止 `INTO OUTFILE`、`LOAD_FILE`、多语句分隔符。
4. 自动补 `LIMIT`（默认 1000）；已有更小 LIMIT 时保留。
5. 输出规范化 SQL（用于执行与指纹），并返回警告列表。

### 6.4 SqlExecutor

- 只读连接；`SET TRANSACTION READ ONLY`（支持时）。
- 超时：`DSH_QA_SQL_TIMEOUT_SECONDS`（默认 15s）；取消：查询级 `cancel_event`。
- 返回：`columns`、`rows`（最多 200 行）、`row_count`、`truncated`、`elapsed_ms`。
- 异常归一：`SQL_SYNTAX` / `SQL_TIMEOUT` / `SQL_PERMISSION` / `SQL_EXECUTION`。
- **不重试执行**；仅在语法/字段错误时允许一次「修正 SQL → 重新校验 → 再执行」。

### 6.5 ResultBuilder 与真实性约束

- `result_data` 使用信封：

```json
{
  "schema_version": "1",
  "columns": [{"name": "dept", "type": "string"}],
  "rows": [["A 区", 12]],
  "row_count": 1,
  "truncated": false,
  "error": null
}
```

- 提示词硬约束：只能引用工具返回的行；禁止补全、四舍五入到未给出的精度、编造行数。
- 校验：若模型回答中的数值/行数与结果明显不一致，降级为「仅展示表格 + 摘要」。

### 6.6 ChartPlanner

优先级：

1. 请求显式 `chart.type`。
2. LLM 图表意图（仅一次，失败不重试）。
3. 结构规则：1 行 1 数值 → 指标卡；1 维度 + 1 数值 → 柱/折线；时间维度 → 折线；占比且和为 100 → 饼图。
4. 兜底 `table`。

- 输出 `chart_suggestion`；`has_chart_done` 防止重复。
- 一轮结束仍未出图则自动兜底一次。

### 6.7 ContextBudget

- 预算：`min(DSH_QA_SESSION_MAX_TOKENS, window - system - tools - reply_reserve)`，下限 `DSH_QA_MIN_HISTORY_TOKENS`。
- 裁剪：从最早一轮开始整轮删除；保留最近 1 轮；保留 `tool_call/tool_result` 配对。
- 超长工具消息：按原 id 原位截断到 1/4，并加 `[truncated]` 标记。
- 不做 LLM 摘要；超限给用户「请开启新会话」提示。

### 6.8 状态机与落库

| 状态 | 进入条件 | 落库字段 |
|---|---|---|
| `PENDING` | 创建查询 | `process_status` |
| `PLANNING` | 开始意图/链接/生成 | 同上 |
| `SQL_READY` | 校验通过 | `translated_sql` |
| `EXECUTING` | 开始执行 | 同上 |
| `SUCCEEDED` | 执行 + 图表完成 | `result_data` / `chart_suggestion` |
| `FAILED` | 任一阶段异常 | `result_data.error` |
| `CANCELLED` | 客户端断开/取消 | 同上 |

- 状态推进只允许前向；终态不可回退。
- 会话 `context` 记录 `ontology_version`、`last_query_id`、`schema_link` 摘要。

### 6.9 SSE 事件

| 事件 | 载荷 |
|---|---|
| `status` | `{stage, message}` |
| `thinking` | `{text}`（可省略） |
| `sql` | `{sql, dialect, warnings}` |
| `data` | `{columns, rows, row_count, truncated}` |
| `result` | `{answer, chart_suggestion}` |
| `done` | `{query_id, status}` |
| `error` | `{code, message, stage}` |

- SSE 不套 `{code,msg,data}`。
- 客户端断开触发 `cancel_event`，状态置 `CANCELLED`。

---

## 7. 接口设计

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/report/qa/sessions` | 既有：创建会话 |
| `POST` | `/api/report/qa/sessions/{sessionId}/queries` | 既有：创建查询，返回 `query_id` |
| `GET` | `/api/report/qa/sessions/{sessionId}/queries` | 既有：查询列表 |
| `GET` | `/api/report/qa/queries/{queryId}/stream` | **新增**：SSE 执行并推送 |
| `GET` | `/api/report/qa/queries/{queryId}` | **新增**：查询最终状态 |
| `POST` | `/api/report/qa/queries/{queryId}/cancel` | **新增**：取消执行 |

鉴权：沿用现有依赖；新增端点必须校验租户与会话归属。

---

## 8. 数据模型与兼容

- **不新增表**；复用 `ReportQaSession`、`ReportQaQuery`。
- `result_data` 由「裸行数组」升级为信封；读取侧兼容旧结构。
- `chart_suggestion` 由自由 JSON 规范为 `{type, title, x_field, y_fields, series, option?, reason}`。
- `process_status` 扩展枚举；旧值按 `PENDING`/兼容处理。
- 若后续需要 `intent`、`plan`、`ontology_version` 独立列，列入 0.2.4 DDL 计划。

---

## 9. 配置项

| 变量 | 默认 | 说明 |
|---|---|---|
| `DSH_QA_ENABLED` | `false` | 问数链路开关 |
| `DSH_QA_DATASOURCE_URL` | — | 只读数据源 |
| `DSH_QA_ONTOLOGY_TTL_SECONDS` | `5` | 本体快照 TTL |
| `DSH_QA_SQL_TIMEOUT_SECONDS` | `15` | SQL 超时 |
| `DSH_QA_MAX_ROWS` | `1000` | 执行 LIMIT 上限 |
| `DSH_QA_RETURN_ROWS` | `200` | 返回行数上限 |
| `DSH_QA_CONTEXT_WINDOW` | `8192` | 模型上下文 |
| `DSH_QA_REPLY_RESERVE` | `512` | 回复预留 token |
| `DSH_QA_SESSION_MAX_TOKENS` | `3000` | 历史预算上限 |
| `DSH_QA_MAX_TOOL_CALLS` | `6` | 工具调用上限 |
| `DSH_QA_CHART_ENABLED` | `true` | 图表兜底开关 |

---

## 10. 可观测性与评测

- 指标：各阶段耗时、SQL 校验失败率、执行失败率、重试次数、返回行数、图表类型分布、P95 延迟。
- 日志：`query_id` 贯穿；SQL 只记录指纹与截断文本，不记录敏感参数。
- 评测：`packages/qa/tests/eval/golden.jsonl`；指标为执行成功率、结果一致率、图表有效率。
- 回归：新增单测覆盖 `SqlGuard`、`ContextBudget`、`ChartPlanner`、`ResultBuilder`；集成测试覆盖 SSE 事件顺序。

---

## 11. 分阶段实施

| 阶段 | 内容 | 验收 |
|---|---|---|
| Q0 | 状态机、SSE 骨架、落库 | 无 LLM 也能跑通 `PENDING→FAILED` |
| Q1 | 本体快照 + 提示词编译 + SchemaLinker | 生成提示词不含全量无关表 |
| Q2 | SqlGuard + SqlExecutor 单入口 | 写操作/多语句/超时全部被拒 |
| Q3 | Planner + 一次修正重试 | 简单单表问题可执行成功 |
| Q4 | ResultBuilder + 真实性约束 | 回答数值与 DB 一致 |
| Q5 | ChartPlanner + 兜底 | 无显式图表时仍能出图或退表格 |
| Q6 | ContextBudget + 评测集 | 长会话不超预算；评测基线落盘 |

---

## 12. 验收标准

1. `packages/qa` 具备可执行的问数链路，查询记录状态可追踪。
2. 所有 SQL 均经同一入口校验并以只读方式执行；写操作、多语句、超时、超行数被拒绝或截断。
3. 本体规则变更后 ≤ 5s 生效，无需重启。
4. 回答中的数值/行数只能来自数据库结果；矛盾时降级为表格。
5. SSE 事件顺序为 `status → (thinking) → sql → data → result → done`，异常走 `error`。
6. `uv run pytest` 全绿；新增单测覆盖 guard/context/chart/result。
7. golden set 评测报告归档到本目录。

---

## 13. 风险与回滚

| 风险 | 应对 |
|---|---|
| 新增 `sqlglot` 依赖 | 锁定版本；解析失败按 `SQL_SYNTAX` 拒绝 |
| 本体提示词过大 | 默认按域裁剪；保留全量开关 |
| `result_data` 结构变更影响前端 | 信封带 `schema_version`，读取兼容旧数组 |
| 只读账号不可用 | 启动自检；不可用时问数开关自动关闭并记日志 |
| SSE 代理/超时 | 保留轮询降级；心跳事件 |
| 状态枚举与 Java 不一致 | 以本文件为准，双栈评审时同步 |

回滚：`DSH_QA_ENABLED=false` 即回到仅 CRUD 的现状；新增端点不注册，既有端点不受影响。

---

## 14. 参考来源

### 14.1 本地

- [packages/qa/router.py](../../packages/qa/src/dsh_onto_qa/router.py)
- [packages/qa/service.py](../../packages/qa/src/dsh_onto_qa/service.py)
- [packages/qa/models.py](../../packages/qa/src/dsh_onto_qa/models.py)
- [packages/qa/schemas.py](../../packages/qa/src/dsh_onto_qa/schemas.py)
- [v0.2.2 设计文档](../0.2.2/design.md)

### 14.2 糖豆（tangdou-data）

- 项目主页：<https://gitee.com/weedlu/tangdou-data>
- Agent：<https://gitee.com/weedlu/tangdou-data/blob/master/backend/app/agent/agent.py>
- 图表工具：<https://gitee.com/weedlu/tangdou-data/blob/master/backend/app/agent/tools/chart_tool.py>
- 聊天 SSE：<https://gitee.com/weedlu/tangdou-data/blob/master/backend/app/api/chat.py>
- 本体 API：<https://gitee.com/weedlu/tangdou-data/blob/master/backend/app/api/ontology.py>
- DeepAgent 设计：<https://gitee.com/weedlu/tangdou-data/blob/master/docs/tangdou/1-糖豆（tangdou）之心DeepAgent.md>
- 本体规则加载：<https://gitee.com/weedlu/tangdou-data/blob/master/docs/tangdou/5-糖豆（tangdou）加载本体规则.md>
- 历史过长：<https://gitee.com/weedlu/tangdou-data/blob/master/docs/tangdou/6-糖豆（tangdou）历史过长.md>
- token 裁剪：<https://gitee.com/weedlu/tangdou-data/blob/master/docs/tangdou/7-糖豆（tangdou）token裁剪.md>
