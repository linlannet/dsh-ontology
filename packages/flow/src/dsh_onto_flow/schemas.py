"""流程层出入参模型（pydantic），字段与 Java 实体/Map 输出对齐。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StageOut(_Out):
    order: int
    name: str
    code: str


class WorklineContextOut(_Out):
    worklineId: str
    tenantId: int | None = None
    userId: int | None = None
    attributes: dict = {}
    currentPhase: str | None = None
    startTime: datetime | None = None
    endTime: datetime | None = None
    status: str | None = None


class WorklinePhaseResultOut(_Out):
    phase: str
    success: bool
    message: str
    output: dict | None = None
    startTime: datetime | None = None
    endTime: datetime | None = None
    durationMs: int


class AggregationStatsOut(_Out):
    entityCount: int = 0
    relationCount: int = 0
    durationMs: int = 0
    success: bool = False
    errorMsg: str | None = None


class PageResultOut(_Out):
    records: list[dict] = []
    total: int = 0
    pageNum: int = 1
    pageSize: int = 10
    pages: int = 0


class EntityMergeLogOut(_Out):
    """与 Java ``EntityMergeLog`` 的 Jackson 输出（camelCase）对齐。"""

    id: int
    sourceEntityId: int
    targetEntityId: int
    entityType: str | None = None
    similarityScore: float | None = None
    mergeStrategy: str | None = None
    operatorId: int | None = None
    tenantId: int | None = None
    createdBy: str | None = None
    createdAt: datetime | None = None
    updatedBy: str | None = None
    updatedAt: datetime | None = None
    delFlag: int | None = None
    remark: str | None = None
