"""alias / category 双索引只读注册表。"""

from __future__ import annotations

from collections.abc import Iterable

from .model import AggregateDescriptor


class OntologyRegistry:
    """``alias`` / ``category`` 索引 + ``by_tag()``；未知键返回 ``None``。"""

    def __init__(self, descriptors: Iterable[AggregateDescriptor]) -> None:
        self._all: tuple[AggregateDescriptor, ...] = tuple(descriptors)
        aliases: dict[str, AggregateDescriptor] = {}
        categories: dict[str, AggregateDescriptor] = {}
        for descriptor in self._all:
            self._register(descriptor, aliases, categories)
        self._by_alias = aliases
        self._by_category = categories

    @classmethod
    def from_descriptors(
        cls, descriptors: Iterable[AggregateDescriptor]
    ) -> "OntologyRegistry":
        return cls(descriptors)

    @staticmethod
    def _register(
        descriptor: AggregateDescriptor,
        aliases: dict[str, AggregateDescriptor],
        categories: dict[str, AggregateDescriptor],
    ) -> None:
        if descriptor.alias:
            aliases[descriptor.alias] = descriptor
        if descriptor.category:
            categories[descriptor.category] = descriptor
        for child in descriptor.sub_entities:
            OntologyRegistry._register(child, aliases, categories)

    def by_alias(self, alias: str) -> AggregateDescriptor | None:
        return self._by_alias.get(alias)

    def by_category(self, category: str) -> AggregateDescriptor | None:
        return self._by_category.get(category)

    def categories(self) -> tuple[str, ...]:
        return tuple(self._by_category)

    def by_tag(self, tag: str) -> tuple[AggregateDescriptor, ...]:
        return tuple(item for item in self._all if tag in item.tags)

    def all(self) -> tuple[AggregateDescriptor, ...]:
        return self._all

    def size(self) -> int:
        return len(self._all)
