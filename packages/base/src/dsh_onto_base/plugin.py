"""Harness 插件协议：与 Java 版 ``JavaHarnessPlugin`` 三要素对齐。"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Callable, Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolSpec:
    """单个工具定义，JSON Schema 与 Java 版保持一致。"""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[..., Any]
    #: 对应 Java ``ToolDefinition#isConcurrencySafe``，默认串行。
    concurrency_safe: bool = False


@runtime_checkable
class HarnessPlugin(Protocol):
    """插件三要素：name / version / tools()。"""

    name: str
    version: str

    def tools(self) -> list[ToolSpec]: ...


def load_plugins(group: str = "dsh.harness.plugins") -> dict[str, HarnessPlugin]:
    """按 entry points 发现插件，与 ``plugin.yaml`` 清单互为校验。"""
    found: dict[str, HarnessPlugin] = {}
    for ep in entry_points(group=group):
        plugin = ep.load()
        found[plugin.name] = plugin
    return found
