"""报告层服务：默认值填充与状态流转，逻辑与 Java ``ReportService`` 对齐。"""

from __future__ import annotations

from datetime import datetime

from .repository import ReportRepository


class ReportService:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    async def find_all_templates(self, tenant_id: int | None):
        return await self._repository.find_all_templates(tenant_id)

    async def find_template_by_id(self, template_id: int, tenant_id: int | None):
        return await self._repository.find_template_by_id(template_id, tenant_id)

    async def create_template(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else 0
        return await self._repository.create(entity)

    async def find_all_instances(self, tenant_id: int | None):
        return await self._repository.find_all_instances(tenant_id)

    async def find_instance_by_id(self, instance_id: int, tenant_id: int | None):
        return await self._repository.find_instance_by_id(instance_id, tenant_id)

    async def create_instance(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else "DRAFT"
        return await self._repository.create(entity)

    async def generate_report(self, instance_id: int) -> int:
        return await self._repository.update_instance_status(
            instance_id, "GENERATED", datetime.now()
        )

    async def publish_report(self, instance_id: int) -> int:
        return await self._repository.update_instance_status(
            instance_id, "PUBLISHED", datetime.now()
        )

    async def find_sections_by_instance_id(self, instance_id: int):
        return await self._repository.find_sections_by_instance_id(instance_id)

    async def find_charts_by_template_id(self, template_id: int):
        return await self._repository.find_charts_by_template_id(template_id)

    async def find_all_qa_sessions(self, tenant_id: int | None):
        return await self._repository.find_all_qa_sessions(tenant_id)

    async def create_qa_session(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else "ACTIVE"
        return await self._repository.create(entity)

    async def find_qa_queries_by_session_id(self, session_id: int):
        return await self._repository.find_qa_queries_by_session_id(session_id)

    async def create_qa_query(self, entity) -> int:
        entity.process_status = (
            entity.process_status if entity.process_status is not None else "PENDING"
        )
        return await self._repository.create(entity)

    async def find_all_analysis_tasks(self, tenant_id: int | None):
        return await self._repository.find_all_analysis_tasks(tenant_id)

    async def create_analysis_task(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else "PENDING"
        return await self._repository.create(entity)

    async def complete_analysis_task(self, task_id: int, result_summary: str) -> int:
        return await self._repository.update_analysis_task_status(
            task_id, "SUCCESS", result_summary, datetime.now()
        )
