"""Worldview Explorer API — Cohezion's interpretive ToE mapping of cultural traditions.

Exposes the 17 cultural/religious traditions' 10-step mappings, interpretive
cross-tradition convergences, per-step comparative views, and vault knowledge graph data
for the Genesis Engine webapp (Tab 9: Worldview Explorer + VaultKnowledgeGraph).

Every tradition/convergence/step response carries ``notice`` (INTERPRETIVE_NOTICE): the
mapping is Cohezion's analogy, generated and unreviewed by the communities concerned.
Speculative frameworks (stealthskater) are served separately under
``/speculative-frameworks`` and are never listed as traditions.

Exposure (2026-09-21): ``worldviews_router`` is not mounted in ``cohezion.api:app``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from cohezion.worldviews.tradition_data import (
    CATEGORY_TRADITION,
    INTERPRETIVE_NOTICE,
    TOE_STEPS,
    get_convergences,
    get_speculative_frameworks,
    get_step_across_traditions,
    get_tradition,
    get_traditions,
)
from cohezion.worldviews.vault_graph import get_vault_graph


logger = logging.getLogger(__name__)

worldviews_router = APIRouter(prefix="/worldviews", tags=["worldviews"])


@worldviews_router.get("/traditions")
async def list_traditions() -> dict:
    """List cultural/religious traditions (speculative frameworks excluded)."""
    traditions = get_traditions()
    return {
        "notice": INTERPRETIVE_NOTICE,
        "count": len(traditions),
        "traditions": [t.to_summary() for t in traditions],
    }


@worldviews_router.get("/traditions/{slug}")
async def get_tradition_detail(slug: str) -> dict:
    """Get Cohezion's interpretive 10-step mapping for a single tradition."""
    tradition = get_tradition(slug)
    if tradition is None or tradition.category != CATEGORY_TRADITION:
        slugs = [t.slug for t in get_traditions()]
        raise HTTPException(
            status_code=404, detail=f"Tradition '{slug}' not found. Available: {slugs}"
        )
    return {"notice": INTERPRETIVE_NOTICE, **tradition.to_dict()}


@worldviews_router.get("/speculative-frameworks")
async def list_speculative_frameworks() -> dict:
    """Speculative/fringe-physics frameworks — a separate category, not traditions."""
    frameworks = get_speculative_frameworks()
    return {
        "notice": INTERPRETIVE_NOTICE,
        "count": len(frameworks),
        "frameworks": [f.to_dict() for f in frameworks],
    }


@worldviews_router.get("/convergences")
async def list_convergences() -> dict:
    """Return the 6 interpretive (template-produced) convergence patterns."""
    convergences = get_convergences()
    return {
        "notice": INTERPRETIVE_NOTICE,
        "count": len(convergences),
        "convergences": [c.to_dict() for c in convergences],
    }


@worldviews_router.get("/step/{step_index}")
async def get_step_comparison(step_index: int) -> dict:
    """Compare all traditions' mapping for a single ToE step (0-9)."""
    if not 0 <= step_index <= 9:
        raise HTTPException(status_code=400, detail=f"Step index must be 0-9, got {step_index}")
    return {
        "notice": INTERPRETIVE_NOTICE,
        "step_index": step_index,
        "step_name": TOE_STEPS[step_index],
        "traditions": get_step_across_traditions(step_index),
    }


# ─── Vault Knowledge Graph Endpoints ──────────────────────────────


@worldviews_router.get("/vault-graph")
async def get_vault_graph_data(
    refresh: bool = Query(False, description="Force re-parse of cortex directory"),
) -> dict:
    """Full vault knowledge graph — nodes, edges, and clusters.

    Parses ``~/vaults/cohezion-vault/cortex/`` for wikilinks and YAML
    frontmatter, returning the MOC structure for VaultKnowledgeGraph.tsx.
    """
    graph = get_vault_graph(force_refresh=refresh)
    return graph.to_dict()


@worldviews_router.get("/vault-graph/traditions")
async def get_vault_tradition_subgraph() -> dict:
    """Indigenous cosmology subgraph — tradition-related nodes and their links.

    Filters the full vault graph to nodes tagged with ``indigenous-cosmology``,
    ``TOE``, or ``cross-tradition``, returning only intra-subgraph edges.
    """
    graph = get_vault_graph()
    return graph.get_tradition_subgraph()


@worldviews_router.get("/vault-graph/clusters")
async def get_vault_clusters() -> dict:
    """Vault graph clusters grouped by aspect (doer/thinker/knower)."""
    graph = get_vault_graph()
    clusters = graph.get_clusters()
    return {
        "count": len(clusters),
        "total_nodes": graph.node_count,
        "clusters": clusters,
    }
