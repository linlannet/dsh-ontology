"""指标层路由：端点与 Java ``MetricController`` 一一对应。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from dsh_onto_base import fail, ok, require_role, tenant_id_var, user_id_var

from .models import (
    MetricBusinessObject,
    MetricDecisionPoint,
    MetricDefinition,
    MetricDependency,
    MetricProcess,
)
from .repository import MetricRepository
from .schemas import (
    BusinessObjectIn,
    DecisionPointIn,
    DefinitionIn,
    DependencyIn,
    ProcessIn,
    TreeNodeOut,
)
from .service import MetricService, MetricTreeNode

router = APIRouter(tags=["metric"])
# Java MetricController 全部端点标注 @RequiresRole(1)
business_router = APIRouter(
    prefix="/api/metric", tags=["metric"], dependencies=[Depends(require_role(1))]
)
health_router = APIRouter(prefix="/api/metric", tags=["metric"])


def _tenant_id() -> int | None:
    value = tenant_id_var.get()
    return int(value) if value and value.isdigit() else None


def _created_by() -> str:
    return user_id_var.get() or "anonymous"


def _service(request: Request) -> MetricService:
    return MetricService(MetricRepository(request.app.state.database.onto_session))


def _dump(items) -> list[dict]:
    return [item.model_dump() for item in items]


def _tree(node: MetricTreeNode) -> TreeNodeOut:
    return TreeNodeOut(
        metricId=node.metricId,
        depth=node.depth,
        children=[_tree(child) for child in node.children],
    )


@health_router.get("/health")
async def health() -> dict:
    from . import __version__

    return {"module": "metric", "status": "ok", "version": __version__}


@business_router.get("/business-objects")
async def list_business_objects(request: Request) -> dict:
    rows = await _service(request).find_all_business_objects(_tenant_id())
    return ok(_dump(BusinessObjectIn.model_validate(row) for row in rows))


@business_router.post("/business-objects")
async def create_business_object(body: BusinessObjectIn, request: Request) -> dict:
    entity = MetricBusinessObject(
        **body.model_dump(exclude={"id", "tenant_id", "created_by"}),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_business_object(entity))


@business_router.get("/processes")
async def list_processes(request: Request) -> dict:
    rows = await _service(request).find_all_processes(_tenant_id())
    return ok(_dump(ProcessIn.model_validate(row) for row in rows))


@business_router.get("/business-objects/{bo_id}/processes")
async def list_processes_by_business_object(bo_id: int, request: Request) -> dict:
    rows = await _service(request).find_processes_by_business_object_id(bo_id)
    return ok(_dump(ProcessIn.model_validate(row) for row in rows))


@business_router.post("/processes")
async def create_process(body: ProcessIn, request: Request) -> dict:
    entity = MetricProcess(
        **body.model_dump(exclude={"id", "tenant_id", "created_by"}),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_process(entity))


@business_router.get("/decision-points")
async def list_decision_points(request: Request) -> dict:
    rows = await _service(request).find_all_decision_points(_tenant_id())
    return ok(_dump(DecisionPointIn.model_validate(row) for row in rows))


@business_router.get("/processes/{process_id}/decision-points")
async def list_decision_points_by_process(process_id: int, request: Request) -> dict:
    rows = await _service(request).find_decision_points_by_process_id(process_id)
    return ok(_dump(DecisionPointIn.model_validate(row) for row in rows))


@business_router.post("/decision-points")
async def create_decision_point(body: DecisionPointIn, request: Request) -> dict:
    entity = MetricDecisionPoint(
        **body.model_dump(exclude={"id", "tenant_id", "created_by"}),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_decision_point(entity))


@business_router.get("/definitions")
async def list_definitions(request: Request, category: str | None = None) -> dict:
    tenant = _tenant_id()
    service = _service(request)
    rows = (
        await service.find_definitions_by_category(category, tenant)
        if category
        else await service.find_all_definitions(tenant)
    )
    return ok(_dump(DefinitionIn.model_validate(row) for row in rows))


@business_router.get("/definitions/{metric_id}")
async def get_definition(metric_id: int, request: Request) -> dict:
    row = await _service(request).find_definition_by_id(metric_id, _tenant_id())
    if row is None:
        # 对齐 Java 版 queryForObject 未命中 → EmptyResultDataAccessException → 404。
        return JSONResponse(status_code=404, content=fail("记录不存在", code=404))
    return ok(DefinitionIn.model_validate(row).model_dump())


@business_router.post("/definitions")
async def create_definition(body: DefinitionIn, request: Request) -> dict:
    entity = MetricDefinition(
        **body.model_dump(exclude={"id", "tenant_id", "created_by"}),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_definition(entity))


@business_router.get("/dependencies")
async def list_dependencies(request: Request) -> dict:
    rows = await _service(request).find_all_dependencies(_tenant_id())
    return ok(_dump(DependencyIn.model_validate(row) for row in rows))


@business_router.post("/dependencies")
async def create_dependency(body: DependencyIn, request: Request) -> dict:
    entity = MetricDependency(
        **body.model_dump(exclude={"id", "tenant_id", "created_by"}),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_dependency(entity))


@business_router.get("/definitions/{metric_id}/dependency-tree")
async def get_dependency_tree(metric_id: int, request: Request) -> dict:
    tree = await _service(request).build_dependency_tree(metric_id, _tenant_id())
    return ok(_tree(tree))


router.include_router(business_router)
router.include_router(health_router)
