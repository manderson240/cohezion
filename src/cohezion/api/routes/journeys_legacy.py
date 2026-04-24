"""Legacy journey-tracker stub routes (501 Not Implemented).

These endpoints are placeholders that 501 until the new
cohezion.compound.journey_tracker is wired up. Use /compound/history for
execution history.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException


journeys_legacy_router = APIRouter(tags=["journeys-legacy"])


_JOURNEY_TRACKER_UNAVAILABLE = HTTPException(
    status_code=501,
    detail="Journey tracker endpoints are being migrated to the compound module. "
    "Use /compound/history for execution history.",
)


@journeys_legacy_router.get("/journeys")
async def list_journeys():
    """List recent agent journeys."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@journeys_legacy_router.get("/journeys/{journey_id}")
async def get_journey(journey_id: str):
    """Get a specific journey with full trajectory."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@journeys_legacy_router.get("/journeys/{journey_id}/trajectory")
async def get_journey_trajectory(journey_id: str):
    """Get physics trajectory for visualization."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@journeys_legacy_router.post("/journeys/demo")
async def create_demo_journey():
    """Create a demo journey to showcase visualization."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@journeys_legacy_router.get("/journeys/{journey_id}/visualize")
async def visualize_journey(journey_id: str):
    """Render an animated visualization of the journey trajectory."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@journeys_legacy_router.get("/journeys/{journey_id}/plot")
async def plot_journey(journey_id: str):
    """Render a multi-panel 12D physics visualization of the journey."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@journeys_legacy_router.get("/compare/calm-vs-llm/{journey_id}")
async def compare_calm_llm(journey_id: str):
    """Compare CALM continuous trajectory vs standard LLM discrete steps."""
    raise _JOURNEY_TRACKER_UNAVAILABLE
