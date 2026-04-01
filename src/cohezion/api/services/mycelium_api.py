"""Mycelium API — Knowledge distribution network status and spore queries.

Exposes the Mycelium distributed knowledge network for the Genesis Engine webapp.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cohezion.learning.mycelium_network import MyceliumNetwork
from cohezion.learning.mycelium_registry import MyceliumRegistry


logger = logging.getLogger(__name__)

mycelium_router = APIRouter(prefix="/mycelium", tags=["mycelium"])

# Module-level singletons
_network: MyceliumNetwork | None = None
_registry: MyceliumRegistry | None = None


def _get_network() -> MyceliumNetwork:
    global _network
    if _network is None:
        _network = MyceliumNetwork()
    return _network


def _get_registry() -> MyceliumRegistry:
    global _registry
    if _registry is None:
        _registry = MyceliumRegistry()
    return _registry


class NetworkStatusResponse(BaseModel):
    connected_evos: list[str]
    evo_count: int
    spore_counts: dict[str, int]


class SporeResponse(BaseModel):
    origin_evo_id: str
    topic: str
    summary_text: str
    confidence: float


class SporesQueryResponse(BaseModel):
    spores: list[SporeResponse]
    count: int
    topic: str


class SkillResponse(BaseModel):
    skill_name: str
    skill_content: str
    source_entries: list[str]
    content_hash: str


class SkillsResponse(BaseModel):
    skills: list[SkillResponse]
    count: int


@mycelium_router.get("/network", response_model=NetworkStatusResponse)
async def get_mycelium_network() -> NetworkStatusResponse:
    """Get connected EVOs and spore counts.

    Shows the topology of the Mycelium knowledge distribution network.
    """
    network = _get_network()
    evos = sorted(network._connected_evos)
    spore_counts = {evo: len(network._network_graph.get(evo, [])) for evo in evos}
    return NetworkStatusResponse(
        connected_evos=evos,
        evo_count=len(evos),
        spore_counts=spore_counts,
    )


@mycelium_router.get("/spores", response_model=SporesQueryResponse)
async def query_spores(
    topic: str = Query(..., description="Topic keyword to filter spores"),
    evo_id: str = Query("*", description="EVO ID to query (default: all)"),
) -> SporesQueryResponse:
    """Query knowledge spores by topic.

    Returns matching KnowledgeSpores from the Mycelium cache.
    """
    network = _get_network()
    results = []

    target_evos = sorted(network._connected_evos) if evo_id == "*" else [evo_id]
    for eid in target_evos:
        matches = network.query_insights(eid, topic)
        for spore in matches:
            results.append(
                SporeResponse(
                    origin_evo_id=spore.origin_evo_id,
                    topic=spore.topic,
                    summary_text=spore.summary_text,
                    confidence=spore.confidence,
                )
            )

    return SporesQueryResponse(spores=results, count=len(results), topic=topic)


@mycelium_router.get("/skills", response_model=SkillsResponse)
async def get_mycelium_skills() -> SkillsResponse:
    """Get auto-synthesized skills from journal entries.

    Skills are synthesized by the MyceliumRegistry during audit cycles.
    """
    registry = _get_registry()
    skills = [
        SkillResponse(
            skill_name=s.skill_name,
            skill_content=s.skill_content,
            source_entries=s.source_entries,
            content_hash=s.content_hash,
        )
        for s in registry.skills.values()
    ]
    return SkillsResponse(skills=skills, count=len(skills))
