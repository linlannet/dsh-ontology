"""平台应用包（dsh_ontology）：应用工厂 + 5 包路由聚合。"""

from .app import create_app

__version__ = "0.2.0"

__all__ = ["create_app", "__version__"]
