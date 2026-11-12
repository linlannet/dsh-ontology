"""报告层数据访问：统一走平台库 ``onto_engine``（报告表归 ontodb）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from .models import (
    ReportAnalysisTask,
    ReportChartDef,
    ReportInstance,
    ReportQaQuery,
    ReportQaSession,
    ReportSection,
    ReportTemplate,
)


class ReportRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(self, entity) -> int:
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            return int(entity.id)

    async def _list(self, model, *criteria, order_by=None, descending: bool = True) -> list:
        async with self._session_factory() as session:
            stmt = select(model).where(model.del_flag == 0, *criteria)
            if order_by is not None:
                stmt = stmt.order_by(order_by.desc() if descending else order_by.asc())
            return list((await session.scalars(stmt)).all())

    async def _one(self, model, *criteria):
        async with self._session_factory() as session:
            stmt = select(model).where(model.del_flag == 0, *criteria)
            return (await session.scalars(stmt)).first()

    async def find_all_templates(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [ReportTemplate.tenant_id == tenant_id]
        return await self._list(ReportTemplate, *criteria, order_by=ReportTemplate.created_at)

    async def find_template_by_id(self, template_id: int, tenant_id: int | None):
        criteria = [ReportTemplate.id == template_id]
        if tenant_id is not None:
            criteria.append(ReportTemplate.tenant_id == tenant_id)
        return await self._one(ReportTemplate, *criteria)

    async def find_all_instances(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [ReportInstance.tenant_id == tenant_id]
        return await self._list(ReportInstance, *criteria, order_by=ReportInstance.created_at)

    async def find_instance_by_id(self, instance_id: int, tenant_id: int | None):
        criteria = [ReportInstance.id == instance_id]
        if tenant_id is not None:
            criteria.append(ReportInstance.tenant_id == tenant_id)
        return await self._one(ReportInstance, *criteria)

    async def update_instance_status(self, instance_id: int, status: str, moment: datetime) -> int:
        column = (
            ReportInstance.generated_time
            if status == "GENERATED"
            else ReportInstance.published_time
        )
        stmt = (
            update(ReportInstance)
            .where(ReportInstance.id == instance_id)
            .values(status=status, updated_at=moment, **{column.name: moment})
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
            return int(result.rowcount or 0)

    async def find_sections_by_instance_id(self, instance_id: int) -> list:
        return await self._list(
            ReportSection,
            ReportSection.instance_id == instance_id,
            order_by=ReportSection.section_index,
            descending=False,
        )

    async def find_charts_by_template_id(self, template_id: int) -> list:
        return await self._list(
            ReportChartDef,
            ReportChartDef.template_id == template_id,
            order_by=ReportChartDef.created_at,
        )

    async def find_all_qa_sessions(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [ReportQaSession.tenant_id == tenant_id]
        return await self._list(ReportQaSession, *criteria, order_by=ReportQaSession.created_at)

    async def find_qa_queries_by_session_id(self, session_id: int) -> list:
        return await self._list(
            ReportQaQuery,
            ReportQaQuery.session_id == session_id,
            order_by=ReportQaQuery.created_at,
            descending=False,
        )

    async def find_all_analysis_tasks(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [ReportAnalysisTask.tenant_id == tenant_id]
        return await self._list(
            ReportAnalysisTask, *criteria, order_by=ReportAnalysisTask.created_at
        )

    async def update_analysis_task_status(
        self,
        task_id: int,
        status: str,
        result_summary: str | None,
        end_time: datetime | None,
    ) -> int:
        stmt = (
            update(ReportAnalysisTask)
            .where(ReportAnalysisTask.id == task_id)
            .values(
                status=status,
                result_summary=result_summary,
                end_time=end_time,
                updated_at=datetime.now(),
            )
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
            return int(result.rowcount or 0)
