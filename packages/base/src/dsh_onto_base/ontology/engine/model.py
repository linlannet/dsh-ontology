"""不可变模型描述符，字段与 Java ``dsh-ontology`` 0.2.2 引擎对齐。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AttributeDescriptor:
    """YAML ``attributes`` 列表中的一项；``source_path`` 仅内部诊断用，不对外输出。"""

    name: str
    label: str | None = None
    type: str | None = None
    required: bool = False
    unique: bool = False
    enum_values: tuple[str, ...] = ()
    default_value: str | None = None
    description: str | None = None
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "unique": self.unique,
            "enumValues": list(self.enum_values),
            "defaultValue": self.default_value,
            "description": self.description,
        }


@dataclass(frozen=True)
class AggregateDescriptor:
    """聚合根；嵌套实体（``entities``）同样以本类型表达。"""

    id: str | None = None
    name: str | None = None
    alias: str = ""
    category: str | None = None
    lifecycle: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    attributes: tuple[AttributeDescriptor, ...] = ()
    sub_entities: tuple[AggregateDescriptor, ...] = ()
    source_file: str | None = None

    def attribute(self, name: str) -> AttributeDescriptor | None:
        return next((item for item in self.attributes if item.name == name), None)

    def total_attribute_count(self) -> int:
        """含嵌套子实体字段的总数，与 Java ``totalAttributeCount`` 一致。"""
        return len(self.attributes) + sum(
            child.total_attribute_count() for child in self.sub_entities
        )

    def total_enum_count(self) -> int:
        return sum(1 for item in self.attributes if item.type == "Enum") + sum(
            child.total_enum_count() for child in self.sub_entities
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "alias": self.alias,
            "category": self.category,
            "lifecycle": list(self.lifecycle),
            "tags": list(self.tags),
            "attributes": [item.to_dict() for item in self.attributes],
            "subEntities": [child.to_dict() for child in self.sub_entities],
            "sourceFile": self.source_file,
        }


@dataclass(frozen=True)
class ModelManifest:
    """基座或项目层清单，对应 ``manifest.json``。"""

    model_type: str
    version: str
    platform: str | None = None
    name: str | None = None
    description: str | None = None
    base_models: tuple[str, ...] = ()
    projects: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    base_manifest: str | None = None
    source_file: str | None = None
