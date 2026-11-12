# dsh-ontology

简体中文 | [English](./README.en.md)

> **TL;DR** · DSH 本体库的 **Python 平台层基座**：uv workspace 维护 5 个平台包（base / flow / qa / viz / metric）+ 平台应用，FastAPI 监听 **8093**。
> **Keywords**: DSH, Ontology, FastAPI, Python 3.12, uv workspace, SQLAlchemy, JWT, Multi-tenant
> **AI 入口**: [llms.txt](./llms.txt) · [AGENTS.md](./AGENTS.md)

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
![python](https://img.shields.io/badge/Python-3.12-blue.svg)
![fastapi](https://img.shields.io/badge/FastAPI-0.115-009688.svg)

## 简介

`dsh-ontology` 是基于 DeepSeek Harness 体系的本体库 **Python 平台层**，与 Java 版 `dsh-java-ontology` 同契约、同表结构、不同技术栈。平台提供静态本体、动态本体、指标、报告、问数与可视化能力，并由项目层 SIIS（`dsh-ontots-siis`，8094）通过 HTTP 复用。

- **平台应用**（`apps/platform`）：聚合 5 个包，FastAPI 监听 **8093**
- **平台包**：`base`（配置/双库/租户/插件协议）、`flow`（认证/动态本体/工作台/全局聚合）、`qa`（报告问数）、`viz`（图谱展示）、`metric`（指标）
- **数据层**：37 张 SQLAlchemy 模型；双引擎 `dsh_java_siisdb` + `dsh_java_ontodb`
- **对等实现**：Java `dsh-java-ontology`（8100）+ `dsh-ontolab-siis`（8101）

## 双栈定位

| 栈 | 平台层 | 项目层（SIIS） |
| --- | --- | --- |
| Java | `dsh-java-ontology`（8100） | `dsh-ontolab-siis`（8101） |
| Python | **`dsh-ontology`（8093）** | `dsh-ontots-siis`（8094） |

## 版本历史

全部版本变更见 [CHANGELOG](./CHANGELOG.md)。当前版本：workspace 与全部平台包均为 `0.2.0`。

## 目录

- [1. 平台包](#1-平台包)
- [2. 快速开始](#2-快速开始)
- [3. 架构与基线](#3-架构与基线)
- [4. 配置项](#4-配置项)
- [5. 目录结构](#5-目录结构)
- [6. 开发约定](#6-开发约定)
- [7. 当前状态与计划](#7-当前状态与计划)
- [8. 文档索引](#8-文档索引)
- [参与贡献](#参与贡献)
- [许可证](#许可证)

---

## 1. 平台包

| 包 | 版本 | 职责 |
| --- | --- | --- |
| `packages/base` | 0.2.0 | 配置、双库会话、租户中间件、JWT、统一结果、Harness 插件协议 |
| `packages/flow` | 0.2.0 | 认证授权、动态本体、工作台、个人/公共/全局知识汇聚 |
| `packages/qa` | 0.2.0 | 报告与问数：报告、章节、图表、会话、任务 |
| `packages/viz` | 0.2.0 | 图谱查询与展示数据组装 |
| `packages/metric` | 0.2.0 | 指标采集与统计（`onto_metric_*` 5 张表） |
| `apps/platform` | 0.2.0 | 聚合应用，FastAPI 入口，默认 8093 |

## 2. 快速开始

### 2.1 环境要求

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- MySQL 8.0+

### 2.2 安装与运行

```bash
cd dsh-ontology
uv sync --all-packages

# 启动平台应用（8093）
uv run dsh-ontology
```

健康检查：<http://127.0.0.1:8093/health>

平台层通常与项目层 `dsh-ontots-siis`（8094）配套运行；SIIS 通过 HTTP 调用本服务。

## 3. 架构与基线

```text
SIIS App (8094) ──HTTP──► Platform App (8093)
                              ├── base   (config / db / security / middleware / plugin)
                              ├── flow   (sys / ontology / workspace / global)
                              ├── qa     (report / qa / task)
                              ├── viz    (graph view)
                              └── metric (metric models)
                              │
                    SIIS DB (dsh_java_siisdb)  ⇄  Onto DB (dsh_java_ontodb)
```

### 3.1 基线事实（见 `docs/0.2.2/spec.md`）

| 项 | 值 |
| --- | --- |
| 应用端口 | 8093（`DSH_PLATFORM_PORT`） |
| 包结构 | base / flow / qa / viz / metric + platform |
| 数据库 | 双引擎 `dsh_java_siisdb` + `dsh_java_ontodb`，延迟创建 |
| 表模型 | 37 张 SQLAlchemy `__tablename__` |
| HTTP 端点 | 107 个（base / flow / sys / metric / qa / viz / ontologies） |
| 响应结构 | 成功为裸结构，异常为 `{code, msg, data}`；统一包装在计划中 |
| 测试 | 当前 0；计划建立 pytest 基线 |

## 4. 配置项

全部通过环境变量注入：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DSH_APP_NAME` | `dsh-ontology` | 应用名 |
| `DSH_VERSION` | `0.2.0` | 应用版本 |
| `DSH_PLATFORM_HOST` | `0.0.0.0` | 监听地址 |
| `DSH_PLATFORM_PORT` | `8093` | 应用端口 |
| `DSH_DEPLOY_MODE` | `split` | 部署形态（split / embedded） |
| `DSH_SIIS_DB_URL` | `mysql+asyncmy://127.0.0.1:3306/dsh_java_siisdb` | SIIS 库 |
| `DSH_ONTO_DB_URL` | `mysql+asyncmy://127.0.0.1:3306/dsh_java_ontodb` | 本体库 |
| `DSH_SQL_ECHO` | `false` | 是否打印 SQL |
| `DSH_JWT_SECRET` | 内置默认值 | JWT 密钥，生产必须覆盖 |
| `DSH_JWT_EXPIRATION_MS` | `86400000` | Token 有效期 |
| `DSH_JWT_HEADER` | `Authorization` | Token 头 |
| `DSH_JWT_PREFIX` | `Bearer ` | Token 前缀 |
| `DSH_HARNESS_BASE_URL` | `http://127.0.0.1:8090` | Harness 地址 |

> 连接串默认只给主机与库名，账号密码由部署环境通过完整 URL 注入；不要写入仓库。

## 5. 目录结构

```text
dsh-ontology/
├── packages/base/                 dsh_onto_base：config/db/security/middleware/plugin/result/router
├── packages/flow/                 dsh_onto_flow：sys/ontology/workspace/global
├── packages/qa/                   dsh_onto_qa：报告与问数
├── packages/viz/                  dsh_onto_viz：图谱展示
├── packages/metric/               dsh_onto_metric：指标
├── apps/platform/                 dsh_ontology：create_app / main
├── docs/0.2.2/                    对齐 Java 0.2.2 的 spec / design / tasks / release notes
├── pyproject.toml                 uv workspace 根
└── uv.lock
```

## 6. 开发约定

- 保持包边界：`base` 不依赖业务包；`flow` / `qa` / `viz` / `metric` 只依赖 `base`
- 通用能力（双库会话、租户中间件、JWT、插件协议、统一结果）只放 `base`
- 业务路由按域放在各自包的 `router.py`，由 `apps/platform/app.py` 统一挂载
- 错误结构保持 `{code, msg, data}`；新增端点遵循现有异常处理
- 与 Java 版保持同契约、同表结构；差异需在 `docs/0.2.2/` 说明
- `README.md` 与 `README.en.md` 同步维护；版本变更写入 `CHANGELOG.md`

## 7. 当前状态与计划

- 当前交付：workspace 0.2.0，5 包 + platform，37 模型 / 107 端点
- 尚未建立 pytest 基线（现有测试 0）
- 计划版本 `v0.2.2`：对齐 Java 0.2.2 的模型引擎、`/api/model/*`、discovered、Schema 校验、晋升 9 类、响应包装、CORS 与 pytest ≥ 60
- 规划状态与任务见 `docs/0.2.2/`

## 8. 文档索引

| 文档 | 内容 |
| --- | --- |
| [CHANGELOG.md](./CHANGELOG.md) | 版本记录与 AI 检索提示 |
| [AGENTS.md](./AGENTS.md) | AI Agent 使用的结构、命令与约束 |
| [llms.txt](./llms.txt) | 机器可读摘要与命令索引 |
| [docs/0.2.2/spec.md](./docs/0.2.2/spec.md) | 对齐 Java 0.2.2 的需求规格与基线事实 |
| [docs/0.2.2/design.md](./docs/0.2.2/design.md) | 对齐设计 |
| [docs/0.2.2/tasks.md](./docs/0.2.2/tasks.md) | 任务拆分 |
| [docs/0.2.2/release-v0.2.2-development-notes.md](./docs/0.2.2/release-v0.2.2-development-notes.md) | 开发说明（规划） |

## 参与贡献

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/xxxx`
3. 提交前至少通过 `uv sync --all-packages` 与相关包的自检
4. 发起 Pull Request

## 许可证

[MIT © 2026 linlannet](./LICENSE)