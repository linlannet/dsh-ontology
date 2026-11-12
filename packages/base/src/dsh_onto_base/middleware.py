"""租户与认证上下文中间件，供平台与项目层复用。

身份来源优先级：JWT（``Authorization: Bearer``） > 开发态请求头（``X-Tenant-Id`` / ``X-User-Id``）。
角色层级只来自 JWT，避免仅凭请求头伪造角色。
"""

from __future__ import annotations

from contextvars import ContextVar

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .security import decode_token, role_level_var

tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


class TenantMiddleware(BaseHTTPMiddleware):
    """解析身份并写入 ContextVar 后向下传递。"""

    def __init__(self, app, settings=None) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next):
        settings = self._settings
        tenant_token = user_token = role_token = None
        tenant_id = request.headers.get("X-Tenant-Id")
        user_id = request.headers.get("X-User-Id")
        role_level = None

        auth_header = request.headers.get(settings.jwt_header) if settings else None
        if settings and auth_header and auth_header.startswith(settings.jwt_prefix):
            claims = decode_token(settings.jwt_secret, auth_header[len(settings.jwt_prefix):])
            if claims:
                user_id = str(claims.get("sub")) if claims.get("sub") else user_id
                tenant_id = (
                    str(claims.get("tenantId")) if claims.get("tenantId") is not None else tenant_id
                )
                role_level = claims.get("roleLevel")

        tenant_token = tenant_id_var.set(tenant_id)
        user_token = user_id_var.set(user_id)
        role_token = role_level_var.set(int(role_level) if role_level is not None else None)
        try:
            return await call_next(request)
        finally:
            tenant_id_var.reset(tenant_token)
            user_id_var.reset(user_token)
            role_level_var.reset(role_token)


def install_middlewares(app: FastAPI, settings=None) -> None:
    """平台与项目层共用的中间件装配入口。"""
    app.add_middleware(TenantMiddleware, settings=settings)
