"""模型引擎完整性检查，语义对齐 Java ``ModelIntegrityChecker``。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .model import AggregateDescriptor, AttributeDescriptor
from .registry import OntologyRegistry

BASE_ROOT_COUNT = 25
BASE_ATTRIBUTE_COUNT = 200
BASE_ENUM_COUNT = 16
PROJECT_ROOT_COUNT = 27
PROJECT_ATTRIBUTE_COUNT = 292
PROJECT_ENUM_COUNT = 14

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"

REFERENCE_KEYS = ("ownerEntity", "objectRef")


@dataclass(frozen=True)
class IntegrityIssue:
    severity: str
    code: str
    message: str
    source_file: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "sourceFile": self.source_file,
            "path": self.path,
        }


@dataclass(frozen=True)
class IntegrityReport:
    issues: tuple[IntegrityIssue, ...] = ()
    aggregate_count: int = 0
    attribute_count: int = 0
    enum_count: int = 0

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == SEVERITY_ERROR for issue in self.issues)

    def errors(self) -> tuple[IntegrityIssue, ...]:
        return tuple(i for i in self.issues if i.severity == SEVERITY_ERROR)

    def warnings(self) -> tuple[IntegrityIssue, ...]:
        return tuple(i for i in self.issues if i.severity == SEVERITY_WARNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregateCount": self.aggregate_count,
            "attributeCount": self.attribute_count,
            "enumCount": self.enum_count,
            "duplicateAliases": sum(1 for i in self.issues if i.code == "DUPLICATE_ALIAS"),
            "danglingRefs": sum(1 for i in self.issues if i.code == "DANGLING_REFERENCE"),
            "hasErrors": self.has_errors,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class _CheckState:
    issues: list[IntegrityIssue] = field(default_factory=list)
    alias_owners: dict[str, str | None] = field(default_factory=dict)
    ids: set[str] = field(default_factory=set)


class ModelIntegrityChecker:
    """空属性、重复 alias、重复字段、空枚举、悬空引用、基线计数。"""

    def check(self, snapshot: Any) -> IntegrityReport:
        state = _CheckState()
        attribute_count = 0
        enum_count = 0

        for descriptor in snapshot.descriptors:
            attribute_count += descriptor.total_attribute_count()
            enum_count += descriptor.total_enum_count()
            self._collect_ids(descriptor, state.ids)
            self._check_aggregate(descriptor, state)

        self._check_dangling_references(
            snapshot.raw_documents, state.ids, snapshot.project_layer_present, state.issues
        )
        self._check_baseline(
            snapshot.project_layer_present,
            len(snapshot.descriptors),
            attribute_count,
            enum_count,
            state.issues,
        )

        return IntegrityReport(
            issues=tuple(state.issues),
            aggregate_count=len(snapshot.descriptors),
            attribute_count=attribute_count,
            enum_count=enum_count,
        )

    def _check_aggregate(self, descriptor: AggregateDescriptor, state: _CheckState) -> None:
        if not descriptor.attributes:
            state.issues.append(
                IntegrityIssue(
                    SEVERITY_ERROR,
                    "EMPTY_ATTRIBUTES",
                    f"聚合根缺少 attributes: {descriptor.alias}",
                    descriptor.source_file,
                    descriptor.alias,
                )
            )

        previous = state.alias_owners.setdefault(descriptor.alias, descriptor.source_file)
        if previous is not None and previous != descriptor.source_file:
            state.issues.append(
                IntegrityIssue(
                    SEVERITY_ERROR,
                    "DUPLICATE_ALIAS",
                    f"重复 alias {descriptor.alias}（{previous} / {descriptor.source_file}）",
                    descriptor.source_file,
                    descriptor.alias,
                )
            )

        field_names: set[str] = set()
        for attribute in descriptor.attributes:
            if attribute.name in field_names:
                state.issues.append(
                    IntegrityIssue(
                        SEVERITY_ERROR,
                        "DUPLICATE_FIELD",
                        f"重复字段 {descriptor.alias}.{attribute.name}",
                        descriptor.source_file,
                        descriptor.alias,
                    )
                )
            field_names.add(attribute.name)
            self._check_empty_enum(descriptor, attribute, state.issues)

        for child in descriptor.sub_entities:
            self._check_aggregate(child, state)

    @staticmethod
    def _check_empty_enum(
        descriptor: AggregateDescriptor,
        attribute: AttributeDescriptor,
        issues: list[IntegrityIssue],
    ) -> None:
        if attribute.type == "Enum" and not attribute.enum_values:
            issues.append(
                IntegrityIssue(
                    SEVERITY_ERROR,
                    "EMPTY_ENUM",
                    f"枚举字段缺少 enumValues: {descriptor.alias}.{attribute.name}",
                    descriptor.source_file,
                    descriptor.alias,
                )
            )

    def _collect_ids(self, descriptor: AggregateDescriptor, ids: set[str]) -> None:
        if descriptor.id:
            ids.add(descriptor.id)
        for child in descriptor.sub_entities:
            self._collect_ids(child, ids)

    def _check_dangling_references(
        self,
        documents: Sequence[Mapping[str, Any]],
        ids: set[str],
        project_present: bool,
        issues: list[IntegrityIssue],
    ) -> None:
        severity = SEVERITY_ERROR if project_present else SEVERITY_WARNING
        for document in documents:
            self._scan_references(document, ids, severity, issues)

    def _scan_references(
        self,
        node: Any,
        ids: set[str],
        severity: str,
        issues: list[IntegrityIssue],
    ) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if (
                    key in REFERENCE_KEYS
                    and isinstance(value, str)
                    and value.strip()
                    and value not in ids
                ):
                    issues.append(
                        IntegrityIssue(
                            severity,
                            "DANGLING_REFERENCE",
                            f"悬空引用: {value}",
                            None,
                            key,
                        )
                    )
                self._scan_references(value, ids, severity, issues)
        elif isinstance(node, (list, tuple)):
            for item in node:
                self._scan_references(item, ids, severity, issues)

    @staticmethod
    def _check_baseline(
        project_present: bool,
        roots: int,
        attributes: int,
        enums: int,
        issues: list[IntegrityIssue],
    ) -> None:
        expected_roots = BASE_ROOT_COUNT + (PROJECT_ROOT_COUNT if project_present else 0)
        expected_attributes = BASE_ATTRIBUTE_COUNT + (
            PROJECT_ATTRIBUTE_COUNT if project_present else 0
        )
        expected_enums = BASE_ENUM_COUNT + (PROJECT_ENUM_COUNT if project_present else 0)
        if roots < expected_roots:
            issues.append(
                IntegrityIssue(
                    SEVERITY_WARNING,
                    "BASELINE_ROOT_DRIFT",
                    f"聚合根数下降: {roots} < {expected_roots}",
                    None,
                    "aggregates",
                )
            )
        if attributes < expected_attributes:
            issues.append(
                IntegrityIssue(
                    SEVERITY_WARNING,
                    "BASELINE_FIELD_DRIFT",
                    f"字段数下降: {attributes} < {expected_attributes}",
                    None,
                    "attributes",
                )
            )
        if enums < expected_enums:
            issues.append(
                IntegrityIssue(
                    SEVERITY_WARNING,
                    "BASELINE_ENUM_DRIFT",
                    f"枚举字段数下降: {enums} < {expected_enums}",
                    None,
                    "enumValues",
                )
            )
