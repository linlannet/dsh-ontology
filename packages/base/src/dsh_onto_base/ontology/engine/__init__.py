"""模型引擎只读入口：加载七模型并产出注册表与完整性报告。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .integrity import IntegrityIssue, IntegrityReport, ModelIntegrityChecker
from .loader import EngineSnapshot, ModelLoadError, ModelLoader
from .model import AggregateDescriptor, AttributeDescriptor, ModelManifest
from .registry import OntologyRegistry

__all__ = [
    "AggregateDescriptor",
    "AttributeDescriptor",
    "EngineSnapshot",
    "IntegrityIssue",
    "IntegrityReport",
    "ModelIntegrityChecker",
    "ModelLoadError",
    "ModelLoader",
    "ModelManifest",
    "OntologyModelEngine",
    "OntologyRegistry",
    "load_engine",
]


@dataclass(frozen=True)
class OntologyModelEngine:
    """启动时一次性加载的模型引擎快照。"""

    snapshot: EngineSnapshot
    registry: OntologyRegistry
    report: IntegrityReport

    @property
    def manifests(self) -> tuple[ModelManifest, ...]:
        return self.snapshot.manifests

    @property
    def source_files(self) -> tuple[str, ...]:
        return self.snapshot.source_files

    @property
    def project_layer_present(self) -> bool:
        return self.snapshot.project_layer_present


def load_engine(resources: Any = None) -> OntologyModelEngine:
    """加载模型资源并执行完整性检查；失败抛 ``ModelLoadError``。"""
    snapshot = ModelLoader(resources).load()
    registry = OntologyRegistry.from_descriptors(snapshot.descriptors)
    report = ModelIntegrityChecker().check(snapshot)
    return OntologyModelEngine(snapshot=snapshot, registry=registry, report=report)
