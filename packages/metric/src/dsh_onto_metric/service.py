"""指标层服务：默认值填充与依赖树构建，逻辑与 Java ``MetricService`` 对齐。"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from .repository import MetricRepository


@dataclass
class MetricTreeNode:
    metricId: int
    depth: int
    children: list["MetricTreeNode"] = field(default_factory=list)


class MetricService:
    def __init__(self, repository: MetricRepository) -> None:
        self._repository = repository

    async def find_all_business_objects(self, tenant_id: int | None):
        return await self._repository.find_all_business_objects(tenant_id)

    async def find_business_object_by_id(self, obj_id: int, tenant_id: int | None):
        return await self._repository.find_business_object_by_id(obj_id, tenant_id)

    async def create_business_object(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else 0
        return await self._repository.create(entity)

    async def find_all_processes(self, tenant_id: int | None):
        return await self._repository.find_all_processes(tenant_id)

    async def find_processes_by_business_object_id(self, business_object_id: int):
        return await self._repository.find_processes_by_business_object_id(business_object_id)

    async def create_process(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else 0
        return await self._repository.create(entity)

    async def find_all_decision_points(self, tenant_id: int | None):
        return await self._repository.find_all_decision_points(tenant_id)

    async def find_decision_points_by_process_id(self, process_id: int):
        return await self._repository.find_decision_points_by_process_id(process_id)

    async def create_decision_point(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else 0
        entity.node_index = entity.node_index if entity.node_index is not None else 0
        return await self._repository.create(entity)

    async def find_all_definitions(self, tenant_id: int | None):
        return await self._repository.find_all_definitions(tenant_id)

    async def find_definitions_by_category(self, category: str, tenant_id: int | None):
        return await self._repository.find_definitions_by_category(category, tenant_id)

    async def find_definition_by_id(self, metric_id: int, tenant_id: int | None):
        return await self._repository.find_definition_by_id(metric_id, tenant_id)

    async def create_definition(self, entity) -> int:
        entity.status = entity.status if entity.status is not None else 0
        return await self._repository.create(entity)

    async def find_all_dependencies(self, tenant_id: int | None):
        return await self._repository.find_all_dependencies(tenant_id)

    async def create_dependency(self, entity) -> int:
        entity.dependency_type = entity.dependency_type or "DIRECT"
        entity.weight = entity.weight if entity.weight is not None else 1.0
        return await self._repository.create(entity)

    async def build_dependency_tree(self, root_metric_id: int, tenant_id: int | None) -> MetricTreeNode:
        """以指定指标为根，广度优先展开全部上游依赖（被依赖方）。"""
        deps = await self._repository.find_all_dependencies(tenant_id)
        upstream_map: dict[int, list[int]] = defaultdict(list)
        for dep in deps:
            upstream_map[dep.downstream_metric_id].append(dep.upstream_metric_id)

        root = MetricTreeNode(root_metric_id, 0)
        queue = deque([root])
        visited = {root_metric_id}
        while queue:
            node = queue.popleft()
            for upstream_id in upstream_map.get(node.metricId, []):
                child = MetricTreeNode(upstream_id, node.depth + 1)
                node.children.append(child)
                if upstream_id not in visited:
                    visited.add(upstream_id)
                    queue.append(child)
        return root
