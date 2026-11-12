"""统一响应结构，与 Java 版 ``Result`` 对齐：``{code, msg, data}``。"""

from __future__ import annotations

from typing import Any


def ok(data: Any = None) -> dict[str, Any]:
    # Java ``Result.success`` 使用 code=200，保持一致，前端无需分支适配。
    return {"code": 200, "msg": "success", "data": data}


def fail(msg: str = "error", code: int = 500) -> dict[str, Any]:
    return {"code": code, "msg": msg, "data": None}
