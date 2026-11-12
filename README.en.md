# dsh-ontology

[简体中文](./README.md) | English

> **TL;DR** · The **Python platform layer** for the DSH ontology: a uv workspace with 5 platform packages (base / flow / qa / viz / metric) plus a platform app, served by FastAPI on **8093**.
> **Keywords**: DSH, Ontology, FastAPI, Python 3.12, uv workspace, SQLAlchemy, JWT, Multi-tenant
> **AI entry**: [llms.txt](./llms.txt) · [AGENTS.md](./AGENTS.md)

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
![python](https://img.shields.io/badge/Python-3.12-blue.svg)
![fastapi](https://img.shields.io/badge/FastAPI-0.115-009688.svg)

## Introduction

`dsh-ontology` is the **Python platform layer** for the ontology library in the DeepSeek Harness ecosystem. It shares the contract and schema with the Java `dsh-java-ontology` but uses a different stack. The platform provides static ontology, dynamic ontology, metrics, reports, Q&A and visualization, and is reused over HTTP by the SIIS project layer (`dsh-ontots-siis`, 8094).

- **Platform app** (`apps/platform`): aggregates the 5 packages, FastAPI on **8093**
- **Platform packages**: `base` (config / dual DB / tenant / plugin protocol), `flow` (auth / dynamic ontology / workspace / global aggregation), `qa` (reports and Q&A), `viz` (graph visualization), `metric` (metrics)
- **Data layer**: 37 SQLAlchemy models; dual engines `dsh_java_siisdb` + `dsh_java_ontodb`
- **Peer implementation**: Java `dsh-java-ontology` (8100) + `dsh-ontolab-siis` (8101)

## Dual-Stack Positioning

| Stack | Platform | Project layer (SIIS) |
| --- | --- | --- |
| Java | `dsh-java-ontology` (8100) | `dsh-ontolab-siis` (8101) |
| Python | **`dsh-ontology` (8093)** | `dsh-ontots-siis` (8094) |

## Version History

All changes are recorded in [CHANGELOG](./CHANGELOG.md). The workspace and all platform packages are currently `0.2.0`.

## Table of Contents

- [1. Platform Packages](#1-platform-packages)
- [2. Quick Start](#2-quick-start)
- [3. Architecture and Baseline](#3-architecture-and-baseline)
- [4. Configuration](#4-configuration)
- [5. Directory Layout](#5-directory-layout)
- [6. Conventions](#6-conventions)
- [7. Current Status and Plan](#7-current-status-and-plan)
- [8. Documentation Index](#8-documentation-index)
- [Contributing](#contributing)
- [License](#license)

---

## 1. Platform Packages

| Package | Version | Responsibility |
| --- | --- | --- |
| `packages/base` | 0.2.0 | Config, dual-DB sessions, tenant middleware, JWT, unified result, Harness plugin protocol |
| `packages/flow` | 0.2.0 | Auth, dynamic ontology, workspace, personal/common/global knowledge aggregation |
| `packages/qa` | 0.2.0 | Reports and Q&A: reports, sections, charts, sessions, tasks |
| `packages/viz` | 0.2.0 | Graph query and presentation data assembly |
| `packages/metric` | 0.2.0 | Metric collection and statistics (`onto_metric_*`, 5 tables) |
| `apps/platform` | 0.2.0 | Aggregation app and FastAPI entry, default 8093 |

## 2. Quick Start

### 2.1 Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- MySQL 8.0+

### 2.2 Install and Run

```bash
cd dsh-ontology
uv sync --all-packages

# start the platform app (8093)
uv run dsh-ontology
```

Health check: <http://127.0.0.1:8093/health>

The platform normally runs together with the project layer `dsh-ontots-siis` (8094), which calls it over HTTP.

## 3. Architecture and Baseline

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

### 3.1 Baseline Facts (see `docs/0.2.2/spec.md`)

| Item | Value |
| --- | --- |
| App port | 8093 (`DSH_PLATFORM_PORT`) |
| Package layout | base / flow / qa / viz / metric + platform |
| Databases | Dual engines `dsh_java_siisdb` + `dsh_java_ontodb`, lazily created |
| Tables | 37 SQLAlchemy `__tablename__` models |
| HTTP endpoints | 107 (base / flow / sys / metric / qa / viz / ontologies) |
| Response shape | Raw on success, `{code, msg, data}` on errors; unified wrapping is planned |
| Tests | Currently 0; a pytest baseline is planned |

## 4. Configuration

All settings come from environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `DSH_APP_NAME` | `dsh-ontology` | App name |
| `DSH_VERSION` | `0.2.0` | App version |
| `DSH_PLATFORM_HOST` | `0.0.0.0` | Bind host |
| `DSH_PLATFORM_PORT` | `8093` | App port |
| `DSH_DEPLOY_MODE` | `split` | Deployment mode (split / embedded) |
| `DSH_SIIS_DB_URL` | `mysql+asyncmy://127.0.0.1:3306/dsh_java_siisdb` | SIIS DB |
| `DSH_ONTO_DB_URL` | `mysql+asyncmy://127.0.0.1:3306/dsh_java_ontodb` | Ontology DB |
| `DSH_SQL_ECHO` | `false` | Print SQL |
| `DSH_JWT_SECRET` | built-in default | JWT secret; must be overridden in production |
| `DSH_JWT_EXPIRATION_MS` | `86400000` | Token lifetime |
| `DSH_JWT_HEADER` | `Authorization` | Token header |
| `DSH_JWT_PREFIX` | `Bearer ` | Token prefix |
| `DSH_HARNESS_BASE_URL` | `http://127.0.0.1:8090` | Harness URL |

> Connection strings only carry host and database by default; inject credentials through the full URL in the deployment environment. Never commit them.

## 5. Directory Layout

```text
dsh-ontology/
├── packages/base/                 dsh_onto_base: config/db/security/middleware/plugin/result/router
├── packages/flow/                 dsh_onto_flow: sys/ontology/workspace/global
├── packages/qa/                   dsh_onto_qa: reports and Q&A
├── packages/viz/                  dsh_onto_viz: graph presentation
├── packages/metric/               dsh_onto_metric: metrics
├── apps/platform/                 dsh_ontology: create_app / main
├── docs/0.2.2/                    Alignment spec / design / tasks / release notes
├── pyproject.toml                 uv workspace root
└── uv.lock
```

## 6. Conventions

- Keep package boundaries: `base` must not depend on business packages; `flow` / `qa` / `viz` / `metric` depend only on `base`
- Shared capabilities (dual-DB sessions, tenant middleware, JWT, plugin protocol, unified result) live only in `base`
- Put domain routes in each package's `router.py`; mount them in `apps/platform/app.py`
- Keep the `{code, msg, data}` error shape and existing exception handling
- Stay aligned with the Java version on contract and schema; document any divergence in `docs/0.2.2/`
- Keep `README.md` and `README.en.md` in sync; record changes in `CHANGELOG.md`

## 7. Current Status and Plan

- Delivered: workspace 0.2.0, 5 packages + platform, 37 models / 107 endpoints
- No pytest baseline yet (0 tests)
- Planned `v0.2.2`: align with Java 0.2.2 — model engine, `/api/model/*`, discovered, schema validation, promote 9 categories, response wrapping, CORS, pytest ≥ 60
- Plan details in `docs/0.2.2/`

## 8. Documentation Index

| Document | Content |
| --- | --- |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and AI retrieval hints |
| [AGENTS.md](./AGENTS.md) | Layout, commands and constraints for AI agents |
| [llms.txt](./llms.txt) | Machine-readable summary and command index |
| [docs/0.2.2/spec.md](./docs/0.2.2/spec.md) | Java 0.2.2 alignment requirements and baseline facts |
| [docs/0.2.2/design.md](./docs/0.2.2/design.md) | Alignment design |
| [docs/0.2.2/tasks.md](./docs/0.2.2/tasks.md) | Task breakdown |
| [docs/0.2.2/release-v0.2.2-development-notes.md](./docs/0.2.2/release-v0.2.2-development-notes.md) | Development notes (planned) |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/xxxx`
3. At least pass `uv sync --all-packages` and the relevant package checks before committing
4. Open a Pull Request

## License

[MIT © 2026 linlannet](./LICENSE)