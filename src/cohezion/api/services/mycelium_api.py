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


def _get_network() -> MyceliumNetwork:
    global _network
    if _network is None:
        _network = MyceliumNetwork()
    return _network


def _get_registry() -> MyceliumRegistry:
    # Shared singleton so the executor (writer) and this reader see the same
    # synthesized skills — closes the experience->skill->read-back recursion loop.
    return MyceliumRegistry.get_instance()


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


class PiTurnLog(BaseModel):
    entry_id: str
    content: str
    domain: str = "pattern"


class PiTurnAck(BaseModel):
    accepted: bool


@mycelium_router.post("/turn", response_model=PiTurnAck)
async def log_pi_turn(body: PiTurnLog) -> PiTurnAck:
    """Ingest a Pi agent turn into the Mycelium skill-learning loop."""
    try:
        from cohezion.learning.mycelium_registry import JournalEntry

        registry = _get_registry()
        entry = JournalEntry(
            entry_id=body.entry_id,
            content=body.content,
            domain=body.domain,
        )
        registry.ingest_entry(entry)
        return PiTurnAck(accepted=True)
    except Exception:
        logger.debug("Mycelium turn ingest failed silently", exc_info=True)
        return PiTurnAck(accepted=False)


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
