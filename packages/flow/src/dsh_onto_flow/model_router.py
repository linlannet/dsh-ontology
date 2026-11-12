"""模型元数据只读 API（``/api/model``），字段与 Java 0.2.2 / OpenAPI 基线一致。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dsh_onto_base import ok, require_role
from dsh_onto_base.ontology import OntologyModelEngine

_DISABLED_MSG = "模型引擎未启用（dsh.ontology.model.enabled=false）"


class Result(BaseModel):
    code: int
    msg: str
    data: Any = None


class AttributeDescriptor(BaseModel):
    name: str
    label: str | None = None
    type: str | None = None
    required: bool = False
    unique: bool = False
    enumValues: list[str] = Field(default_factory=list)
    defaultValue: str | None = None
    description: str | None = None


class AggregateDescriptor(BaseModel):
    id: str | None = None
    name: str | None = None
    alias: str | None = None
    category: str | None = None
    lifecycle: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    attributes: list[AttributeDescriptor] = Field(default_factory=list)
    subEntities: list["AggregateDescriptor"] = Field(default_factory=list)
    sourceFile: str | None = None


AggregateDescriptor.model_rebuild()


class AggregateVO(BaseModel):
    alias: str
    name: str | None = None
    category: str | None = None
    attributeCount: int = 0


class DomainGroupVO(BaseModel):
    tag: str
    aggregateCount: int
    aggregates: list[AggregateVO] = Field(default_factory=list)


class ManifestVO(BaseModel):
    platform: str | None = None
    baseVersion: str | None = None
    projectVersion: str | None = None
    baseModels: list[str] = Field(default_factory=list)
    projectModelCount: int = 0
    aggregateCount: int = 0
    attributeCount: int = 0
    enumCount: int = 0
    projectLayerPresent: bool = False


class IntegrityIssue(BaseModel):
    severity: str
    code: str
    message: str
    sourceFile: str | None = None
    path: str | None = None


class IntegrityVO(BaseModel):
    aggregateCount: int = 0
    attributeCount: int = 0
    enumCount: int = 0
    duplicateAliases: int = 0
    danglingRefs: int = 0
    hasErrors: bool = False
    issues: list[IntegrityIssue] = Field(default_factory=list)


class ResultManifest(Result):
    data: ManifestVO | None = None


class ResultDomainGroups(Result):
    data: list[DomainGroupVO] | None = None


class ResultAggregate(Result):
    data: AggregateDescriptor | None = None


class ResultIntegrity(Result):
    data: IntegrityVO | None = None


def _error_responses() -> dict[int | str, dict[str, Any]]:
    schema = Result.model_json_schema()
    return {
        401: {
            "description": "未认证或登录已过期",
            "content": {"application/json": {"schema": schema}},
        },
        403: {
            "description": "无权限访问",
            "content": {"application/json": {"schema": schema}},
        },
    }


_ERROR_RESPONSES = _error_responses()

router = APIRouter(
    prefix="/api/model",
    tags=["model"],
    dependencies=[Depends(require_role(1))],
)


def _engine(request: Request) -> OntologyModelEngine:
    engine = getattr(request.app.state, "ontology_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail=_DISABLED_MSG)
    return engine


@router.get("/manifest", response_model=ResultManifest, responses=_ERROR_RESPONSES)
async def manifest(request: Request) -> dict:
    engine = _engine(request)
    manifests = engine.manifests
    base = manifests[0] if manifests else None
    project = manifests[1] if len(manifests) > 1 else None
    project_model_count = sum(
        1 for file in engine.source_files if file.startswith("siis-models/")
    )
    report = engine.report
    return ok(
        {
            "platform": base.platform if base else None,
            "baseVersion": base.version if base else None,
            "projectVersion": project.version if project else None,
            "baseModels": list(base.base_models) if base else [],
            "projectModelCount": project_model_count,
            "aggregateCount": report.aggregate_count,
            "attributeCount": report.attribute_count,
            "enumCount": report.enum_count,
            "projectLayerPresent": engine.project_layer_present,
        }
    )


@router.get("/aggregates", response_model=ResultDomainGroups, responses=_ERROR_RESPONSES)
async def aggregates(request: Request) -> dict:
    engine = _engine(request)
    grouped: dict[str, list[dict[str, Any]]] = {}
    seen: dict[str, set[str]] = {}
    for descriptor in engine.registry.all():
        tags = descriptor.tags or ("未分组",)
        vo = {
            "alias": descriptor.alias,
            "name": descriptor.name,
            "category": descriptor.category,
            "attributeCount": descriptor.total_attribute_count(),
        }
        for tag in tags:
            grouped.setdefault(tag, [])
            if descriptor.alias not in seen.setdefault(tag, set()):
                seen[tag].add(descriptor.alias)
                grouped[tag].append(vo)

    groups = [
        {"tag": tag, "aggregateCount": len(items), "aggregates": items}
        for tag, items in grouped.items()
    ]
    return ok(groups)


@router.get(
    "/aggregates/{alias}", response_model=ResultAggregate, responses=_ERROR_RESPONSES
)
async def aggregate(alias: str, request: Request) -> dict:
    engine = _engine(request)
    descriptor = engine.registry.by_alias(alias)
    if descriptor is None:
        raise HTTPException(status_code=404, detail=f"未知聚合根: {alias}")
    return ok(descriptor.to_dict())


@router.get("/integrity", response_model=ResultIntegrity, responses=_ERROR_RESPONSES)
async def integrity(request: Request) -> dict:
    engine = _engine(request)
    return ok(engine.report.to_dict())
