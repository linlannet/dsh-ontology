"""报告层 ORM 模型：与 Java 版七张 ``onto_report_*`` 表同名同构。"""

from __future__ import annotations

from datetime import datetime

from dsh_onto_base import Base
from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
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


class ReportTemplate(AuditMixin, Base):
    """报告模板。"""

    __tablename__ = "onto_report_template"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_name: Mapped[str] = mapped_column(String(200))
    template_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(800))
    section_config: Mapped[str | None] = mapped_column(Text)
    chart_config: Mapped[str | None] = mapped_column(Text)
    status: Mapped[int | None] = mapped_column(Integer, default=0)


class ReportInstance(AuditMixin, Base):
    """报告实例。"""

    __tablename__ = "onto_report_instance"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[int | None] = mapped_column(BigInteger)
    report_name: Mapped[str] = mapped_column(String(200))
    report_type: Mapped[str | None] = mapped_column(String(50))
    data_source: Mapped[str | None] = mapped_column(String(200))
    parameters: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(20), default="DRAFT")
    generated_time: Mapped[datetime | None] = mapped_column(DateTime)
    published_time: Mapped[datetime | None] = mapped_column(DateTime)
    legacy_report_id: Mapped[int | None] = mapped_column(BigInteger)


class ReportSection(AuditMixin, Base):
    """报告章节。"""

    __tablename__ = "onto_report_section"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(BigInteger)
    section_index: Mapped[int | None] = mapped_column(Integer, default=0)
    section_title: Mapped[str | None] = mapped_column(String(200))
    section_type: Mapped[str | None] = mapped_column(String(50))
    content: Mapped[str | None] = mapped_column(Text)
    chart_data: Mapped[str | None] = mapped_column(Text)


class ReportChartDef(AuditMixin, Base):
    """图表定义。"""

    __tablename__ = "onto_report_chart_def"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chart_name: Mapped[str] = mapped_column(String(200))
    chart_type: Mapped[str | None] = mapped_column(String(50))
    data_query: Mapped[str | None] = mapped_column(Text)
    x_axis: Mapped[str | None] = mapped_column(String(100))
    y_axis: Mapped[str | None] = mapped_column(String(100))
    series_config: Mapped[str | None] = mapped_column(Text)
    template_id: Mapped[int | None] = mapped_column(BigInteger)


class ReportQaSession(AuditMixin, Base):
    """问数会话。"""

    __tablename__ = "onto_report_qa_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_name: Mapped[str | None] = mapped_column(String(200))
    user_question: Mapped[str | None] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(20), default="ACTIVE")


class ReportQaQuery(AuditMixin, Base):
    """问数查询记录。"""

    __tablename__ = "onto_report_qa_query"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger)
    query_text: Mapped[str] = mapped_column(Text)
    translated_sql: Mapped[str | None] = mapped_column(Text)
    result_data: Mapped[str | None] = mapped_column(Text)
    chart_suggestion: Mapped[str | None] = mapped_column(String(500))
    process_status: Mapped[str | None] = mapped_column(String(20), default="PENDING")


class ReportAnalysisTask(AuditMixin, Base):
    """分析任务。"""

    __tablename__ = "onto_report_analysis_task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(200))
    task_type: Mapped[str | None] = mapped_column(String(50))
    data_range: Mapped[str | None] = mapped_column(String(200))
    analysis_config: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(20), default="PENDING")
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
