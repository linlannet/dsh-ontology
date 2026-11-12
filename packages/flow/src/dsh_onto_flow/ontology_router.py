"""本体管理路由：内存态本体库 + Harness AI 代理，对齐 Java ``OntologyController``。

说明：Java 版本体数据同样存于进程内 ``ConcurrentHashMap``，持久化引擎尚未接入；
AI 端点转发到外部 Harness（``dsh.ontology.harness.base-url``）。
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from dsh_onto_base import require_role

router = APIRouter(
    prefix="/api/ontologies", tags=["ontology"], dependencies=[Depends(require_role(1))]
)

_ONTOLOGIES: dict[str, dict] = {}


def _bad_request(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content={"message": message})


def _not_found(message: str) -> JSONResponse:
    return JSONResponse(status_code=404, content={"message": message})


def _build_prompt(ontology_id: str, message: str) -> str:
    lines = ["当前环境："]
    if ontology_id:
        lines.append(f"- 本体库 ID：{ontology_id}")
    lines.append(
        "- 你可以使用以下只读本体检索工具获取真实数据（回答涉及概念定义、层级关系、实体属性的问题时，"
        "必须先调用工具查证，禁止凭空猜测）："
    )
    lines.append("  - plugin__dsh-java-ontology-plugin__ontology_list()：列出可用本体库")
    lines.append(
        "  - plugin__dsh-java-ontology-plugin__ontology_query(ontologyId, query)：查询概念与关系"
    )
    lines.append("  - plugin__dsh-java-ontology-plugin__ontology_search(keyword)：模糊搜索概念")
    lines.append("")
    lines.append(f"用户需求：{message}")
    lines.append("")
    lines.append("回答要求：")
    lines.append("- 使用中文，Markdown 格式，结论先行。")
    lines.append("- 引用工具查询结果时给出关键结论，不要原样转储大段 JSON。")
    return "\n".join(lines)


@router.get("")
async def list_ontologies():
    return list(_ONTOLOGIES.values())


@router.post("")
async def save_ontology(payload: dict):
    name = str(payload.get("name") or "")
    if not name.strip():
        return _bad_request("name 不能为空")
    ontology_id = str(payload.get("id") or "") or str(uuid.uuid4())
    ontology = {
        "id": ontology_id,
        "name": name,
        "description": str(payload.get("description") or ""),
        "source": str(payload.get("source") or ""),
    }
    _ONTOLOGIES[ontology_id] = ontology
    return ontology


@router.delete("/{ontology_id}")
async def delete_ontology(ontology_id: str):
    if _ONTOLOGIES.pop(ontology_id, None) is None:
        return _not_found(f"本体库不存在: {ontology_id}")
    return JSONResponse(status_code=200, content={})


@router.post("/query")
async def query_ontology(payload: dict):
    ontology_id = str(payload.get("ontologyId") or "")
    ontology = _ONTOLOGIES.get(ontology_id)
    if ontology is None:
        return _not_found(f"本体库不存在: {ontology_id}")
    return {
        "ontologyId": ontology_id,
        "ontologyName": ontology.get("name"),
        "query": payload.get("query"),
        "concepts": [],
        "relations": [],
        "message": "查询已接收，本体引擎待接入",
    }


@router.post("/search")
async def search_ontology(payload: dict):
    keyword = str(payload.get("keyword") or "")
    if not keyword.strip():
        return _bad_request("keyword 不能为空")
    return [
        item
        for item in _ONTOLOGIES.values()
        if keyword in str(item.get("name", "")) or keyword in str(item.get("description", ""))
    ]


@router.post("/ai")
async def ai_chat(payload: dict, request: Request):
    agent_id = str(payload.get("agentId") or "")
    message = str(payload.get("message") or "")
    if not agent_id.strip():
        return _bad_request("agentId 不能为空")
    if not message.strip():
        return _bad_request("message 不能为空")
    settings = request.app.state.settings
    prompt = _build_prompt(str(payload.get("ontologyId") or ""), message)
    try:
        async with httpx.AsyncClient(base_url=settings.harness_base_url, timeout=60.0) as client:
            resp = await client.post("/api/agent/message", json={"agentId": agent_id, "message": prompt})
        body = resp.json()
    except Exception as exc:
        return JSONResponse(status_code=502, content={"message": f"Harness 对话失败：{exc}"})
    messages = (body.get("data") or {}).get("messages") or []
    for item in reversed(messages):
        if item.get("role") == "assistant" and (item.get("content") or "").strip():
            return {"answer": item["content"]}
    return JSONResponse(status_code=502, content={"message": "Harness 未返回助手内容"})


@router.post("/ai/stream")
async def ai_stream(payload: dict, request: Request):
    agent_id = str(payload.get("agentId") or "")
    message = str(payload.get("message") or "")
    if not agent_id.strip():
        return _bad_request("agentId 不能为空")
    if not message.strip():
        return _bad_request("message 不能为空")
    settings = request.app.state.settings
    prompt = _build_prompt(str(payload.get("ontologyId") or ""), message)

    async def relay():
        try:
            async with httpx.AsyncClient(base_url=settings.harness_base_url, timeout=None) as client:
                async with client.stream(
                    "POST", "/api/agent/stream", json={"agentId": agent_id, "message": prompt}
                ) as resp:
                    if resp.status_code // 100 != 2:
                        yield f'event: error\ndata: {{"message":"Harness 返回 {resp.status_code}"}}\n\n'
                        return
                    async for chunk in resp.aiter_raw():
                        yield chunk.decode("utf-8", errors="ignore")
        except Exception as exc:
            yield f'event: error\ndata: {{"message":"{exc}"}}\n\n'

    return StreamingResponse(relay(), media_type="text/event-stream")
