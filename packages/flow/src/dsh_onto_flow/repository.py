"""流程层数据访问。

- ``WorklineRepository``：工作流七相位的计数（gwy_* 走 siis，onto_* 走 onto）
- ``AggregationRepository``：汇聚源数据读取与全局表写入
- ``GlobalKnowledgeRepository``：全局查询与实体合并
- ``WorkspaceRepository``：知识沉淀四类实体的通用 CRUD

两库之间不做 JOIN，聚合/关联在 service 层应用内完成。
"""

from __future__ import annotations

import math
from datetime import datetime

from sqlalchemy import func, insert, or_, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from .models import (
    GwyAnalyzeTrackTopic,
    GwyOntologyBilateralRelation,
    GwyOntologyHotspot,
    GwyTrackArticle,
    GwyTrackKgEdge,
    GwyTrackKgNode,
    OntoCommonDiscoveredEntity,
    OntoCommonLlmChatHistory,
    OntoCommonMergeLog,
    OntoCommonPersonalVectorIndex,
    OntoCommonTenantRelationAsset,
    OntoGlobalAggregationLog,
    OntoGlobalBilateralRelation,
    OntoGlobalDiscoveredEntity,
    OntoGlobalKgEdge,
    OntoGlobalKgNode,
    OntoReportAlertRecord,
    OntoReportPushRecord,
)


class _BaseRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._factory = session_factory

    async def _list(self, model, *criteria, order_by=None, limit=None, offset=None) -> list:
        async with self._factory() as session:
            stmt = select(model).where(*criteria)
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            if limit is not None:
                stmt = stmt.limit(limit)
            if offset is not None:
                stmt = stmt.offset(offset)
            return list((await session.scalars(stmt)).all())

    async def _one(self, model, *criteria):
        async with self._factory() as session:
            return (await session.scalars(select(model).where(*criteria))).first()

    async def _count(self, model, *criteria) -> int:
        async with self._factory() as session:
            stmt = select(func.count()).select_from(model).where(*criteria)
            return int((await session.execute(stmt)).scalar_one() or 0)

    async def _mappings(self, stmt) -> list[dict]:
        async with self._factory() as session:
            result = await session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    async def _insert(self, entity) -> int:
        async with self._factory() as session:
            session.add(entity)
            await session.commit()
            return int(entity.id)

    async def _insert_values(self, model, values: dict) -> int:
        async with self._factory() as session:
            result = await session.execute(insert(model.__table__).values(**values))
            await session.commit()
            return int(result.inserted_primary_key[0])

    async def _update(self, model, criteria, values: dict) -> int:
        async with self._factory() as session:
            result = await session.execute(update(model).where(*criteria).values(**values))
            await session.commit()
            return int(result.rowcount or 0)


