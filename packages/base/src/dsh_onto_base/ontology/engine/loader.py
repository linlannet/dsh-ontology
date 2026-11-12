"""七模型 YAML 加载器：``importlib.resources`` 定位 + ``yaml.safe_load``。

只负责解析和结构转换；完整性诊断由 ``integrity`` 承担。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import yaml

from .model import AggregateDescriptor, AttributeDescriptor, ModelManifest

BASE_MANIFEST = "ontology-models/manifest.json"
PROJECT_MANIFEST = "siis-models/manifest.json"
BASE_PREFIX = "ontology-models/"
PROJECT_PREFIX = "siis-models/"

# 存量 YAML alias → category 兼容映射，与 Java TypeCatalog 一致。
ALIAS_TO_CATEGORY: dict[str, str] = {
    "OntologyCountry": "country",
    "OntologyOrganization": "organization",
    "OntologyPerson": "person",
    "OntologyHotspot": "hotspot",
    "OntologyMedia": "media",
    "OntologyBook": "book",
    "OntologyPaper": "paper",
    "OntologyBilateralRelation": "bilateralRelation",
    "OntologyLocation": "location",
    "OntologyTerm": "term",
    "OntologyEventType": "eventType",
    "OntologyEntity": "entity",
    "OntologyVersion": "version",
    "OntologyI18n": "i18n",
}

ResourceProvider = Callable[[str], "str | None"]


class ModelLoadError(Exception):
    """模型加载失败；携带相对资源名与行号，对外不泄露绝对路径。"""

    def __init__(
        self,
        message: str,
        file: str | None = None,
        path: str | None = None,
        line: int = -1,
    ) -> None:
        self.file = file
        self.path = path
        self.line = line
        location = ""
        if file:
            location = f" [{file}"
            if path:
                location += f"#{path}"
            if line > 0:
                location += f":{line}"
            location += "]"
        super().__init__(f"{message}{location}")


@dataclass(frozen=True)
class EngineSnapshot:
    """一次加载的完整快照。"""

    descriptors: tuple[AggregateDescriptor, ...] = ()
    manifests: tuple[ModelManifest, ...] = ()
    raw_documents: tuple[dict[str, Any], ...] = ()
    source_files: tuple[str, ...] = ()
    project_layer_present: bool = False


def _default_provider(name: str) -> str | None:
    """从 ``dsh_onto_base/resources`` 读取文本资源。"""
    from importlib.resources import files

    target = files("dsh_onto_base").joinpath("resources")
    for part in name.split("/"):
        target = target.joinpath(part)
    try:
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None


class ModelLoader:
    """读取基座（可选项目层）清单与模型 YAML，产出不可变 ``EngineSnapshot``。"""

    def __init__(self, resources: Mapping[str, str] | ResourceProvider | None = None) -> None:
        if resources is None:
            self._provider: ResourceProvider = _default_provider
        elif callable(resources):
            self._provider = resources
        else:
            self._provider = resources.get

    def load(self) -> EngineSnapshot:
        manifests: list[ModelManifest] = []
        raw_documents: list[dict[str, Any]] = []
        source_files: list[str] = []
        descriptors: list[AggregateDescriptor] = []
        alias_to_file: dict[str, str] = {}

        base_doc = self._read_manifest_document(BASE_MANIFEST)
        base = self._to_manifest(BASE_MANIFEST, base_doc)
        if not base.base_models:
            raise ModelLoadError("基座清单 base_models 为空", BASE_MANIFEST, "base_models")
        manifests.append(base)
        self._load_models(
            BASE_PREFIX,
            base.base_models,
            raw_documents,
            source_files,
            descriptors,
            alias_to_file,
        )

        project_present = self._provider(PROJECT_MANIFEST) is not None
        if project_present:
            project_doc = self._read_manifest_document(PROJECT_MANIFEST)
            models = _string_list(project_doc.get("models"))
            if not models:
                raise ModelLoadError("项目清单 models 为空", PROJECT_MANIFEST, "models")
            manifests.append(self._to_manifest(PROJECT_MANIFEST, project_doc))
            self._load_models(
                PROJECT_PREFIX,
                models,
                raw_documents,
                source_files,
                descriptors,
                alias_to_file,
            )

        return EngineSnapshot(
            descriptors=tuple(descriptors),
            manifests=tuple(manifests),
            raw_documents=tuple(raw_documents),
            source_files=tuple(source_files),
            project_layer_present=project_present,
        )

    def _load_models(
        self,
        prefix: str,
        models: tuple[str, ...],
        raw_documents: list[dict[str, Any]],
        source_files: list[str],
        descriptors: list[AggregateDescriptor],
        alias_to_file: dict[str, str],
    ) -> None:
        for model in models:
            file = prefix + model
            text = self._read_text(file)
            self._detect_bare_blocks(file, text)
            document = self._parse_yaml(file, text)
            self._require_header(file, document)
            raw_documents.append(document)
            source_files.append(file)
            for index, node in enumerate(self._entities_of(file, document)):
                descriptor = self._to_aggregate(node, file, f"aggregates[{index}]")
                self._register_alias(descriptor, file, alias_to_file)
                descriptors.append(descriptor)

    def _detect_bare_blocks(self, file: str, text: str) -> None:
        """检测顶层序列中形如 ``- {name, type}`` 的裸属性块（缺少父实体 alias）。"""
        try:
            root = yaml.compose(text)
        except yaml.YAMLError as exc:
            raise ModelLoadError(
                f"YAML 语法错误: {_problem_text(exc)}", file, "$", _problem_line(exc)
            ) from exc
        if not isinstance(root, yaml.MappingNode):
            return
        for key_node, value_node in root.value:
            if not isinstance(key_node, yaml.ScalarNode) or not isinstance(
                value_node, yaml.SequenceNode
            ):
                continue
            for item in value_node.value:
                if not isinstance(item, yaml.MappingNode):
                    continue
                keys = {
                    node.value
                    for node, _ in item.value
                    if isinstance(node, yaml.ScalarNode)
                }
                if "alias" not in keys and "name" in keys and "type" in keys:
                    raise ModelLoadError(
                        "裸属性块：缺少父实体 alias",
                        file,
                        key_node.value,
                        item.start_mark.line + 1,
                    )

    def _read_text(self, file: str) -> str:
        text = self._provider(file)
        if text is None:
            raise ModelLoadError("资源缺失", file, "$")
        return text

    def _read_manifest_document(self, file: str) -> dict[str, Any]:
        text = self._read_text(file)
        try:
            document = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise ModelLoadError(f"清单解析失败: {exc}", file, "$") from exc
        if not isinstance(document, dict):
            raise ModelLoadError("清单根节点必须是对象", file, "$")
        return document

    def _to_manifest(self, file: str, document: Mapping[str, Any]) -> ModelManifest:
        model_type = _string_or_none(document.get("model_type"))
        if model_type is None:
            raise ModelLoadError("清单缺少 model_type", file, "$")
        version = _string_or_none(document.get("version"))
        if version is None:
            raise ModelLoadError("清单缺少 version", file, "$")
        projects = tuple(
            item for item in document.get("projects") or () if isinstance(item, dict)
        )
        return ModelManifest(
            model_type=model_type,
            version=version,
            platform=_string_or_none(document.get("platform")),
            name=_string_or_none(document.get("name")),
            description=_string_or_none(document.get("description")),
            base_models=tuple(_string_list(document.get("base_models"))),
            projects=projects,
            base_manifest=_string_or_none(document.get("base_manifest")),
            source_file=file,
        )

    def _parse_yaml(self, file: str, text: str) -> dict[str, Any]:
        try:
            document = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ModelLoadError(
                f"YAML 语法错误: {_problem_text(exc)}", file, "$", _problem_line(exc)
            ) from exc
        if document is None:
            raise ModelLoadError("YAML 解析结果为空", file, "$")
        if not isinstance(document, dict):
            raise ModelLoadError("YAML 根节点必须是对象", file, "$")
        return document

    def _require_header(self, file: str, document: Mapping[str, Any]) -> None:
        if document.get("model_type") is None or document.get("version") is None:
            raise ModelLoadError("YAML 根节点缺少 model_type/version", file, "$")

    def _entities_of(self, file: str, document: Mapping[str, Any]) -> list[dict[str, Any]]:
        entities = document.get("entities")
        if entities is None:
            entities = document.get("aggregates")
        if entities is None:
            if document.get("model_type") == "OBJECT":
                raise ModelLoadError("对象模型缺少 entities/aggregates 节点", file, "$")
            return []
        if not isinstance(entities, list):
            raise ModelLoadError("entities 节点必须是列表", file, "entities")
        return [item for item in entities if isinstance(item, dict)]

    def _to_aggregate(self, node: Mapping[str, Any], file: str, path: str) -> AggregateDescriptor:
        alias_value = node.get("alias")
        if alias_value is None:
            raise ModelLoadError("实体缺少 alias", file, path)
        alias = _scalar_text(alias_value)
        category_value = node.get("category")
        category = (
            _scalar_text(category_value)
            if category_value is not None
            else ALIAS_TO_CATEGORY.get(alias)
        )

        attributes: list[AttributeDescriptor] = []
        raw_attributes = node.get("attributes")
        if isinstance(raw_attributes, list):
            for index, item in enumerate(raw_attributes):
                if isinstance(item, dict):
                    attributes.append(
                        self._to_attribute(item, file, f"{path}.attributes[{index}]")
                    )

        children: list[AggregateDescriptor] = []
        raw_children = node.get("entities")
        if isinstance(raw_children, list):
            for index, item in enumerate(raw_children):
                if isinstance(item, dict):
                    children.append(
                        self._to_aggregate(item, file, f"{path}.entities[{index}]")
                    )

        return AggregateDescriptor(
            id=_string_or_none(node.get("id")),
            name=_string_or_none(node.get("name")),
            alias=alias,
            category=category,
            lifecycle=tuple(_string_list(node.get("lifecycle"))),
            tags=tuple(_string_list(node.get("tags"))),
            attributes=tuple(attributes),
            sub_entities=tuple(children),
            source_file=file,
        )

    def _to_attribute(
        self, node: Mapping[str, Any], file: str, path: str
    ) -> AttributeDescriptor:
        name = node.get("name")
        if name is None:
            raise ModelLoadError("字段缺少 name", file, path)
        default = node.get("defaultValue") if "defaultValue" in node else node.get("default")
        return AttributeDescriptor(
            name=_scalar_text(name),
            label=_string_or_none(node.get("label")),
            type=_string_or_none(node.get("type")),
            required=node.get("required") is True,
            unique=node.get("unique") is True,
            enum_values=tuple(_string_list(node.get("enumValues"))),
            default_value=_string_or_none(default),
            description=_string_or_none(node.get("description")),
            source_path=f"{file}:{path}",
        )

    def _register_alias(
        self,
        descriptor: AggregateDescriptor,
        file: str,
        alias_to_file: dict[str, str],
    ) -> None:
        previous = alias_to_file.get(descriptor.alias)
        if previous is not None:
            raise ModelLoadError(
                f"重复 alias: {descriptor.alias}（已定义于 {previous}）", file, descriptor.alias
            )
        alias_to_file[descriptor.alias] = file
        for child in descriptor.sub_entities:
            self._register_alias(child, file, alias_to_file)


def _problem_line(exc: yaml.YAMLError) -> int:
    mark = getattr(exc, "problem_mark", None)
    return -1 if mark is None else mark.line + 1


def _problem_text(exc: yaml.YAMLError) -> str:
    problem = getattr(exc, "problem", None)
    return str(problem or exc)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_scalar_text(item) for item in value if item is not None]


def _string_or_none(value: Any) -> str | None:
    return None if value is None else _scalar_text(value)


def _scalar_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
