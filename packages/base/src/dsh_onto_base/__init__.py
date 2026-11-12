"""平台基础包（dsh-onto-base）。"""

from .config import Settings
from .db import Base, Database
from .middleware import TenantMiddleware, tenant_id_var, user_id_var
from .plugin import HarnessPlugin, ToolSpec, load_plugins
from .result import fail, ok
from .security import create_token, decode_token, require_role, role_level_var

__version__ = "0.2.0"

__all__ = [
    "Settings",
    "Base",
    "Database",
    "TenantMiddleware",
    "tenant_id_var",
    "user_id_var",
    "role_level_var",
    "create_token",
    "decode_token",
    "require_role",
    "HarnessPlugin",
    "ToolSpec",
    "load_plugins",
    "ok",
    "fail",
    "__version__",
]
