"""平台配置：全部由环境变量注入，不硬编码账号密码。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class Settings:
    """平台运行配置。

    连接串默认只给主机与库名，账号密码由部署环境通过环境变量补全，例如：
    ``DSH_ONTO_DB_URL=mysql+asyncmy://user:pass@host:3306/dsh_java_ontodb``。
    """

    app_name: str = "dsh-ontology"
    version: str = "0.2.0"
    host: str = "0.0.0.0"
    port: int = 8093
    deploy_mode: str = "split"
    siis_database_url: str = "mysql+asyncmy://127.0.0.1:3306/dsh_java_siisdb"
    onto_database_url: str = "mysql+asyncmy://127.0.0.1:3306/dsh_java_ontodb"
    sql_echo: bool = False
    # JWT 与 Java 版 dsh.ontology.jwt.* 对齐；secret 必须由部署环境覆盖
    jwt_secret: str = "dsh-java-ontology-secret-key-2026-please-change-in-production-at-least-32-chars"
    jwt_expiration_ms: int = 86400000
    jwt_header: str = "Authorization"
    jwt_prefix: str = "Bearer "
    harness_base_url: str = "http://127.0.0.1:8090"
    # 模型引擎开关：默认启用，加载失败即阻断启动；置 false 可降级。
    model_enabled: bool = True
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=_env("DSH_APP_NAME", "dsh-ontology"),
            version=_env("DSH_VERSION", "0.2.0"),
            host=_env("DSH_PLATFORM_HOST", "0.0.0.0"),
            port=int(_env("DSH_PLATFORM_PORT", "8093")),
            deploy_mode=_env("DSH_DEPLOY_MODE", "split"),
            siis_database_url=_env(
                "DSH_SIIS_DB_URL", "mysql+asyncmy://127.0.0.1:3306/dsh_java_siisdb"
            ),
            onto_database_url=_env(
                "DSH_ONTO_DB_URL", "mysql+asyncmy://127.0.0.1:3306/dsh_java_ontodb"
            ),
            sql_echo=_env("DSH_SQL_ECHO", "false").lower() == "true",
            jwt_secret=_env(
                "DSH_JWT_SECRET",
                "dsh-java-ontology-secret-key-2026-please-change-in-production-at-least-32-chars",
            ),
            jwt_expiration_ms=int(_env("DSH_JWT_EXPIRATION_MS", "86400000")),
            jwt_header=_env("DSH_JWT_HEADER", "Authorization"),
            jwt_prefix=_env("DSH_JWT_PREFIX", "Bearer "),
            harness_base_url=_env("DSH_HARNESS_BASE_URL", "http://127.0.0.1:8090"),
            model_enabled=_env("DSH_ONTOLOGY_MODEL_ENABLED", "true").lower() == "true",
        )
