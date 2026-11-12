"""流程包（dsh-onto-flow）。"""

from .model_router import router as model_router
from .ontology_router import router as ontology_router
from .router import router
from .sys_router import ALL_SYS_ROUTERS

__version__ = "0.2.0"

__all__ = [
    "router",
    "ontology_router",
    "model_router",
    "ALL_SYS_ROUTERS",
    "__version__",
]
