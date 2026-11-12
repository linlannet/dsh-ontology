"""JWT 认证与角色校验，对齐 Java ``JwtUtil`` / ``RoleInterceptor``。

角色层级：0=主任（SUPER_ADMIN）/ 1=研究员（RESEARCHER）/ 2=访客（GUEST）。
"""

from __future__ import annotations

import time
from contextvars import ContextVar

import jwt
from fastapi import HTTPException

role_level_var: ContextVar[int | None] = ContextVar("role_level", default=None)


def create_token(
    secret: str,
    user_id: int,
    user_name: str,
    role_level: int,
    tenant_id: int | None,
    expiration_ms: int,
) -> str:
    """签发 JWT，claim 名称与 Java 版一致（userName/roleLevel/tenantId）。"""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "userName": user_name,
        "roleLevel": role_level,
        "tenantId": tenant_id,
        "iat": now,
        "exp": now + expiration_ms // 1000,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(secret: str, token: str) -> dict | None:
    """解析并校验 JWT；无效或过期返回 ``None``（对齐 Java ``validateToken``）。"""
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None


def require_role(level: int):
    """生成 FastAPI 依赖：要求当前用户角色层级不高于 ``level``。"""

    def dependency() -> None:
        current = role_level_var.get()
        if current is None:
            raise HTTPException(status_code=401, detail="未登录")
        if current > level:
            raise HTTPException(status_code=403, detail="权限不足")

    return dependency
