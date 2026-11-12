# AGENTS.md — dsh-ontology

## Project
DSH 本体库的 Python 平台层基座：uv workspace，5 个平台包 + 平台应用，FastAPI 监听 8093。与 Java `dsh-java-ontology` 同契约、同表结构。

## Layout
- `packages/base/` `dsh_onto_base`：`config.py`、`db.py`（双库）、`security.py`（JWT/角色）、`middleware.py`（租户）、`plugin.py`（Harness 插件协议）、`result.py`、`router.py`
- `packages/flow/` `dsh_onto_flow`：`sys_*`（认证权限）、`ontology_router`、`workspace`、全局知识汇聚
- `packages/qa/` `dsh_onto_qa`：报告、问数、分析任务
- `packages/viz/` `dsh_onto_viz`：图谱查询与展示
- `packages/metric/` `dsh_onto_metric`：指标采集与统计（`onto_metric_*` 5 张表）
- `apps/platform/` `dsh_ontology`：`app.py`（create_app）、`main.py`（入口，8093）
- `docs/0.2.2/` 对齐 Java 0.2.2 的 spec / design / tasks / release notes

## Build & Test
- 安装：`uv sync --all-packages`
- 运行：`uv run dsh-ontology`（8093）
- 健康检查：`GET /health`
- 测试：当前未建立 pytest 基线（0 用例），计划见 `docs/0.2.2/`
- 改动后至少执行 `uv sync --all-packages` 并验证应用可启动

## Conventions
- 包边界：`base` 不依赖业务包；其余包只依赖 `base`
- 通用能力（双库会话、租户、JWT、插件协议、统一结果）只放 `base`
- 域路由放各包 `router.py`，由 `apps/platform/app.py` 统一挂载
- 错误结构保持 `{code, msg, data}`；HTTP 状态与 Java 拦截器一致
- 与 Java 版保持同契约、同表结构；差异写入 `docs/0.2.2/`
- `README.md` / `README.en.md` 同步；版本变更写入 `CHANGELOG.md`

## Do Not
- 不提交 `.venv/`、`__pycache__/`、缓存目录、`.env`
- 不提交数据库密码、JWT 密钥、Harness Token
- 不在 `base` 中引入业务域依赖
- 不在 Python 侧新增与 Java 不一致的 DDL
- 不声称尚未实现的规划能力已交付

## Key Docs
- `README.md` / `README.en.md` / `llms.txt`
- `CHANGELOG.md`
- `docs/0.2.2/spec.md` / `design.md` / `tasks.md`