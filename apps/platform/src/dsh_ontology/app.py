"""平台应用工厂。

两种使用方式：
1. 独立进程：``dsh-ontology``（监听 8093），见 ``main.py``；
2. 被项目层复用：``from dsh_ontology.app import create_app``，
   后续嵌入式形态（``DSH_DEPLOY_MODE=embedded``）可直接挂载路由。
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from dsh_onto_base import Database, Settings
from dsh_onto_base.middleware import install_middlewares
from dsh_onto_base.ontology import load_engine
from dsh_onto_base.router import router as base_router
from dsh_onto_flow import model_router
from dsh_onto_flow import router as flow_router
from dsh_onto_metric import router as metric_router
from dsh_onto_qa import router as qa_router
from dsh_onto_viz import router as viz_router

PLATFORM_ROUTERS = (
    base_router,
    flow_router,
    model_router,
    qa_router,
    viz_router,
    metric_router,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建平台 FastAPI 实例；不在此处连接数据库。"""
    cfg = settings or Settings.from_env()
    app = FastAPI(title=cfg.app_name, version=cfg.version)

    app.state.settings = cfg
    app.state.database = Database(
        siis_url=cfg.siis_database_url,
        onto_url=cfg.onto_database_url,
        echo=cfg.sql_echo,
    )

    # 模型引擎启动即加载；启用时加载失败直接终止启动，避免静默降级。
    if cfg.model_enabled:
        app.state.ontology_engine = load_engine()

    install_middlewares(app, cfg)
    for router in PLATFORM_ROUTERS:
        app.include_router(router)

    @app.exception_handler(HTTPException)
    async def auth_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        """对齐 Java 全局异常：401 未登录 / 403 权限不足 / 404 路径不存在。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "msg": str(exc.detail), "data": None},
        )

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {
            "service": cfg.app_name,
            "version": cfg.version,
            "status": "ok",
            "deploy_mode": cfg.deploy_mode,
            "modules": [r.tags[0] if r.tags else "" for r in PLATFORM_ROUTERS],
        }

    return app
