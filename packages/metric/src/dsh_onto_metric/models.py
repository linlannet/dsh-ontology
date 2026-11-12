"""指标层 ORM 模型：与 Java 版五张 ``onto_metric_*`` 表同名同构。"""

from __future__ import annotations

from datetime import datetime

from dsh_onto_base import Base
from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """公共字段，与平台既有表保持一致。"""

    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    del_flag: Mapped[int | None] = mapped_column(Integer, default=0)
    remark: Mapped[str | None] = mapped_column(String(800))


class MetricBusinessObject(AuditMixin, Base):
    """业务对象（被度量的实体类型）。"""

    __tablename__ = "onto_metric_business_object"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    object_name: Mapped[str] = mapped_column(String(200))
    object_code: Mapped[str] = mapped_column(String(64))
    object_type: Mapped[str | None] = mapped_column(String(32))
    source_table: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(800))
    status: Mapped[int | None] = mapped_column(Integer, default=0)


class MetricProcess(AuditMixin, Base):
    """业务流程。"""

    __tablename__ = "onto_metric_process"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    process_name: Mapped[str] = mapped_column(String(200))
    process_code: Mapped[str] = mapped_column(String(64))
    business_object_id: Mapped[int | None] = mapped_column(BigInteger)
    node_config: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(String(800))
    status: Mapped[int | None] = mapped_column(Integer, default=0)


class MetricDecisionPoint(AuditMixin, Base):
    """关键决策点。"""

    __tablename__ = "onto_metric_decision_point"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    point_name: Mapped[str] = mapped_column(String(200))
    process_id: Mapped[int | None] = mapped_column(BigInteger)
    node_index: Mapped[int | None] = mapped_column(Integer, default=0)
    decision_type: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(800))
    status: Mapped[int | None] = mapped_column(Integer, default=0)


class MetricDefinition(AuditMixin, Base):
    """指标定义（ATOM 原子 / DERIVED 派生 / COMPOSITE 复合）。"""

    __tablename__ = "onto_metric_definition"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(200))
    metric_code: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(16))
    business_object_id: Mapped[int | None] = mapped_column(BigInteger)
    process_id: Mapped[int | None] = mapped_column(BigInteger)
    decision_point_id: Mapped[int | None] = mapped_column(BigInteger)
    formula: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(800))
    status: Mapped[int | None] = mapped_column(Integer, default=0)


class MetricDependency(AuditMixin, Base):
    """指标依赖边：downstream 依赖 upstream。"""

    __tablename__ = "onto_metric_dependency"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    downstream_metric_id: Mapped[int] = mapped_column(BigInteger)
    upstream_metric_id: Mapped[int] = mapped_column(BigInteger)
    dependency_type: Mapped[str | None] = mapped_column(String(32), default="DIRECT")
    weight: Mapped[float | None] = mapped_column(Numeric(10, 4), default=1.0)
