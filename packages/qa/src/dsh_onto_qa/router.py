"""报告层路由：端点与 Java ``ReportController`` 一一对应。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from dsh_onto_base import fail, ok, require_role, tenant_id_var, user_id_var

from .models import (
    ReportAnalysisTask,
    ReportInstance,
    ReportQaQuery,
    ReportQaSession,
    ReportTemplate,
)
from .repository import ReportRepository
from .schemas import (
    AnalysisTaskIn,
    ChartDefIn,
    InstanceIn,
    QaQueryIn,
    QaSessionIn,
    SectionIn,
    TemplateIn,
)
from .service import ReportService

_AUDIT_FIELDS = {
    "id",
    "tenant_id",
    "created_by",
    "created_at",
    "updated_by",
    "updated_at",
    "del_flag",
    "remark",
}

router = APIRouter(tags=["qa"])
# Java ReportController 全部端点标注 @RequiresRole(1)
business_router = APIRouter(tags=["qa"], dependencies=[Depends(require_role(1))])
health_router = APIRouter(tags=["qa"])


def _tenant_id() -> int | None:
    value = tenant_id_var.get()
    return int(value) if value and value.isdigit() else None


def _created_by() -> str:
    return user_id_var.get() or "anonymous"


def _service(request: Request) -> ReportService:
    return ReportService(ReportRepository(request.app.state.database.onto_session))


def _dump(items) -> list[dict]:
    return [item.model_dump() for item in items]


@health_router.get("/api/qa/health")
async def health() -> dict:
    from . import __version__

    return {"module": "qa", "status": "ok", "version": __version__}


@business_router.get("/api/report/templates")
async def list_templates(request: Request) -> dict:
    rows = await _service(request).find_all_templates(_tenant_id())
    return ok(_dump(TemplateIn.model_validate(row) for row in rows))


@business_router.get("/api/report/templates/{id}")
async def get_template(id: int, request: Request) -> dict:
    row = await _service(request).find_template_by_id(id, _tenant_id())
    if row is None:
        # Java 版 queryForObject 未命中抛 EmptyResultDataAccessException，统一 404。
        return JSONResponse(status_code=404, content=fail("记录不存在", code=404))
    return ok(TemplateIn.model_validate(row).model_dump())


@business_router.post("/api/report/templates")
async def create_template(body: TemplateIn, request: Request) -> dict:
    entity = ReportTemplate(
        **body.model_dump(exclude=_AUDIT_FIELDS),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_template(entity))


@business_router.get("/api/report/instances")
async def list_instances(request: Request) -> dict:
    rows = await _service(request).find_all_instances(_tenant_id())
    return ok(_dump(InstanceIn.model_validate(row) for row in rows))


@business_router.get("/api/report/instances/{id}")
async def get_instance(id: int, request: Request) -> dict:
    row = await _service(request).find_instance_by_id(id, _tenant_id())
    if row is None:
        return JSONResponse(status_code=404, content=fail("记录不存在", code=404))
    return ok(InstanceIn.model_validate(row).model_dump())


@business_router.post("/api/report/instances")
async def create_instance(body: InstanceIn, request: Request) -> dict:
    entity = ReportInstance(
        **body.model_dump(exclude=_AUDIT_FIELDS),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_instance(entity))


@business_router.post("/api/report/instances/{id}/generate")
async def generate_report(id: int, request: Request) -> dict:
    return ok(await _service(request).generate_report(id))


@business_router.post("/api/report/instances/{id}/publish")
async def publish_report(id: int, request: Request) -> dict:
    return ok(await _service(request).publish_report(id))


@business_router.get("/api/report/instances/{id}/sections")
async def list_sections(id: int, request: Request) -> dict:
    rows = await _service(request).find_sections_by_instance_id(id)
    return ok(_dump(SectionIn.model_validate(row) for row in rows))


@business_router.get("/api/report/templates/{id}/charts")
async def list_charts(id: int, request: Request) -> dict:
    rows = await _service(request).find_charts_by_template_id(id)
    return ok(_dump(ChartDefIn.model_validate(row) for row in rows))


@business_router.get("/api/report/qa/sessions")
async def list_qa_sessions(request: Request) -> dict:
    rows = await _service(request).find_all_qa_sessions(_tenant_id())
    return ok(_dump(QaSessionIn.model_validate(row) for row in rows))


@business_router.post("/api/report/qa/sessions")
async def create_qa_session(body: QaSessionIn, request: Request) -> dict:
    entity = ReportQaSession(
        **body.model_dump(exclude=_AUDIT_FIELDS),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_qa_session(entity))


@business_router.get("/api/report/qa/sessions/{sessionId}/queries")
async def list_qa_queries(sessionId: int, request: Request) -> dict:
    rows = await _service(request).find_qa_queries_by_session_id(sessionId)
    return ok(_dump(QaQueryIn.model_validate(row) for row in rows))


@business_router.post("/api/report/qa/sessions/{sessionId}/queries")
async def create_qa_query(sessionId: int, body: QaQueryIn, request: Request) -> dict:
    entity = ReportQaQuery(
        **body.model_dump(exclude=_AUDIT_FIELDS | {"session_id"}),
        session_id=sessionId,
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_qa_query(entity))


@business_router.get("/api/report/analysis/tasks")
async def list_analysis_tasks(request: Request) -> dict:
    rows = await _service(request).find_all_analysis_tasks(_tenant_id())
    return ok(_dump(AnalysisTaskIn.model_validate(row) for row in rows))


@business_router.post("/api/report/analysis/tasks")
async def create_analysis_task(body: AnalysisTaskIn, request: Request) -> dict:
    entity = ReportAnalysisTask(
        **body.model_dump(exclude=_AUDIT_FIELDS),
        tenant_id=_tenant_id(),
        created_by=_created_by(),
    )
    return ok(await _service(request).create_analysis_task(entity))


@business_router.post("/api/report/analysis/tasks/{id}/complete")
async def complete_analysis_task(id: int, resultSummary: str, request: Request) -> dict:
    return ok(await _service(request).complete_analysis_task(id, resultSummary))


router.include_router(business_router)
router.include_router(health_router)
