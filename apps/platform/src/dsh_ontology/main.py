"""平台服务入口：``dsh-ontology`` 控制台脚本，默认监听 8093。"""

from __future__ import annotations

import uvicorn

from .app import create_app


def run() -> None:
    app = create_app()
    cfg = app.state.settings
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    run()
