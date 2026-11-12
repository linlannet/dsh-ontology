"""流程层 ORM 模型：与 Java 版 ``onto_*`` / ``gwy_*`` 表同名同构。

平台层表（``onto_common_*`` / ``onto_global_*`` / ``onto_report_*``）属于 ontodb，
项目层表（``gwy_*``）属于 siisdb。两库不跨库 JOIN，聚合在应用层完成。
"""

from __future__ import annotations

from datetime import datetime

from dsh_onto_base import Base
from sqlalchemy import BigInteger, DateTime, Float, Integer, JSON, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """公共审计字段，与 Java DDL 保持一致（tenant_id 由各表按需声明）。"""

    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    del_flag: Mapped[int | None] = mapped_column(Integer, default=0)
    remark: Mapped[str | None] = mapped_column(String(800))


# ---------------------------------------------------------------------------
# 平台库：知识沉淀（个人层）
# ---------------------------------------------------------------------------


class OntoCommonDiscoveredEntity(AuditMixin, Base):
    __tablename__ = "onto_common_discovered_entity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_name: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    source_topic_id: Mapped[int | None] = mapped_column(BigInteger)
    first_seen_time: Mapped[datetime | None] = mapped_column(DateTime)
    mention_count: Mapped[int | None] = mapped_column(Integer, default=1)
    ontology_entity_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str | None] = mapped_column(String(20), default="DISCOVERED")
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class OntoCommonTenantRelationAsset(AuditMixin, Base):
    __tablename__ = "onto_common_tenant_relation_asset"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_entity_id: Mapped[int] = mapped_column(BigInteger)
    object_entity_id: Mapped[int] = mapped_column(BigInteger)
    relation_type: Mapped[str | None] = mapped_column(String(50))
    avg_score: Mapped[float | None] = mapped_column(Float)
    topic_ids: Mapped[str | None] = mapped_column(String(500))
    last_updated: Mapped[datetime | None] = mapped_column(DateTime)
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class OntoCommonPersonalVectorIndex(AuditMixin, Base):
    __tablename__ = "onto_common_personal_vector_index"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_id: Mapped[int] = mapped_column(BigInteger)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    model_version: Mapped[str | None] = mapped_column(String(50))
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class OntoCommonLlmChatHistory(AuditMixin, Base):
    __tablename__ = "onto_common_llm_chat_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str | None] = mapped_column(String(20))
    content: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[str | None] = mapped_column(String(100))
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class OntoCommonMergeLog(AuditMixin, Base):
    __tablename__ = "onto_common_merge_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_entity_id: Mapped[int] = mapped_column(BigInteger)
    target_entity_id: Mapped[int] = mapped_column(BigInteger)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    similarity_score: Mapped[float | None] = mapped_column(Float)
    merge_strategy: Mapped[str] = mapped_column(String(30))
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    tenant_id: Mapped[int] = mapped_column(BigInteger)


# ---------------------------------------------------------------------------
# 平台库：全局汇聚（共享层）
# ---------------------------------------------------------------------------


class OntoGlobalDiscoveredEntity(AuditMixin, Base):
    __tablename__ = "onto_global_discovered_entity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_name: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    tenant_ids: Mapped[str | None] = mapped_column(String(1000))
    total_mention_count: Mapped[int | None] = mapped_column(Integer, default=0)
    first_seen_time: Mapped[datetime | None] = mapped_column(DateTime)
    last_seen_time: Mapped[datetime | None] = mapped_column(DateTime)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)


class OntoGlobalBilateralRelation(AuditMixin, Base):
    __tablename__ = "onto_global_bilateral_relation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_entity_name: Mapped[str] = mapped_column(String(200))
    object_entity_name: Mapped[str] = mapped_column(String(200))
    relation_type: Mapped[str | None] = mapped_column(String(50))
    tenant_ids: Mapped[str | None] = mapped_column(String(1000))
    avg_score: Mapped[float | None] = mapped_column(Float)
    sample_count: Mapped[int | None] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)


class OntoGlobalKgNode(AuditMixin, Base):
    __tablename__ = "onto_global_kg_node"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ontology_entity_id: Mapped[int | None] = mapped_column(BigInteger)
    node_name: Mapped[str | None] = mapped_column(String(200))
    node_type: Mapped[str | None] = mapped_column(String(50))
    tenant_ids: Mapped[str | None] = mapped_column(String(1000))
    cross_tenant_weight: Mapped[float | None] = mapped_column(Float, default=1.0)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)


class OntoGlobalKgEdge(AuditMixin, Base):
    __tablename__ = "onto_global_kg_edge"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_node_id: Mapped[str] = mapped_column(String(100))
    target_node_id: Mapped[str] = mapped_column(String(100))
    relation_type: Mapped[str | None] = mapped_column(String(100))
    tenant_ids: Mapped[str | None] = mapped_column(String(1000))
    cross_tenant_weight: Mapped[float | None] = mapped_column(Float, default=1.0)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)


