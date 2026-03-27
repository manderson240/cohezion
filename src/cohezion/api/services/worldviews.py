"""Worldview Explorer API — indigenous cosmological traditions mapped to the ToE chain.

Exposes 16 traditions' 10-step mappings, cross-tradition convergences,
and per-step comparative views for the Genesis Engine webapp.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from cohezion.worldviews.tradition_data import (
    TOE_STEPS,
    get_convergences,
    get_step_across_traditions,
    get_tradition,
    get_traditions,
)

logger = logging.getLogger(__name__)

worldviews_router = APIRouter(prefix="/worldviews", tags=["worldviews"])


@worldviews_router.get("/traditions")
async def list_traditions() -> dict:
    """List all 16 indigenous traditions with summary metadata."""
    traditions = get_traditions()
    return {
        "count": len(traditions),
        "traditions": [t.to_summary() for t in traditions],
    }


@worldviews_router.get("/traditions/{slug}")
async def get_tradition_detail(slug: str) -> dict:
    """Get full 10-step ToE mapping for a single tradition."""
    tradition = get_tradition(slug)
    if tradition is None:
        slugs = [t.slug for t in get_traditions()]
        raise HTTPException(
            status_code=404, detail=f"Tradition '{slug}' not found. Available: {slugs}"
        )
    return tradition.to_dict()


@worldviews_router.get("/convergences")
async def list_convergences() -> dict:
    """Return the 6 cross-tradition convergence patterns."""
    convergences = get_convergences()
    return {
        "count": len(convergences),
        "convergences": [c.to_dict() for c in convergences],
    }


@worldviews_router.get("/step/{step_index}")
async def get_step_comparison(step_index: int) -> dict:
    """Compare all 16 traditions' mapping for a single ToE step (0-9)."""
    if not 0 <= step_index <= 9:
        raise HTTPException(status_code=400, detail=f"Step index must be 0-9, got {step_index}")
    return {
        "step_index": step_index,
        "step_name": TOE_STEPS[step_index],
        "traditions": get_step_across_traditions(step_index),
    }
