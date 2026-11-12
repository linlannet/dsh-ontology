# dsh-ontology（Python 平台）v0.2.2 对齐开发说明

> 版本：`v0.2.2`（拟） ｜ 对齐：Java `dsh-java-ontology` 0.2.2 ｜ 状态：**规划定稿（待实施）**
>
> 本文件描述 Python 产品层基座的 0.2.2 对齐计划，不是已发布版本的 changelog。实施后补充实际测试结果与偏差。

---

## 一、版本概述

| 项 | 内容 |
|---|---|
| 当前版本 | `0.2.0`（根 + 5 包） |
| 目标版本 | `0.2.2` |
| 应用端口 | 8093 |
| 包结构 | base / flow / qa / viz / metric + platform |
| 数据表 | 37 张 SQLAlchemy 模型；本版本不新增 |
| 现有端点 | 107 个 |
| 现有测试 | 0（本版本建立 pytest 基线） |
| 对齐目标 | Java 0.2.2：模型引擎、4 模型 API、discovered、晋升 9 类、CORS、统一包装 |

## 二、交付内容（计划）

1. **模型引擎**：七模型 YAML 加载、注册表、完整性报告、类型目录。
2. **模型 API**：`/api/model/manifest|aggregates|aggregates/{alias}|integrity`。
3. **discovered 端点**：`GET /api/ontology/discovered`。
4. **Schema 校验**：必填/类型/枚举/未知字段，HTTP 400 字段级错误。
5. **晋升 9 类**：按名称列写入，未知类型 400，幂等。
6. **响应包装**：`{code,msg,data}`，SSE/health 例外。
7. **CORS**：白名单跨域。
8. **测试与契约**：pytest ≥ 60，5 端点进基线。

## 三、任务映射

| 交付项 | 任务 |
|---|---|
| 版本/配置/测试脚手架 | TP0 |
| 模型引擎 | TP1 |
| 模型 API | TP2 |
| Schema 校验 | TP3 |
| 晋升与匹配 | TP4 |
| discovered | TP5 |
| 响应包装/CORS | TP6 |
| 测试/契约 | TP7 |

详见 [tasks.md](./tasks.md)。

## 四、验证计划（待执行）

### 4.1 启动与引擎

```bash
uv run pytest
DSH_ONTOLOGY_MODEL_ENABLED=true uv run python -m dsh_ontology.main
```

预期：启动日志输出模型数/聚合根数/完整性计数；坏 YAML 阻断启动并指出文件。

### 4.2 模型 API

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8093/api/model/manifest
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8093/api/model/integrity
```

预期：`{code:200,msg:"success",data:{...}}`；未知 alias 404；未登录 401。

### 4.3 晋升 9 类

| 场景 | 预期 |
|---|---|
| hotspot | 写 `hotspot_name` |
| book / paper | 写 `title` |
| term | 写 `term_name` |
| 显式未知类型 | 400 |
| 空目标 + 非 9 类 | `onto_ontology_entity` |
| 重复晋升 | `ALREADY_EXISTS` |

### 4.4 响应包装回归

对 107 个端点抽查：成功响应均为 `{code,msg,data}`；SSE 与 health 不包装；无二次包装。

### 4.5 契约

Python OpenAPI 片段与 Java 0.2.2 做 diff，5 个新增端点字段/错误码一致。

## 五、已知限制与风险

1. **响应包装是破坏性变更**：既有前端若直接消费裸结构会受影响；用 `DSH_RESPONSE_ENVELOPE` 灰度，默认建议先 `false` 再切 `true`。
2. **表数差异**：Python 37 张 vs Java 38 张，需以 Java 迁移为准核对差异；本版本不建表。
3. **Alembic 缺失**：Python 侧尚无迁移链；本版本不引入，只做 SQLAlchemy 模型对齐。
4. **无现成测试**：从 0 建立 pytest，需先补脚手架，不能以“无测试”作为跳过理由。
5. **Java 晋升改造未实施**：Java 0.2.2 的 9 类晋升同为规划态；Python 侧以其契约为准，实施时双栈同步。
6. **契约基线未落盘**：`ai-pilot/contract/openapi-baseline.yaml` 目录尚未建立，TP7.3 补齐。

## 六、依赖与兼容性

| 项 | 说明 |
|---|---|
| Python | 3.12+；FastAPI / Pydantic v2 / SQLAlchemy 2 async |
| 数据库 | 双引擎沿用 `dsh_java_siisdb` + `dsh_java_ontodb`，无 DDL |
| 依赖新增 | 仅测试依赖 pytest / httpx / pytest-asyncio |
| 既有端点 | 107 个路径不变；响应结构统一包装（可开关） |
| 双栈 | 与 Java 0.2.2 5 端点 + 9 类晋升一致 |

## 七、发布检查清单（实施完成后勾选）

- [ ] 版本 0.2.2（根 + 5 包）
- [ ] 七模型加载成功，完整性报告可查
- [ ] `/api/model/*` 4 端点与 Java 一致
- [ ] `GET /api/ontology/discovered` 可用
- [ ] 9 类晋升 + 特殊名称列验证通过
- [ ] Schema 校验 400 + 字段级错误
- [ ] 响应包装 107 端点回归完成
- [ ] CORS 白名单验证
- [ ] `uv run pytest` ≥ 60 全绿
- [ ] 契约基线含 5 端点
- [ ] `ai-pilot` 设计文档实现状态同步

## 八、回滚方案

1. 代码回滚到 0.2.0 基线 commit。
2. 配置回滚：`DSH_RESPONSE_ENVELOPE=false`、`DSH_ONTOLOGY_MODEL_ENABLED=false`、清空 `DSH_CORS_ALLOWED_ORIGINS`。
3. 模型 API 与晋升服务为新增路由，回滚后不影响既有 107 端点。
4. 无数据库变更，无需数据回滚。
