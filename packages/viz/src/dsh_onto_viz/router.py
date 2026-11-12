"""可视化包路由（P0 占位，图谱端点按 P2 阶段补齐）。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/viz", tags=["viz"])


@router.get("/health")
async def health() -> dict:
    from . import __version__

    return {"module": "viz", "status": "ok", "version": __version__}
