"""指标层数据访问：统一走平台库 ``onto_engine``（指标表归 ontodb）。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from .models import (
    MetricBusinessObject,
    MetricDecisionPoint,
    MetricDefinition,
    MetricDependency,
    MetricProcess,
)


class MetricRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(self, entity) -> int:
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            return int(entity.id)

    async def _list(self, model, *criteria) -> list:
        async with self._session_factory() as session:
            stmt = select(model).where(model.del_flag == 0, *criteria)
            return list((await session.scalars(stmt)).all())

    async def _one(self, model, *criteria):
        async with self._session_factory() as session:
            stmt = select(model).where(model.del_flag == 0, *criteria)
            return (await session.scalars(stmt)).first()

    async def find_all_business_objects(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [MetricBusinessObject.tenant_id == tenant_id]
        return await self._list(MetricBusinessObject, *criteria)

    async def find_business_object_by_id(self, obj_id: int, tenant_id: int | None):
        criteria = [MetricBusinessObject.id == obj_id]
        if tenant_id is not None:
            criteria.append(MetricBusinessObject.tenant_id == tenant_id)
        return await self._one(MetricBusinessObject, *criteria)

    async def find_all_processes(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [MetricProcess.tenant_id == tenant_id]
        return await self._list(MetricProcess, *criteria)

    async def find_processes_by_business_object_id(self, business_object_id: int) -> list:
        return await self._list(
            MetricProcess, MetricProcess.business_object_id == business_object_id
        )

    async def find_all_decision_points(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [MetricDecisionPoint.tenant_id == tenant_id]
        return await self._list(MetricDecisionPoint, *criteria)

    async def find_decision_points_by_process_id(self, process_id: int) -> list:
        return await self._list(MetricDecisionPoint, MetricDecisionPoint.process_id == process_id)

    async def find_all_definitions(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [MetricDefinition.tenant_id == tenant_id]
        return await self._list(MetricDefinition, *criteria)

    async def find_definitions_by_category(self, category: str, tenant_id: int | None) -> list:
        criteria = [MetricDefinition.category == category]
        if tenant_id is not None:
            criteria.append(MetricDefinition.tenant_id == tenant_id)
        return await self._list(MetricDefinition, *criteria)

    async def find_definition_by_id(self, metric_id: int, tenant_id: int | None):
        criteria = [MetricDefinition.id == metric_id]
        if tenant_id is not None:
            criteria.append(MetricDefinition.tenant_id == tenant_id)
        return await self._one(MetricDefinition, *criteria)

    async def find_all_dependencies(self, tenant_id: int | None) -> list:
        criteria = [] if tenant_id is None else [MetricDependency.tenant_id == tenant_id]
        return await self._list(MetricDependency, *criteria)
