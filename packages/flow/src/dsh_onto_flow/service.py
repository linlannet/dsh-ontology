"""流程层服务：workline 七相位编排、全局汇聚、实体合并、工作区 CRUD。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from time import perf_counter
from uuid import uuid4

from dsh_onto_base import tenant_id_var, user_id_var

from .models import (
    OntoGlobalBilateralRelation,
    OntoGlobalDiscoveredEntity,
    OntoGlobalKgEdge,
    OntoGlobalKgNode,
)
from .repository import (
    AggregationRepository,
    GlobalKnowledgeRepository,
    WorklineRepository,
    WorkspaceRepository,
)


# ---------------------------------------------------------------------------
# Workline：七相位编排
# ---------------------------------------------------------------------------

PHASES: list[tuple[int, str, str]] = [
    (1, "TOPIC_SETUP", "主题设定"),
    (2, "COLLECTION_MONITORING", "采集监测"),
    (3, "NLP_ANALYSIS", "NLP分析"),
    (4, "KG_CONSTRUCTION", "知识图谱构建"),
    (5, "HOTSPOT_ANALYSIS", "热点分析"),
    (6, "REPORT_GENERATION", "报告生成"),
    (7, "PUSH_DISPLAY", "推送展示"),
]
PHASE_ORDER = {code: order for order, code, _ in PHASES}


def _duration_ms(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() * 1000)


def _current_tenant() -> int | None:
    value = tenant_id_var.get()
    return int(value) if value and value.isdigit() else None


def _current_user() -> int | None:
    value = user_id_var.get()
    return int(value) if value and value.isdigit() else None


@dataclass
class WorklineContext:
    worklineId: str
    tenantId: int | None
    userId: int | None
    attributes: dict = field(default_factory=dict)
    currentPhase: str | None = None
    startTime: datetime = field(default_factory=datetime.now)
    endTime: datetime | None = None
    status: str = "INITIALIZED"


@dataclass
class WorklinePhaseResult:
    phase: str
    success: bool
    message: str
    output: dict | None
    startTime: datetime
    endTime: datetime
    durationMs: int


_CONTEXTS: dict[str, WorklineContext] = {}
_RESULTS: dict[str, list[WorklinePhaseResult]] = {}


class WorklineOrchestrator:
    """七相位流水线执行与内存状态管理（对应 Java ``WorklineOrchestrator``）。"""

    def __init__(self, repository: WorklineRepository) -> None:
        self._repository = repository

    def init(self, workline_id: str, tenant_id: int | None, user_id: int | None) -> WorklineContext:
        context = WorklineContext(worklineId=workline_id, tenantId=tenant_id, userId=user_id)
        _CONTEXTS[workline_id] = context
        return context

    def get_context(self, workline_id: str) -> WorklineContext | None:
        return _CONTEXTS.get(workline_id)

    def get_results(self, workline_id: str) -> list[WorklinePhaseResult] | None:
        return _RESULTS.get(workline_id)

    async def execute_phase(
        self, context: WorklineContext, phase: str
    ) -> WorklinePhaseResult:
        if phase not in PHASE_ORDER:
            raise ValueError(f"未知阶段: {phase}")
        context.currentPhase = phase
        context.status = f"RUNNING_{phase}"
        start = datetime.now()
        try:
            result = await self._run_phase(context, phase, start)
        except Exception as exc:  # 与 Java 一致：相位失败记录为 failure 结果
            end = datetime.now()
            result = WorklinePhaseResult(
                phase=phase,
                success=False,
                message=str(exc),
                output=None,
                startTime=start,
                endTime=end,
                durationMs=_duration_ms(start, end),
            )
        self._store_result(context.worklineId, result)
        return result

    async def execute_all(self, context: WorklineContext) -> list[WorklinePhaseResult]:
        context.status = "RUNNING"
        return [await self.execute_phase(context, code) for code in self._ordered_codes()]

    async def execute_until(
        self, context: WorklineContext, target: str
    ) -> list[WorklinePhaseResult]:
        context.status = "RUNNING"
        target_order = PHASE_ORDER[target]
        return [
            await self.execute_phase(context, code)
            for code in self._ordered_codes()
            if PHASE_ORDER[code] <= target_order
        ]

    async def _run_phase(
        self, context: WorklineContext, phase: str, start: datetime
    ) -> WorklinePhaseResult:
        handler = getattr(self, f"_phase_{PHASE_ORDER[phase]}")
        return await handler(context, start)

    @staticmethod
    def _ordered_codes() -> list[str]:
        return [code for _, code, _ in sorted(PHASES, key=lambda item: item[0])]

    @staticmethod
    def _store_result(workline_id: str, result: WorklinePhaseResult) -> None:
        _RESULTS.setdefault(workline_id, []).append(result)

    async def _phase_1(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        topic_id = context.attributes.get("topicId")
        topic_count = await self._repository.count_topic(int(topic_id)) if topic_id else 0
        output = {"topicId": topic_id if topic_id is not None else 0, "topicValid": topic_count > 0}
        end = datetime.now()
        return WorklinePhaseResult(
            phase="TOPIC_SETUP",
            success=True,
            message=f"主题设定完成（topicId={topic_id}）",
            output=output,
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )

    async def _phase_2(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        article_count = await self._repository.count_articles(context.tenantId)
        end = datetime.now()
        return WorklinePhaseResult(
            phase="COLLECTION_MONITORING",
            success=True,
            message=f"采集监测完成（文章数={article_count}）",
            output={"articleCount": article_count},
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )

    async def _phase_3(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        pending = await self._repository.count_pending_articles(context.tenantId)
        end = datetime.now()
        return WorklinePhaseResult(
            phase="NLP_ANALYSIS",
            success=True,
            message=f"NLP分析完成（待处理={pending}）",
            output={"pendingArticles": pending},
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )

    async def _phase_4(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        nodes = await self._repository.count_kg_nodes(context.tenantId)
        edges = await self._repository.count_kg_edges(context.tenantId)
        end = datetime.now()
        return WorklinePhaseResult(
            phase="KG_CONSTRUCTION",
            success=True,
            message=f"知识图谱构建完成（节点={nodes}, 边={edges}）",
            output={"kgNodes": nodes, "kgEdges": edges},
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )

    async def _phase_5(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        hotspots = await self._repository.count_hotspots()
        end = datetime.now()
        return WorklinePhaseResult(
            phase="HOTSPOT_ANALYSIS",
            success=True,
            message=f"热点分析完成（热点数={hotspots}）",
            output={"hotspotCount": hotspots},
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )

    async def _phase_6(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        reports = await self._repository.count_report_instances(context.tenantId)
        end = datetime.now()
        return WorklinePhaseResult(
            phase="REPORT_GENERATION",
            success=True,
            message=f"报告生成完成（报告数={reports}）",
            output={"reportCount": reports},
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )

    async def _phase_7(self, context: WorklineContext, start: datetime) -> WorklinePhaseResult:
        pushes = await self._repository.count_push_records(context.tenantId)
        context.status = "COMPLETED"
        context.endTime = datetime.now()
        end = datetime.now()
        return WorklinePhaseResult(
            phase="PUSH_DISPLAY",
            success=True,
            message=f"推送展示完成（推送数={pushes}）",
            output={"pushCount": pushes},
            startTime=start,
            endTime=end,
            durationMs=_duration_ms(start, end),
        )


class WorklineService:
    """工作流生命周期服务（对应 Java ``WorklineService``）。"""

    def __init__(self, orchestrator: WorklineOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def activate_topic(self, topic_id: int) -> WorklineContext:
        workline_id = "wl-" + uuid4().hex[:8]
        context = self._orchestrator.init(workline_id, _current_tenant(), _current_user())
        context.attributes["topicId"] = topic_id
        await self._orchestrator.execute_phase(context, "TOPIC_SETUP")
        return context

    def get_status(self, workline_id: str) -> WorklineContext | None:
        return self._orchestrator.get_context(workline_id)

    def get_progress(self, workline_id: str) -> list[WorklinePhaseResult] | None:
        return self._orchestrator.get_results(workline_id)

    async def execute_phase(self, workline_id: str, phase: str) -> WorklinePhaseResult:
        context = self._require(workline_id)
        return await self._orchestrator.execute_phase(context, phase)

    async def execute_until(self, workline_id: str, phase: str) -> list[WorklinePhaseResult]:
        context = self._require(workline_id)
        if phase not in PHASE_ORDER:
            raise ValueError(f"未知阶段: {phase}")
        return await self._orchestrator.execute_until(context, phase)

    async def execute_all(self, workline_id: str) -> list[WorklinePhaseResult]:
        context = self._require(workline_id)
        return await self._orchestrator.execute_all(context)

    @staticmethod
    def get_stages() -> list[dict]:
        return [
            {"order": order, "name": name, "code": code}
            for order, code, name in sorted(PHASES, key=lambda item: item[0])
        ]

    def _require(self, workline_id: str) -> WorklineContext:
        context = self._orchestrator.get_context(workline_id)
        if context is None:
            raise LookupError(f"工作流不存在: {workline_id}")
        return context


# ---------------------------------------------------------------------------
# 汇聚：全量/增量、日志、统一监测视图、统一知识图谱、主任概览
# ---------------------------------------------------------------------------


@dataclass
class AggregationStats:
    entityCount: int = 0
    relationCount: int = 0
    durationMs: int = 0
    success: bool = False
    errorMsg: str | None = None


def _tenant_ids(tenants: set[int | None]) -> str:
    return "[" + ",".join(str(t) for t in sorted(tenants) if t is not None) + "]"


def _latest(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None or candidate > current:
        return candidate
    return current


class AggregationService:
    """应用层汇聚：源表读取后分组，再分别写入全局表，避免跨库 JOIN。"""

    def __init__(self, repository: AggregationRepository) -> None:
        self._repository = repository

    async def trigger_full_aggregation(self) -> AggregationStats:
        return await self._aggregate_all("MANUAL")

    async def trigger_manual_incremental(self, tenant_id: int) -> AggregationStats:
        return await self._aggregate_incremental(tenant_id, "MANUAL")

    async def _aggregate_all(self, trigger_type: str) -> AggregationStats:
        started = perf_counter()
        stats = AggregationStats()
        try:
            stats.entityCount = await self._aggregate_entities(None)
            stats.relationCount = await self._aggregate_relations(None)
            await self._aggregate_kg_nodes(None)
            await self._aggregate_kg_edges(None)
            stats.success = True
        except Exception as exc:
            stats.success = False
            stats.errorMsg = str(exc)
        finally:
            stats.durationMs = int((perf_counter() - started) * 1000)
            await self._log("FULL", trigger_type, stats)
        return stats

    async def _aggregate_incremental(self, tenant_id: int, trigger_type: str) -> AggregationStats:
        started = perf_counter()
        stats = AggregationStats()
        try:
            stats.entityCount = await self._aggregate_entities(tenant_id)
            stats.relationCount = await self._aggregate_relations(tenant_id)
            await self._aggregate_kg_nodes(tenant_id)
            await self._aggregate_kg_edges(tenant_id)
            stats.success = True
        except Exception as exc:
            stats.success = False
            stats.errorMsg = str(exc)
        finally:
            stats.durationMs = int((perf_counter() - started) * 1000)
            await self._log("INCREMENTAL", trigger_type, stats)
        return stats

    async def _aggregate_entities(self, tenant_id: int | None) -> int:
        rows = await self._repository.list_common_entities(tenant_id)
        groups: dict[tuple[str, str | None], dict] = {}
        for row in rows:
            group = groups.setdefault(
                (row.entity_name, row.entity_type),
                {"tenants": set(), "total": 0, "first": None, "last": None},
            )
            if row.tenant_id is not None:
                group["tenants"].add(row.tenant_id)
            group["total"] += int(row.mention_count or 0)
            group["first"] = _latest(group["first"], row.first_seen_time)
            group["last"] = _latest(group["last"], row.updated_at or row.created_at)

        for (name, entity_type), group in groups.items():
            existing = await self._repository.find_global_entity(name, entity_type)
            if existing is not None:
                if tenant_id is None:
                    values = {
                        "tenant_ids": _tenant_ids(group["tenants"]),
                        "total_mention_count": group["total"],
                        "last_seen_time": group["last"],
                    }
                else:
                    values = {
                        "total_mention_count": int(existing.total_mention_count or 0)
                        + group["total"],
                        "last_seen_time": _latest(existing.last_seen_time, group["last"]),
                    }
                await self._repository.update_global(
                    OntoGlobalDiscoveredEntity, existing.id, values
                )
            else:
                await self._repository.insert_global(
                    OntoGlobalDiscoveredEntity(
                        entity_name=name,
                        entity_type=entity_type,
                        tenant_ids=_tenant_ids(group["tenants"]),
                        total_mention_count=group["total"],
                        first_seen_time=group["first"],
                        last_seen_time=group["last"],
                        created_by="aggregator",
                    )
                )
        return len(groups)

    async def _aggregate_relations(self, tenant_id: int | None) -> int:
        rows = await self._repository.list_bilateral_relations(tenant_id)
        groups: dict[tuple[str, str, str | None], dict] = {}
        for row in rows:
            group = groups.setdefault(
                (row.country_a, row.country_b, row.relation_type),
                {"tenants": set(), "count": 0},
            )
            if row.tenant_id is not None:
                group["tenants"].add(row.tenant_id)
            group["count"] += 1

        for (subject, obj, relation_type), group in groups.items():
            existing = await self._repository.find_global_relation(subject, obj, relation_type)
            if existing is not None:
                if tenant_id is None:
                    values = {
                        "tenant_ids": _tenant_ids(group["tenants"]),
                        "avg_score": 1.0,
                        "sample_count": group["count"],
                    }
                else:
                    old_samples = int(existing.sample_count or 0)
                    new_samples = old_samples + group["count"]
                    old_avg = float(existing.avg_score or 1.0)
                    values = {
                        "avg_score": (old_avg * old_samples + group["count"]) / new_samples
                        if new_samples
                        else 1.0,
                        "sample_count": new_samples,
                    }
                await self._repository.update_global(
                    OntoGlobalBilateralRelation, existing.id, values
                )
            else:
                await self._repository.insert_global(
                    OntoGlobalBilateralRelation(
                        subject_entity_name=subject,
                        object_entity_name=obj,
                        relation_type=relation_type,
                        tenant_ids=_tenant_ids(group["tenants"]),
                        avg_score=1.0,
                        sample_count=group["count"],
                        created_by="aggregator",
                    )
                )
        return len(groups)

    async def _aggregate_kg_nodes(self, tenant_id: int | None) -> None:
        rows = await self._repository.list_kg_nodes(tenant_id)
        groups: dict[tuple[str | None, str | None], set[int | None]] = {}
        for row in rows:
            groups.setdefault((row.node_name, row.node_type), set()).add(row.tenant_id)

        for (node_name, node_type), tenants in groups.items():
            existing = await self._repository.find_global_node(node_name, node_type)
            if existing is not None:
                if tenant_id is None:
                    values = {
                        "tenant_ids": _tenant_ids(tenants),
                        "cross_tenant_weight": float(len(tenants)),
                    }
                else:
                    values = {
                        "cross_tenant_weight": float(existing.cross_tenant_weight or 0) + 1
                    }
                await self._repository.update_global(OntoGlobalKgNode, existing.id, values)
            else:
                await self._repository.insert_global(
                    OntoGlobalKgNode(
                        node_name=node_name,
                        node_type=node_type,
                        tenant_ids=_tenant_ids(tenants),
                        cross_tenant_weight=float(len(tenants)),
                        created_by="aggregator",
                    )
                )

    async def _aggregate_kg_edges(self, tenant_id: int | None) -> None:
        rows = await self._repository.list_kg_edges(tenant_id)
        groups: dict[tuple[str, str, str | None], set[int | None]] = {}
        for row in rows:
            groups.setdefault(
                (row.source_node_id, row.target_node_id, row.relation_type), set()
            ).add(row.tenant_id)

        for (source, target, relation_type), tenants in groups.items():
            existing = await self._repository.find_global_edge(source, target, relation_type)
            if existing is not None:
                if tenant_id is None:
                    values = {
                        "tenant_ids": _tenant_ids(tenants),
                        "cross_tenant_weight": float(len(tenants)),
                    }
                else:
                    values = {
                        "cross_tenant_weight": float(existing.cross_tenant_weight or 0) + 1
                    }
                await self._repository.update_global(OntoGlobalKgEdge, existing.id, values)
            else:
                await self._repository.insert_global(
                    OntoGlobalKgEdge(
                        source_node_id=source,
                        target_node_id=target,
                        relation_type=relation_type,
                        tenant_ids=_tenant_ids(tenants),
                        cross_tenant_weight=float(len(tenants)),
                        created_by="aggregator",
                    )
                )

    async def _log(self, agg_type: str, trigger_type: str, stats: AggregationStats) -> None:
        try:
            await self._repository.insert_aggregation_log(
                {
                    "aggregation_type": agg_type,
                    "trigger_type": trigger_type,
                    "entity_count": stats.entityCount,
                    "relation_count": stats.relationCount,
                    "duration_ms": stats.durationMs,
                    "status": "success" if stats.success else "failed",
                    "created_by": "aggregator",
                    "remark": (stats.errorMsg or "")[:500] or None,
                }
            )
        except Exception:  # 日志写入失败不影响主流程（与 Java 一致）
            pass

    async def get_aggregation_logs(self, page_num: int, page_size: int) -> list[dict]:
        return await self._repository.list_aggregation_logs(
            max(page_size, 1), (max(page_num, 1) - 1) * max(page_size, 1)
        )

    async def get_unified_monitor(
        self,
        page_num: int,
        page_size: int,
        tenant_id: int | None,
        time_window_days: int,
    ) -> list[dict]:
        limit = max(page_size, 1)
        offset = (max(page_num, 1) - 1) * limit
        cutoff = datetime.combine(
            date.today() - timedelta(days=max(time_window_days, 0)), time.min
        )
        topics = await self._repository.list_topics(tenant_id, limit, offset)
        topic_ids = [int(topic["id"]) for topic in topics]

        articles = await self._repository.list_articles_by_topic_ids(topic_ids)
        article_count: dict[tuple, int] = defaultdict(int)
        recent_count: dict[tuple, int] = defaultdict(int)
        latest_article: dict[tuple, datetime | None] = defaultdict(lambda: None)
        for article in articles:
            key = (article["tenant_id"], article["topic_id"])
            article_count[key] += 1
            published = article["published"]
            if published is not None and published >= cutoff:
                recent_count[key] += 1
            latest_article[key] = _latest(latest_article[key], published)

        alerts = await self._repository.alert_counts_by_topic_ids(topic_ids)
        rows: list[dict] = []
        for topic in topics:
            key = (topic["tenant_id"], topic["id"])
            rows.append(
                {
                    "tenant_id": topic["tenant_id"],
                    "topic_id": topic["id"],
                    "topic_name": topic["topic_name"],
                    "topic_type": topic["topic_type"],
                    "hotspot_region": topic["hotspot_region"],
                    "topic_status": topic["status"],
                    "alert_enabled": topic["alert_enabled"],
                    "article_count": article_count.get(key, 0),
                    "recent_article_count": recent_count.get(key, 0),
                    "latest_article_time": latest_article.get(key),
                    "alert_count": alerts.get(int(topic["id"]), 0),
                }
            )
        return rows

    async def get_unified_kg(self) -> list[dict]:
        personal = await self._repository.list_personal_kg_nodes()
        global_nodes = await self._repository.list_global_kg_nodes()
        result = [
            {
                "source_layer": "PERSONAL",
                "tenant_id": row["tenant_id"],
                "node_id": row["node_id"],
                "node_type": row["node_type"],
                "node_name": row["node_name"],
                "weight": row["weight"],
            }
            for row in personal
        ]
        result.extend(
            {
                "source_layer": "GLOBAL",
                "tenant_id": None,
                "node_id": f"G-{row['id']}",
                "node_type": row["node_type"],
                "node_name": row["node_name"],
                "weight": row["cross_tenant_weight"],
            }
            for row in global_nodes
        )
        return result

    async def get_global_entities(self, page_num: int, page_size: int) -> list[dict]:
        return await self._repository.list_global_entities(
            max(page_size, 1), (max(page_num, 1) - 1) * max(page_size, 1)
        )

    async def get_global_relations(self, page_num: int, page_size: int) -> list[dict]:
        return await self._repository.list_global_relations(
            max(page_size, 1), (max(page_num, 1) - 1) * max(page_size, 1)
        )

    async def get_global_kg_nodes(self, page_num: int, page_size: int) -> list[dict]:
        return await self._repository.list_global_kg_nodes_page(
            max(page_size, 1), (max(page_num, 1) - 1) * max(page_size, 1)
        )

    async def get_global_kg_edges(self, page_num: int, page_size: int) -> list[dict]:
        return await self._repository.list_global_kg_edges_page(
            max(page_size, 1), (max(page_num, 1) - 1) * max(page_size, 1)
        )

    async def get_director_overview(self) -> dict:
        overview = {
            "totalEntities": await self._repository.count_global(OntoGlobalDiscoveredEntity),
            "totalRelations": await self._repository.count_global(OntoGlobalBilateralRelation),
            "totalKgNodes": await self._repository.count_global(OntoGlobalKgNode),
            "totalKgEdges": await self._repository.count_global(OntoGlobalKgEdge),
            "totalTenants": await self._repository.count_distinct_article_tenants(),
            "totalArticles": await self._repository.count_articles(),
        }
        last = await self._repository.latest_aggregation_log()
        overview["lastAggregation"] = last if last is not None else {"status": "none"}
        return overview


# ---------------------------------------------------------------------------
# 实体合并
# ---------------------------------------------------------------------------


class EntityMergeService:
    """实体消歧合并（对应 Java ``EntityMergeService``）。"""

    def __init__(self, repository: GlobalKnowledgeRepository) -> None:
        self._repository = repository

    async def merge_entities(
        self,
        source_entity_id: int,
        target_entity_id: int,
        entity_type: str | None,
        similarity_score: float | None,
        strategy: str,
    ) -> int:
        tenant_id = _current_tenant()
        operator_id = _current_user()
        operator = str(operator_id) if operator_id is not None else "system"
        return await self._merge(
            source_entity_id,
            target_entity_id,
            entity_type,
            similarity_score,
            strategy,
            tenant_id or 0,
            operator_id,
            operator,
        )

    async def _merge(
        self,
        source_entity_id: int,
        target_entity_id: int,
        entity_type: str | None,
        similarity_score: float | None,
        strategy: str,
        tenant_id: int,
        operator_id: int | None,
        operator: str,
    ) -> int:
        if source_entity_id == target_entity_id:
            raise ValueError("源实体和目标实体不能相同")

        log_id = await self._repository.insert_merge_log(
            {
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "entity_type": entity_type,
                "similarity_score": similarity_score,
                "merge_strategy": strategy,
                "operator_id": operator_id,
                "tenant_id": tenant_id,
                "created_by": operator,
            }
        )
        await self._repository.migrate_relation_assets(
            source_entity_id, target_entity_id, tenant_id
        )
        delta = await self._repository.get_mention_count(source_entity_id)
        if delta:
            await self._repository.add_mention_count(target_entity_id, delta, operator)
        await self._repository.soft_delete_entity(source_entity_id, operator)
        return log_id

    async def auto_merge_by_name_match(self, tenant_id: int) -> int:
        duplicates = await self._repository.find_duplicate_entities(tenant_id)
        merged = 0
        for dup in duplicates:
            keep_id = int(dup["keep_id"])
            source_ids = await self._repository.find_entity_ids(
                tenant_id, dup["entity_name"], dup["entity_type"], keep_id
            )
            for source_id in source_ids:
                await self._merge(
                    source_id,
                    keep_id,
                    dup["entity_type"],
                    1.0,
                    "AUTO_NAME_MATCH",
                    tenant_id,
                    None,
                    "system",
                )
                merged += 1
        return merged

    async def get_merge_logs(self, tenant_id: int, page_num: int, page_size: int) -> list[dict]:
        rows = await self._repository.list_merge_logs(
            tenant_id, max(page_size, 1), (max(page_num, 1) - 1) * max(page_size, 1)
        )
        return [
            {
                "id": row["id"],
                "sourceEntityId": row["source_entity_id"],
                "targetEntityId": row["target_entity_id"],
                "entityType": row["entity_type"],
                "similarityScore": row["similarity_score"],
                "mergeStrategy": row["merge_strategy"],
                "operatorId": row["operator_id"],
                "tenantId": row["tenant_id"],
                "createdBy": row["created_by"],
                "createdAt": row["created_at"],
                "updatedBy": row["updated_by"],
                "updatedAt": row["updated_at"],
                "delFlag": row["del_flag"],
                "remark": row["remark"],
            }
            for row in rows
        ]


# ---------------------------------------------------------------------------
# 工作区（知识沉淀）
# ---------------------------------------------------------------------------


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def get_categories(self) -> list[str]:
        return list(self._repository.categories)

    async def find_all(self, category: str, tenant_id: int | None) -> list[dict]:
        return await self._repository.find_all(category, tenant_id)

    async def find_page(
        self, category: str, tenant_id: int | None, page_num: int, page_size: int
    ) -> dict:
        return await self._repository.find_page(category, tenant_id, page_num, page_size)

    async def find_by_id(
        self, category: str, tenant_id: int | None, row_id: int
    ) -> dict | None:
        return await self._repository.find_by_id(category, tenant_id, row_id)

    async def create(
        self, category: str, tenant_id: int | None, created_by: str, data: dict
    ) -> int:
        return await self._repository.create(category, tenant_id, created_by, data)

    async def update(
        self, category: str, tenant_id: int | None, row_id: int, data: dict
    ) -> int:
        return await self._repository.update(category, tenant_id, row_id, data)

    async def delete(self, category: str, tenant_id: int | None, row_id: int) -> int:
        return await self._repository.delete(category, tenant_id, row_id)

    async def count(self, category: str, tenant_id: int | None) -> int:
        return await self._repository.count(category, tenant_id)

    async def search(self, keyword: str, category: str | None, limit: int) -> list[dict]:
        return await self._repository.search(keyword, category, limit)

    async def query_by_filters(
        self,
        category: str,
        tenant_id: int | None,
        filters: dict,
        page_num: int,
        page_size: int,
    ) -> list[dict]:
        return await self._repository.query_by_filters(
            category, tenant_id, filters, page_num, page_size
        )
