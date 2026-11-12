"""基础路由：健康检查与版本信息。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/base", tags=["base"])


@router.get("/health")
async def health() -> dict:
    from . import __version__

    return {"module": "base", "status": "ok", "version": __version__}