class WorklineRepository:
    """工作流相位所需计数，按表归属分别使用 siis / onto 会话。"""

    def __init__(
        self,
        siis_session: async_sessionmaker,
        onto_session: async_sessionmaker,
    ) -> None:
        self._siis = _BaseRepository(siis_session)
        self._onto = _BaseRepository(onto_session)

    async def count_topic(self, topic_id: int) -> int:
        return await self._siis._count(
            GwyAnalyzeTrackTopic,
            GwyAnalyzeTrackTopic.id == topic_id,
            GwyAnalyzeTrackTopic.del_flag == 0,
        )

    async def count_articles(self, tenant_id: int | None) -> int:
        return await self._siis._count(
            GwyTrackArticle,
            GwyTrackArticle.del_flag == 0,
            GwyTrackArticle.tenant_id == tenant_id,
        )

    async def count_pending_articles(self, tenant_id: int | None) -> int:
        return await self._siis._count(
            GwyTrackArticle,
            GwyTrackArticle.nlp_status == "PENDING",
            GwyTrackArticle.del_flag == 0,
            GwyTrackArticle.tenant_id == tenant_id,
        )

    async def count_kg_nodes(self, tenant_id: int | None) -> int:
        return await self._siis._count(
            GwyTrackKgNode,
            GwyTrackKgNode.del_flag == 0,
            GwyTrackKgNode.tenant_id == tenant_id,
        )

    async def count_kg_edges(self, tenant_id: int | None) -> int:
        return await self._siis._count(
            GwyTrackKgEdge,
            GwyTrackKgEdge.del_flag == 0,
            GwyTrackKgEdge.tenant_id == tenant_id,
        )

    async def count_hotspots(self) -> int:
        return await self._siis._count(GwyOntologyHotspot, GwyOntologyHotspot.del_flag == 0)

    async def count_report_instances(self, tenant_id: int | None) -> int:
        # onto_report_instance 由 dsh-onto-qa 声明（同一 Base metadata），此处复用其表名计数。
        stmt = text(
            "SELECT COUNT(*) FROM onto_report_instance "
            "WHERE del_flag = 0 AND tenant_id = :tenant_id"
        )
        async with self._onto._factory() as session:
            return int(
                (await session.execute(stmt, {"tenant_id": tenant_id})).scalar_one() or 0
            )

    async def count_push_records(self, tenant_id: int | None) -> int:
        return await self._onto._count(
            OntoReportPushRecord,
            OntoReportPushRecord.del_flag == 0,
            OntoReportPushRecord.tenant_id == tenant_id,
        )


