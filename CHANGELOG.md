# 版本

> 本文件记录 dsh-ontology 的版本变更。
> **变更记录约定**
> - 每个版本标注：版本号、日期、变更类型、影响范围、更新内容
> - 变更类型：`新增` / `变更` / `修复` / `移除` / `文档` / `构建`
> - 影响范围使用包名（`base` / `flow` / `qa` / `viz` / `metric` / `platform`）或 `仓库`
> - 规划中的版本标注“未发布/计划”，不与已交付版本混淆
> - AI Agent 修改代码后，应同步更新本文件并引用版本号与影响范围

## 版本索引

| 版本 | 日期 | 影响范围 | 摘要 |
| --- | --- | --- | --- |
| 0.2.2（计划） | — | 全部包 | 对齐 Java 0.2.2，未实施 |
| 0.2.0 | 2026-10-30 | 仓库、base/flow/qa/viz/metric、platform | Python 平台层初始实现 |

## 版本号：0.2.2（计划，未发布）
- 目标：对齐 Java `dsh-java-ontology` 0.2.2
- 计划内容（详见 `docs/0.2.2/`）：
1. 模型引擎：七模型 YAML 加载、注册表、完整性报告、类型目录
2. 模型 API：`/api/model/manifest|aggregates|aggregates/{alias}|integrity`
3. `GET /api/ontology/discovered`
4. Schema 校验：必填/类型/枚举/未知字段，HTTP 400 字段级错误
5. 晋升 9 类：按名称列写入，未知类型 400，幂等
6. 响应包装：`{code,msg,data}`，SSE / health 例外
7. CORS：白名单跨域
8. 测试与契约：pytest ≥ 60，5 个端点进基线
- 状态：规划定稿，尚未实施；实施后补充实际测试结果与偏差
- 备注：目录名 `docs/0.2.2` 指对齐的 Java 里程碑，本仓版本按自身节奏推进至 0.2.2

## 版本号：0.2.0
- 更新日期：2026-10-30
- 变更类型：新增
- 影响范围：仓库、base、flow、qa、viz、metric、platform
- 更新内容：
1. 建立 uv workspace，按 `packages/*` + `apps/*` 组织
2. `base`：配置（环境变量）、双库会话、租户中间件、JWT、统一结果、Harness 插件协议
3. `flow`：认证授权、动态本体、工作台、个人/公共/全局知识汇聚
4. `qa`：报告、问数、分析任务
5. `viz`：图谱查询与展示数据组装
6. `metric`：指标采集与统计（`onto_metric_*` 5 张表）
7. `platform`：聚合 5 包，FastAPI 监听 8093，提供 `/health`
8. 数据基线：37 张 SQLAlchemy 模型、107 个 HTTP 端点、双数据库引擎
9. 新增 `docs/0.2.2/`：对齐 Java 0.2.2 的 spec / design / tasks / release notes
- 验证命令：`uv sync --all-packages && uv run dsh-ontology`，访问 `http://127.0.0.1:8093/health`
