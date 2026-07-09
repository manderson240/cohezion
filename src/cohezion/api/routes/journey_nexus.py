"""FastAPI router for the JourneyNexus endpoints (stub).

Exports consumed by tests/api/test_journey_nexus_router.py.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from cohezion.api.services.journey_nexus import JourneyNexus


router = APIRouter(prefix="/journey-nexus")

# Module-level singleton — replaced by monkeypatch in tests.
_nexus_instance: JourneyNexus | None = None


async def _get_nexus() -> JourneyNexus:
    """Return (or lazily create) the JourneyNexus singleton."""
    global _nexus_instance
    if _nexus_instance is None:
        _nexus_instance = JourneyNexus()
    return _nexus_instance


@router.get("/evo/snapshot")
async def evo_snapshot() -> list[dict[str, Any]]:
    """Return the current EVO event stream snapshot."""
    nexus = await _get_nexus()
    events = nexus.stream_snapshot() if hasattr(nexus, "stream_snapshot") else []
    return [e.__dict__ if hasattr(e, "__dict__") else e for e in events]


@router.get("/quadrature/{journey_id}")
async def quadrature_vote(journey_id: str, mode: str = "preflight") -> Any:
    """Run a Quadrature Nexus vote on *journey_id*."""
    nexus = await _get_nexus()
    result = await nexus.quadrature(journey_id, mode=mode)  # type: ignore[attr-defined]
    return result


@router.get("/narrate/{journey_id}")
async def narrate(journey_id: str, with_image: bool = False) -> Any:
    """Narrate *journey_id*."""
    nexus = await _get_nexus()
    result = await nexus.narrate(journey_id, with_image=with_image)  # type: ignore[call-arg]
    return result


@router.post("/chat/{journey_id}")
async def omni_chat(journey_id: str, body: dict[str, Any]) -> Any:
    """Route a message through the Omni Tier."""
    nexus = await _get_nexus()
    result = await nexus.omni_chat(  # type: ignore[attr-defined]
        journey_id, message=body.get("message", "")
    )
    return result