class AggregationRepository:
    """汇聚与统一视图查询。源表 gwy_* 在 siis，目标表 onto_global_* 在 onto。"""

    def __init__(
        self,
        siis_session: async_sessionmaker,
        onto_session: async_sessionmaker,
    ) -> None:
        self._siis = _BaseRepository(siis_session)
        self._onto = _BaseRepository(onto_session)

    # -- 汇聚源数据 ---------------------------------------------------------
    async def list_common_entities(self, tenant_id: int | None = None) -> list:
        criteria = [OntoCommonDiscoveredEntity.del_flag == 0]
        if tenant_id is not None:
            criteria.append(OntoCommonDiscoveredEntity.tenant_id == tenant_id)
        return await self._onto._list(OntoCommonDiscoveredEntity, *criteria)

    async def list_bilateral_relations(self, tenant_id: int | None = None) -> list:
        criteria = [GwyOntologyBilateralRelation.del_flag == 0]
        if tenant_id is not None:
            criteria.append(GwyOntologyBilateralRelation.tenant_id == tenant_id)
        return await self._siis._list(GwyOntologyBilateralRelation, *criteria)

    async def list_kg_nodes(self, tenant_id: int | None = None) -> list:
        criteria = [GwyTrackKgNode.del_flag == 0]
        if tenant_id is not None:
            criteria.append(GwyTrackKgNode.tenant_id == tenant_id)
        return await self._siis._list(GwyTrackKgNode, *criteria)

    async def list_kg_edges(self, tenant_id: int | None = None) -> list:
        criteria = [GwyTrackKgEdge.del_flag == 0]
        if tenant_id is not None:
            criteria.append(GwyTrackKgEdge.tenant_id == tenant_id)
        return await self._siis._list(GwyTrackKgEdge, *criteria)

    # -- 全局表读写 ---------------------------------------------------------
    async def find_global_entity(self, entity_name: str, entity_type: str | None):
        criteria = [
            OntoGlobalDiscoveredEntity.entity_name == entity_name,
            OntoGlobalDiscoveredEntity.entity_type == entity_type,
        ]
        if entity_type is None:
            criteria[1] = OntoGlobalDiscoveredEntity.entity_type.is_(None)
        return await self._onto._one(OntoGlobalDiscoveredEntity, *criteria)

    async def find_global_relation(
        self, subject: str, obj: str, relation_type: str | None
    ):
        criteria = [
            OntoGlobalBilateralRelation.subject_entity_name == subject,
            OntoGlobalBilateralRelation.object_entity_name == obj,
            OntoGlobalBilateralRelation.relation_type == relation_type,
        ]
        if relation_type is None:
            criteria[2] = OntoGlobalBilateralRelation.relation_type.is_(None)
        return await self._onto._one(OntoGlobalBilateralRelation, *criteria)

    async def find_global_node(self, node_name: str | None, node_type: str | None):
        criteria = [
            OntoGlobalKgNode.node_name == node_name,
            OntoGlobalKgNode.node_type == node_type,
        ]
        if node_name is None:
            criteria[0] = OntoGlobalKgNode.node_name.is_(None)
        if node_type is None:
            criteria[1] = OntoGlobalKgNode.node_type.is_(None)
        return await self._onto._one(OntoGlobalKgNode, *criteria)

    async def find_global_edge(
        self, source_node_id: str, target_node_id: str, relation_type: str | None
    ):
        criteria = [
            OntoGlobalKgEdge.source_node_id == source_node_id,
            OntoGlobalKgEdge.target_node_id == target_node_id,
            OntoGlobalKgEdge.relation_type == relation_type,
        ]
        if relation_type is None:
            criteria[2] = OntoGlobalKgEdge.relation_type.is_(None)
        return await self._onto._one(OntoGlobalKgEdge, *criteria)

    async def insert_global(self, entity) -> int:
        return await self._onto._insert(entity)

    async def update_global(self, model, row_id: int, values: dict) -> int:
        return await self._onto._update(model, [model.id == row_id], values)

    # -- 汇聚日志 -----------------------------------------------------------
    async def insert_aggregation_log(self, values: dict) -> int:
        return await self._onto._insert_values(OntoGlobalAggregationLog, values)

    async def list_aggregation_logs(self, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(OntoGlobalAggregationLog.__table__)
            .where(OntoGlobalAggregationLog.del_flag == 0)
            .order_by(OntoGlobalAggregationLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return await self._onto._mappings(stmt)

    async def latest_aggregation_log(self) -> dict | None:
        stmt = (
            select(OntoGlobalAggregationLog.__table__)
            .where(OntoGlobalAggregationLog.del_flag == 0)
            .order_by(OntoGlobalAggregationLog.created_at.desc())
            .limit(1)
        )
        rows = await self._onto._mappings(stmt)
        return rows[0] if rows else None

    # -- 统一监测 -----------------------------------------------------------
    async def list_topics(self, tenant_id: int | None, limit: int, offset: int) -> list[dict]:
        criteria = [GwyAnalyzeTrackTopic.del_flag == 0]
        if tenant_id is not None:
            criteria.append(GwyAnalyzeTrackTopic.tenant_id == tenant_id)
        stmt = (
            select(GwyAnalyzeTrackTopic.__table__)
            .where(*criteria)
            .order_by(GwyAnalyzeTrackTopic.id)
            .limit(limit)
            .offset(offset)
        )
        return await self._siis._mappings(stmt)

    async def list_articles_by_topic_ids(self, topic_ids: list[int]) -> list[dict]:
        if not topic_ids:
            return []
        stmt = (
            select(
                GwyTrackArticle.id,
                GwyTrackArticle.topic_id,
                GwyTrackArticle.tenant_id,
                GwyTrackArticle.published,
            )
            .where(
                GwyTrackArticle.topic_id.in_(topic_ids),
                GwyTrackArticle.del_flag == 0,
            )
        )
        return await self._siis._mappings(stmt)

    async def alert_counts_by_topic_ids(self, topic_ids: list[int]) -> dict[int, int]:
        if not topic_ids:
            return {}
        stmt = (
            select(OntoReportAlertRecord.topic_id, func.count().label("alert_count"))
            .where(
                OntoReportAlertRecord.del_flag == 0,
                OntoReportAlertRecord.topic_id.in_(topic_ids),
            )
            .group_by(OntoReportAlertRecord.topic_id)
        )
        rows = await self._onto._mappings(stmt)
        return {
            int(row["topic_id"]): int(row["alert_count"])
            for row in rows
            if row["topic_id"] is not None
        }

    # -- 统一知识图谱 -------------------------------------------------------
    async def list_personal_kg_nodes(self) -> list[dict]:
        stmt = select(GwyTrackKgNode.__table__).where(GwyTrackKgNode.del_flag == 0)
        return await self._siis._mappings(stmt)

    async def list_global_kg_nodes(self) -> list[dict]:
        stmt = select(OntoGlobalKgNode.__table__).where(OntoGlobalKgNode.del_flag == 0)
        return await self._onto._mappings(stmt)

    # -- 全局查询分页 -------------------------------------------------------
    async def list_global_entities(self, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(OntoGlobalDiscoveredEntity.__table__)
            .where(OntoGlobalDiscoveredEntity.del_flag == 0)
            .order_by(OntoGlobalDiscoveredEntity.total_mention_count.desc())
            .limit(limit)
            .offset(offset)
        )
        return await self._onto._mappings(stmt)

    async def list_global_relations(self, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(OntoGlobalBilateralRelation.__table__)
            .where(OntoGlobalBilateralRelation.del_flag == 0)
            .order_by(OntoGlobalBilateralRelation.sample_count.desc())
            .limit(limit)
            .offset(offset)
        )
        return await self._onto._mappings(stmt)

    async def list_global_kg_nodes_page(self, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(OntoGlobalKgNode.__table__)
            .where(OntoGlobalKgNode.del_flag == 0)
            .order_by(OntoGlobalKgNode.cross_tenant_weight.desc())
            .limit(limit)
            .offset(offset)
        )
        return await self._onto._mappings(stmt)

    async def list_global_kg_edges_page(self, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(OntoGlobalKgEdge.__table__)
            .where(OntoGlobalKgEdge.del_flag == 0)
            .order_by(OntoGlobalKgEdge.cross_tenant_weight.desc())
            .limit(limit)
            .offset(offset)
        )
        return await self._onto._mappings(stmt)

    # -- 主任概览计数 -------------------------------------------------------
    async def count_global(self, model) -> int:
        return await self._onto._count(model, model.del_flag == 0)

    async def count_distinct_article_tenants(self) -> int:
        async with self._siis._factory() as session:
            stmt = select(func.count(func.distinct(GwyTrackArticle.tenant_id))).where(
                GwyTrackArticle.del_flag == 0
            )
            return int((await session.execute(stmt)).scalar_one() or 0)

    async def count_articles(self) -> int:
        return await self._siis._count(GwyTrackArticle, GwyTrackArticle.del_flag == 0)


class GlobalKnowledgeRepository:
    """全局实体合并与合并日志。"""

    def __init__(self, onto_session: async_sessionmaker) -> None:
        self._onto = _BaseRepository(onto_session)

    async def find_duplicate_entities(self, tenant_id: int) -> list[dict]:
        stmt = (
            select(
                OntoCommonDiscoveredEntity.entity_name,
                OntoCommonDiscoveredEntity.entity_type,
                func.min(OntoCommonDiscoveredEntity.id).label("keep_id"),
                func.count().label("cnt"),
            )
            .where(
                OntoCommonDiscoveredEntity.tenant_id == tenant_id,
                OntoCommonDiscoveredEntity.del_flag == 0,
                OntoCommonDiscoveredEntity.status == "DISCOVERED",
            )
            .group_by(
                OntoCommonDiscoveredEntity.entity_name,
                OntoCommonDiscoveredEntity.entity_type,
            )
            .having(func.count() > 1)
        )
        return await self._onto._mappings(stmt)

    async def find_entity_ids(
        self, tenant_id: int, entity_name: str, entity_type: str | None, exclude_id: int
    ) -> list[int]:
        criteria = [
            OntoCommonDiscoveredEntity.tenant_id == tenant_id,
            OntoCommonDiscoveredEntity.del_flag == 0,
            OntoCommonDiscoveredEntity.entity_name == entity_name,
            OntoCommonDiscoveredEntity.id != exclude_id,
        ]
        if entity_type is None:
            criteria.append(OntoCommonDiscoveredEntity.entity_type.is_(None))
        else:
            criteria.append(OntoCommonDiscoveredEntity.entity_type == entity_type)
        rows = await self._onto._list(OntoCommonDiscoveredEntity, *criteria)
        return [int(row.id) for row in rows]

    async def insert_merge_log(self, values: dict) -> int:
        return await self._onto._insert_values(OntoCommonMergeLog, values)

    async def migrate_relation_assets(self, source_id: int, target_id: int, tenant_id: int) -> None:
        await self._onto._update(
            OntoCommonTenantRelationAsset,
            [
                OntoCommonTenantRelationAsset.subject_entity_id == source_id,
                OntoCommonTenantRelationAsset.tenant_id == tenant_id,
            ],
            {"subject_entity_id": target_id},
        )
        await self._onto._update(
            OntoCommonTenantRelationAsset,
            [
                OntoCommonTenantRelationAsset.object_entity_id == source_id,
                OntoCommonTenantRelationAsset.tenant_id == tenant_id,
            ],
            {"object_entity_id": target_id},
        )

    async def get_mention_count(self, entity_id: int) -> int:
        row = await self._onto._one(OntoCommonDiscoveredEntity, OntoCommonDiscoveredEntity.id == entity_id)
        return int(row.mention_count or 0) if row is not None else 0

    async def add_mention_count(self, target_id: int, delta: int, operator: str) -> None:
        row = await self._onto._one(OntoCommonDiscoveredEntity, OntoCommonDiscoveredEntity.id == target_id)
        if row is None:
            return
        await self._onto._update(
            OntoCommonDiscoveredEntity,
            [OntoCommonDiscoveredEntity.id == target_id],
            {
                "mention_count": int(row.mention_count or 0) + delta,
                "updated_by": operator,
            },
        )

    async def soft_delete_entity(self, entity_id: int, operator: str) -> None:
        await self._onto._update(
            OntoCommonDiscoveredEntity,
            [OntoCommonDiscoveredEntity.id == entity_id],
            {"del_flag": 1, "updated_by": operator},
        )

    async def list_merge_logs(self, tenant_id: int, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(OntoCommonMergeLog.__table__)
            .where(
                OntoCommonMergeLog.tenant_id == tenant_id,
                OntoCommonMergeLog.del_flag == 0,
            )
            .order_by(OntoCommonMergeLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return await self._onto._mappings(stmt)


CATEGORY_MODELS = {
    "discoveredEntity": OntoCommonDiscoveredEntity,
    "tenantRelationAsset": OntoCommonTenantRelationAsset,
    "personalVectorIndex": OntoCommonPersonalVectorIndex,
    "llmChatHistory": OntoCommonLlmChatHistory,
}

SEARCH_COLUMNS = {
    "discoveredEntity": ["entity_name"],
    "tenantRelationAsset": ["relation_type"],
    "personalVectorIndex": [],
    "llmChatHistory": ["agent_name", "content"],
}


class WorkspaceRepository:
    """知识沉淀域通用 CRUD；表名由固定分类映射决定，列名做白名单校验。"""

    categories = list(CATEGORY_MODELS.keys())

    def __init__(self, onto_session: async_sessionmaker) -> None:
        self._onto = _BaseRepository(onto_session)

    def _table(self, category: str):
        model = CATEGORY_MODELS.get(category)
        if model is None:
            raise ValueError(f"Unknown workspace category: {category}")
        return model, model.__table__

    async def find_all(self, category: str, tenant_id: int | None) -> list[dict]:
        _, table = self._table(category)
        stmt = (
            select(table)
            .where(table.c.del_flag == 0, table.c.tenant_id == tenant_id)
            .order_by(table.c.id.desc())
        )
        return await self._onto._mappings(stmt)

    async def find_page(self, category: str, tenant_id: int | None, page_num: int, page_size: int) -> dict:
        _, table = self._table(category)
        total = await self._onto._count(
            CATEGORY_MODELS[category],
            CATEGORY_MODELS[category].del_flag == 0,
            CATEGORY_MODELS[category].tenant_id == tenant_id,
        )
        if total == 0:
            return {
                "records": [],
                "total": 0,
                "pageNum": page_num,
                "pageSize": page_size,
                "pages": 0,
            }
        stmt = (
            select(table)
            .where(table.c.del_flag == 0, table.c.tenant_id == tenant_id)
            .order_by(table.c.id.desc())
            .limit(page_size)
            .offset((page_num - 1) * page_size)
        )
        records = await self._onto._mappings(stmt)
        pages = math.ceil(total / page_size) if page_size > 0 else 0
        return {
            "records": records,
            "total": total,
            "pageNum": page_num,
            "pageSize": page_size,
            "pages": pages,
        }

    async def find_by_id(self, category: str, tenant_id: int | None, row_id: int) -> dict | None:
        _, table = self._table(category)
        stmt = select(table).where(
            table.c.id == row_id,
            table.c.del_flag == 0,
            table.c.tenant_id == tenant_id,
        )
        rows = await self._onto._mappings(stmt)
        return rows[0] if rows else None

    async def create(self, category: str, tenant_id: int | None, created_by: str, data: dict) -> int:
        model, table = self._table(category)
        allowed = set(table.c.keys()) - {"id"}
        values = {key: value for key, value in data.items() if key in allowed}
        now = datetime.now()
        values["tenant_id"] = tenant_id
        values["del_flag"] = 0
        values.setdefault("created_at", now)
        values["updated_at"] = now
        values["created_by"] = created_by
        return await self._onto._insert_values(model, values)

    async def update(
        self, category: str, tenant_id: int | None, row_id: int, data: dict
    ) -> int:
        model, table = self._table(category)
        immutable = {"id", "tenant_id", "created_at", "created_by", "del_flag"}
        values = {
            key: value
            for key, value in data.items()
            if key in table.c.keys() and key not in immutable
        }
        values["updated_at"] = datetime.now()
        return await self._onto._update(
            model,
            [table.c.id == row_id, table.c.del_flag == 0, table.c.tenant_id == tenant_id],
            values,
        )

    async def delete(self, category: str, tenant_id: int | None, row_id: int) -> int:
        model, table = self._table(category)
        return await self._onto._update(
            model,
            [table.c.id == row_id, table.c.del_flag == 0, table.c.tenant_id == tenant_id],
            {"del_flag": 1, "updated_at": datetime.now()},
        )

    async def count(self, category: str, tenant_id: int | None) -> int:
        model, table = self._table(category)
        return await self._onto._count(
            model, table.c.del_flag == 0, table.c.tenant_id == tenant_id
        )

    async def search(self, keyword: str, category: str | None, limit: int) -> list[dict]:
        like = f"%{keyword}%"
        results: list[dict] = []
        targets = [category] if category else list(CATEGORY_MODELS.keys())
        for cat in targets:
            columns = SEARCH_COLUMNS.get(cat, [])
            if not columns:
                continue
            _, table = self._table(cat)
            conditions = [table.c[col].like(like) for col in columns]
            stmt = (
                select(table)
                .where(table.c.del_flag == 0, or_(*conditions))
                .limit(limit)
            )
            rows = await self._onto._mappings(stmt)
            if category is None:
                for row in rows:
                    row["_category"] = cat
            results.extend(rows)
        return results

    async def query_by_filters(
        self,
        category: str,
        tenant_id: int | None,
        filters: dict,
        page_num: int,
        page_size: int,
    ) -> list[dict]:
        _, table = self._table(category)
        criteria = [table.c.del_flag == 0, table.c.tenant_id == tenant_id]
        for key, value in filters.items():
            if key in table.c.keys():
                criteria.append(table.c[key] == value)
        stmt = (
            select(table)
            .where(*criteria)
            .order_by(table.c.id.desc())
            .limit(page_size)
            .offset((page_num - 1) * page_size)
        )
        return await self._onto._mappings(stmt)
