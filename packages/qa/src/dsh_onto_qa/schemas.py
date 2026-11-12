"""报告层出入参模型（pydantic），字段与 Java 实体对齐。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    tenant_id: int | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None
    del_flag: int | None = None
    remark: str | None = None


class TemplateIn(_Base):
    template_name: str
    template_type: str | None = None
    description: str | None = None
    section_config: str | None = None
    chart_config: str | None = None
    status: int | None = None


class InstanceIn(_Base):
    template_id: int | None = None
    report_name: str
    report_type: str | None = None
    data_source: str | None = None
    parameters: str | None = None
    status: str | None = None
    generated_time: datetime | None = None
    published_time: datetime | None = None
    legacy_report_id: int | None = None


class SectionIn(_Base):
    instance_id: int | None = None
    section_index: int | None = None
    section_title: str | None = None
    section_type: str | None = None
    content: str | None = None
    chart_data: str | None = None


class ChartDefIn(_Base):
    chart_name: str
    chart_type: str | None = None
    data_query: str | None = None
    x_axis: str | None = None
    y_axis: str | None = None
    series_config: str | None = None
    template_id: int | None = None


class QaSessionIn(_Base):
    session_name: str | None = None
    user_question: str | None = None
    context: str | None = None
    status: str | None = None


class QaQueryIn(_Base):
    session_id: int | None = None
    query_text: str
    translated_sql: str | None = None
    result_data: str | None = None
    chart_suggestion: str | None = None
    process_status: str | None = None


class AnalysisTaskIn(_Base):
    task_name: str
    task_type: str | None = None
    data_range: str | None = None
    analysis_config: str | None = None
    result_summary: str | None = None
    status: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
