"""流程包路由。

端点路径/方法/参数名与 Java 版保持一致：
- ``/api/flow/health``（保留 P0 占位）
- ``/api/workline``（WorklineController）
- ``/api/aggregation``（AggregationController）
- ``/api/global``（GlobalKnowledgeController）
- ``/api/workspace``（WorkspaceController）
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from dsh_onto_base import fail, ok, require_role, tenant_id_var, user_id_var

from .repository import (
    CATEGORY_MODELS,
    AggregationRepository,
    GlobalKnowledgeRepository,
    WorklineRepository,
    WorkspaceRepository,
)
from .schemas import (
    AggregationStatsOut,
    WorklineContextOut,
    WorklinePhaseResultOut,
)
from .service import (
    AggregationService,
    EntityMergeService,
    WorklineOrchestrator,
    WorklineService,
    WorkspaceService,
)

router = APIRouter(tags=["flow"])

flow_router = APIRouter(prefix="/api/flow", tags=["flow"])
# 角色层级对齐 Java @RequiresRole：workline/workspace=1，aggregation/global=0
workline_router = APIRouter(
    prefix="/api/workline", tags=["flow"], dependencies=[Depends(require_role(1))]
)
aggregation_router = APIRouter(
    prefix="/api/aggregation", tags=["flow"], dependencies=[Depends(require_role(0))]
)
global_router = APIRouter(
    prefix="/api/global", tags=["flow"], dependencies=[Depends(require_role(0))]
)
workspace_router = APIRouter(
    prefix="/api/workspace", tags=["flow"], dependencies=[Depends(require_role(1))]
)


def _tenant_id() -> int | None:
    value = tenant_id_var.get()
    return int(value) if value and value.isdigit() else None


def _created_by() -> str:
    return user_id_var.get() or "anonymous"


def _workline_service(request: Request) -> WorklineService:
    database = request.app.state.database
    return WorklineService(
        WorklineOrchestrator(
            WorklineRepository(database.siis_session, database.onto_session)
        )
    )


def _aggregation_service(request: Request) -> AggregationService:
    database = request.app.state.database
    return AggregationService(
        AggregationRepository(database.siis_session, database.onto_session)
    )


def _merge_service(request: Request) -> EntityMergeService:
    return EntityMergeService(GlobalKnowledgeRepository(request.app.state.database.onto_session))


def _workspace_service(request: Request) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(request.app.state.database.onto_session))


def _context(context) -> dict:
    return WorklineContextOut.model_validate(context).model_dump(mode="json")


def _result(result) -> dict:
    return WorklinePhaseResultOut.model_validate(result).model_dump(mode="json")


def _stats(stats) -> dict:
    return AggregationStatsOut.model_validate(stats).model_dump(mode="json")


# ---------------------------------------------------------------------------
# flow 健康检查（P0 保留）
# ---------------------------------------------------------------------------


@flow_router.get("/health")
async def health() -> dict:
    from . import __version__

    return {"module": "flow", "status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# /api/workline
# ---------------------------------------------------------------------------


@workline_router.post("/topic/{topicId}/activate")
async def activate_topic(topicId: int, request: Request) -> dict:
    context = await _workline_service(request).activate_topic(topicId)
    return ok(_context(context))


@workline_router.get("/{worklineId}/status")
async def get_status(worklineId: str, request: Request) -> dict:
    context = _workline_service(request).get_status(worklineId)
    if context is None:
        return fail(f"工作流不存在: {worklineId}")
    return ok(_context(context))


@workline_router.get("/{worklineId}/progress")
async def get_progress(worklineId: str, request: Request) -> dict:
    results = _workline_service(request).get_progress(worklineId)
    return ok(None if results is None else [_result(item) for item in results])


@workline_router.post("/{worklineId}/phase/{phase}")
async def execute_phase(worklineId: str, phase: str, request: Request) -> dict:
    try:
        result = await _workline_service(request).execute_phase(worklineId, phase.upper())
    except (LookupError, ValueError) as exc:
        return fail(str(exc))
    return ok(_result(result))


@workline_router.post("/{worklineId}/executeUntil/{phase}")
async def execute_until(worklineId: str, phase: str, request: Request) -> dict:
    try:
        results = await _workline_service(request).execute_until(worklineId, phase.upper())
    except (LookupError, ValueError) as exc:
        return fail(str(exc))
    return ok([_result(item) for item in results])


@workline_router.post("/{worklineId}/executeAll")
async def execute_all(worklineId: str, request: Request) -> dict:
    try:
        results = await _workline_service(request).execute_all(worklineId)
    except LookupError as exc:
        return fail(str(exc))
    return ok([_result(item) for item in results])


@workline_router.get("/stages")
async def get_stages() -> dict:
    return ok(WorklineService.get_stages())


# ---------------------------------------------------------------------------
# /api/aggregation
# ---------------------------------------------------------------------------


@aggregation_router.post("/trigger")
async def trigger_full(request: Request) -> dict:
    stats = await _aggregation_service(request).trigger_full_aggregation()
    return ok(_stats(stats))


@aggregation_router.post("/incremental/{tenantId}")
async def trigger_incremental(tenantId: int, request: Request) -> dict:
    stats = await _aggregation_service(request).trigger_manual_incremental(tenantId)
    return ok(_stats(stats))


@aggregation_router.get("/logs")
async def get_logs(
    request: Request, pageNum: int = 1, pageSize: int = 20
) -> dict:
    rows = await _aggregation_service(request).get_aggregation_logs(pageNum, pageSize)
    return ok(rows)


@aggregation_router.get("/unified-monitor")
async def get_unified_monitor(
    request: Request,
    pageNum: int = 1,
    pageSize: int = 20,
    tenantId: int | None = None,
    timeWindowDays: int = 30,
) -> dict:
    rows = await _aggregation_service(request).get_unified_monitor(
        pageNum, pageSize, tenantId, timeWindowDays
    )
    return ok(rows)


@aggregation_router.get("/unified-kg")
async def get_unified_kg(request: Request) -> dict:
    return ok(await _aggregation_service(request).get_unified_kg())


# ---------------------------------------------------------------------------
# /api/global
# ---------------------------------------------------------------------------


@global_router.get("/entities")
async def get_entities(
    request: Request, pageNum: int = 1, pageSize: int = 20
) -> dict:
    return ok(await _aggregation_service(request).get_global_entities(pageNum, pageSize))


@global_router.get("/relations")
async def get_relations(
    request: Request, pageNum: int = 1, pageSize: int = 20
) -> dict:
    return ok(await _aggregation_service(request).get_global_relations(pageNum, pageSize))


@global_router.get("/kg/nodes")
async def get_kg_nodes(
    request: Request, pageNum: int = 1, pageSize: int = 20
) -> dict:
    return ok(await _aggregation_service(request).get_global_kg_nodes(pageNum, pageSize))


@global_router.get("/kg/edges")
async def get_kg_edges(
    request: Request, pageNum: int = 17, pageSize: int = 20
) -> dict:
    return ok(await _aggregation_service(request).get_global_kg_edges(pageNum, pageSize))


@global_router.get("/director/overview")
async def get_director_overview(request: Request) -> dict:
    return ok(await _aggregation_service(request).get_director_overview())


@global_router.post("/entities/merge")
async def merge_entities(body: dict[str, Any], request: Request) -> dict:
    try:
        source_id = int(body["sourceEntityId"])
        target_id = int(body["targetEntityId"])
        entity_type = body.get("entityType")
        score = body.get("similarityScore")
        strategy = body.get("strategy") or "MANUAL"
        log_id = await _merge_service(request).merge_entities(
            source_id,
            target_id,
            entity_type,
            None if score is None else float(score),
            strategy,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return fail(str(exc))
    return ok(log_id)


@global_router.post("/entities/auto-merge")
async def auto_merge(request: Request, tenantId: int) -> dict:
    merged = await _merge_service(request).auto_merge_by_name_match(tenantId)
    return ok(merged)


@global_router.get("/merge-logs")
async def get_merge_logs(
    request: Request, tenantId: int, pageNum: int = 1, pageSize: int = 20
) -> dict:
    rows = await _merge_service(request).get_merge_logs(tenantId, pageNum, pageSize)
    return ok(rows)


# ---------------------------------------------------------------------------
# /api/workspace（GenericCrudController 对应端点）
# ---------------------------------------------------------------------------


@workspace_router.get("/categories")
async def workspace_categories() -> dict:
    return ok(list(CATEGORY_MODELS.keys()))


@workspace_router.get("/search")
async def workspace_search(
    request: Request,
    keyword: str,
    category: str | None = None,
    limit: int = 20,
) -> dict:
    try:
        rows = await _workspace_service(request).search(keyword, category, limit)
    except ValueError as exc:
        return fail(str(exc))
    return ok(rows)


@workspace_router.get("/{category}")
async def workspace_list(category: str, request: Request) -> dict:
    try:
        rows = await _workspace_service(request).find_all(category, _tenant_id())
    except ValueError as exc:
        return fail(str(exc))
    return ok(rows)


@workspace_router.get("/{category}/typed")
async def workspace_list_typed(category: str, request: Request) -> dict:
    try:
        rows = await _workspace_service(request).find_all(category, _tenant_id())
    except ValueError as exc:
        return fail(str(exc))
    return ok(rows)


@workspace_router.get("/{category}/page")
async def workspace_page(
    category: str,
    request: Request,
    pageNum: int = 1,
    pageSize: int = 10,
) -> dict:
    try:
        page = await _workspace_service(request).find_page(
            category, _tenant_id(), pageNum, pageSize
        )
    except ValueError as exc:
        return fail(str(exc))
    return ok(page)


@workspace_router.get("/{category}/count")
async def workspace_count(category: str, request: Request) -> dict:
    try:
        total = await _workspace_service(request).count(category, _tenant_id())
    except ValueError as exc:
        return fail(str(exc))
    return ok(total)


@workspace_router.get("/{category}/{id}")
async def workspace_get(category: str, id: int, request: Request) -> dict:
    try:
        row = await _workspace_service(request).find_by_id(category, _tenant_id(), id)
    except ValueError as exc:
        return fail(str(exc))
    if row is None:
        return fail(f"记录不存在: {id}")
    return ok(row)


@workspace_router.post("/{category}")
async def workspace_create(
    category: str, body: dict[str, Any], request: Request
) -> dict:
    try:
        record_id = await _workspace_service(request).create(
            category, _tenant_id(), _created_by(), body
        )
    except ValueError as exc:
        return fail(str(exc))
    return ok(record_id)


@workspace_router.put("/{category}/{id}")
async def workspace_update(
    category: str, id: int, body: dict[str, Any], request: Request
) -> dict:
    try:
        rows = await _workspace_service(request).update(
            category, _tenant_id(), id, body
        )
    except ValueError as exc:
        return fail(str(exc))
    return ok(rows)


@workspace_router.delete("/{category}/{id}")
async def workspace_delete(category: str, id: int, request: Request) -> dict:
    try:
        rows = await _workspace_service(request).delete(category, _tenant_id(), id)
    except ValueError as exc:
        return fail(str(exc))
    return ok(rows)


@workspace_router.post("/{category}/query")
async def workspace_query(
    category: str,
    body: dict[str, Any],
    request: Request,
    pageNum: int = 1,
    pageSize: int = 10,
) -> dict:
    try:
        rows = await _workspace_service(request).query_by_filters(
            category, _tenant_id(), body, pageNum, pageSize
        )
    except ValueError as exc:
        return fail(str(exc))
    return ok(rows)


router.include_router(flow_router)
router.include_router(workline_router)
router.include_router(aggregation_router)
router.include_router(global_router)
router.include_router(workspace_router)

# 系统层 / 本体管理 / SSE 排障（同属 Java dsh-onto-flow 模块）
from .sys_router import ALL_SYS_ROUTERS  # noqa: E402
from .ontology_router import router as ontology_router  # noqa: E402

for _sys_router in ALL_SYS_ROUTERS:
    router.include_router(_sys_router)
router.include_router(ontology_router)
