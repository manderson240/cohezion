"""Knowledge / skill / vault search routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cohezion.mcp.knowledge_server import get_server as get_knowledge_server


knowledge_router = APIRouter(tags=["knowledge"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeQueryResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    count: int


@knowledge_router.post("/knowledge/search")
async def search_knowledge(request: SearchRequest):
    """Search knowledge base."""
    server = get_knowledge_server()
    results = server.search_knowledge(request.query, request.limit)
    return {"results": results}


@knowledge_router.get("/knowledge/skills")
async def list_skills():
    """List all skills."""
    server = get_knowledge_server()
    return {"skills": server.list_skills()}


@knowledge_router.get("/knowledge/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get a specific skill."""
    server = get_knowledge_server()
    result = server.get_skill(skill_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@knowledge_router.post("/knowledge/query", response_model=KnowledgeQueryResponse)
async def knowledge_query(request: KnowledgeQueryRequest):
    """Search the knowledge graph for relevant entries."""
    from cohezion.knowledge_graph.query_engine import KnowledgeGraphQueryEngine

    engine = KnowledgeGraphQueryEngine()
    results = engine.search_knowledge(request.query, top_k=request.top_k)
    return KnowledgeQueryResponse(query=request.query, results=results, count=len(results))
