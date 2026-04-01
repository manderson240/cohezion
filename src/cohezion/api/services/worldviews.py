"""Worldview Explorer API — indigenous cosmological traditions mapped to the ToE chain.

Exposes 16 traditions' 10-step mappings, cross-tradition convergences,
per-step comparative views, and vault knowledge graph data for the
Genesis Engine webapp (Tab 9: Worldview Explorer + VaultKnowledgeGraph).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from cohezion.worldviews.tradition_data import (
    TOE_STEPS,
    get_convergences,
    get_step_across_traditions,
    get_tradition,
    get_traditions,
)
from cohezion.worldviews.vault_graph import get_vault_graph


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