class OntoGlobalAggregationLog(AuditMixin, Base):
    __tablename__ = "onto_global_aggregation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aggregation_type: Mapped[str | None] = mapped_column(String(20))
    trigger_type: Mapped[str | None] = mapped_column(String(20))
    entity_count: Mapped[int | None] = mapped_column(Integer, default=0)
    relation_count: Mapped[int | None] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, default=0)
    status: Mapped[str | None] = mapped_column(String(20), default="running")
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)


# ---------------------------------------------------------------------------
# 平台库：报告域（workline 第 6/7 相位与统一监测告警计数使用）
# ---------------------------------------------------------------------------


class OntoReportAlertRecord(AuditMixin, Base):
    __tablename__ = "onto_report_alert_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    topic_id: Mapped[int | None] = mapped_column(BigInteger)
    alert_name: Mapped[str] = mapped_column(String(200))
    alert_type: Mapped[str | None] = mapped_column(String(50))
    alert_level: Mapped[str] = mapped_column(String(20), default="INFO")
    content: Mapped[str | None] = mapped_column(Text)
    entity_ids: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime)
    handled_by: Mapped[str | None] = mapped_column(String(50))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime)


class OntoReportPushRecord(AuditMixin, Base):
    __tablename__ = "onto_report_push_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger)
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int] = mapped_column(BigInteger)
    channel: Mapped[str] = mapped_column(String(50))
    recipient: Mapped[str | None] = mapped_column(String(200))
    payload: Mapped[str | None] = mapped_column(Text)
    delivery_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    error_msg: Mapped[str | None] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


# ---------------------------------------------------------------------------
# 项目库：追踪 / 分析 / 个人知识图谱 / 本体数据（gwy_*）
# ---------------------------------------------------------------------------


class GwyAnalyzeTrackTopic(AuditMixin, Base):
    __tablename__ = "gwy_analyze_track_topic"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_name: Mapped[str] = mapped_column(String(200))
    topic_type: Mapped[str | None] = mapped_column(String(50))
    hotspot_region: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    keyword_group_id: Mapped[int | None] = mapped_column(BigInteger)
    crawl_source_ids: Mapped[str | None] = mapped_column(String(500))
    alert_rule_ids: Mapped[str | None] = mapped_column(String(500))
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str | None] = mapped_column(String(20), default="active")
    alert_enabled: Mapped[int | None] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class GwyTrackArticle(AuditMixin, Base):
    __tablename__ = "gwy_track_article"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_hash: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(1000))
    lang: Mapped[str | None] = mapped_column(String(10), default="zh")
    published: Mapped[datetime | None] = mapped_column(DateTime)
    source: Mapped[str | None] = mapped_column(String(200))
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    topic_id: Mapped[int | None] = mapped_column(BigInteger)
    crawl_task_id: Mapped[int | None] = mapped_column(BigInteger)
    sentiment: Mapped[str | None] = mapped_column(String(20))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    nlp_status: Mapped[str | None] = mapped_column(String(20), default="PENDING")
    content: Mapped[str | None] = mapped_column(Text)
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class GwyTrackKgNode(AuditMixin, Base):
    __tablename__ = "gwy_track_kg_node"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(100))
    node_type: Mapped[str | None] = mapped_column(String(50))
    node_name: Mapped[str | None] = mapped_column(String(200))
    node_name_zh: Mapped[str | None] = mapped_column(String(200))
    ontology_entity_id: Mapped[int | None] = mapped_column(BigInteger)
    properties: Mapped[dict | None] = mapped_column(JSON)
    weight: Mapped[float | None] = mapped_column(Float, default=1.0)
    source_article_ids: Mapped[str | None] = mapped_column(Text)
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class GwyTrackKgEdge(AuditMixin, Base):
    __tablename__ = "gwy_track_kg_edge"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_node_id: Mapped[str] = mapped_column(String(100))
    target_node_id: Mapped[str] = mapped_column(String(100))
    relation_type: Mapped[str | None] = mapped_column(String(100))
    relation_name: Mapped[str | None] = mapped_column(String(200))
    properties: Mapped[dict | None] = mapped_column(JSON)
    weight: Mapped[float | None] = mapped_column(Float, default=1.0)
    article_id: Mapped[int | None] = mapped_column(BigInteger)
    tenant_id: Mapped[int] = mapped_column(BigInteger)


class GwyOntologyHotspot(AuditMixin, Base):
    __tablename__ = "gwy_ontology_hotspot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hotspot_name: Mapped[str] = mapped_column(String(200))
    hotspot_type: Mapped[str | None] = mapped_column(String(50))
    keywords: Mapped[str | None] = mapped_column(Text)
    related_countries: Mapped[str | None] = mapped_column(String(500))
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    heat_score: Mapped[int | None] = mapped_column(Integer, default=0)
    risk_level: Mapped[str | None] = mapped_column(String(20), default="low")
    status: Mapped[int | None] = mapped_column(Integer, default=1)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)


class GwyOntologyBilateralRelation(AuditMixin, Base):
    __tablename__ = "gwy_ontology_bilateral_relation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    country_a: Mapped[str] = mapped_column(String(100))
    country_b: Mapped[str] = mapped_column(String(100))
    relation_type: Mapped[str | None] = mapped_column(String(50))
    relation_level: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    start_year: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[int | None] = mapped_column(Integer, default=1)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
