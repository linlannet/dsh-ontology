"""指标层出入参模型（pydantic），字段与 Java 实体对齐。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    tenant_id: int | None = None
    created_by: str | None = None
    remark: str | None = None


class BusinessObjectIn(_Base):
    object_name: str
    object_code: str
    object_type: str | None = None
    source_table: str | None = None
    description: str | None = None
    status: int | None = 0


class ProcessIn(_Base):
    process_name: str
    process_code: str
    business_object_id: int | None = None
    node_config: str | None = None
    description: str | None = None
    status: int | None = 0


class DecisionPointIn(_Base):
    point_name: str
    process_id: int | None = None
    node_index: int | None = 0
    decision_type: str | None = None
    description: str | None = None
    status: int | None = 0


class DefinitionIn(_Base):
    metric_name: str
    metric_code: str
    category: str
    business_object_id: int | None = None
    process_id: int | None = None
    decision_point_id: int | None = None
    formula: str | None = None
    unit: str | None = None
    description: str | None = None
    status: int | None = 0


class DependencyIn(_Base):
    downstream_metric_id: int
    upstream_metric_id: int
    dependency_type: str | None = "DIRECT"
    weight: float | None = 1.0


class TreeNodeOut(BaseModel):
    """依赖树节点，与 Java ``MetricService.MetricTreeNode`` 对齐。"""

    metricId: int
    depth: int
    children: list["TreeNodeOut"] = []
