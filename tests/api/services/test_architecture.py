"""Tests for api/services/architecture.py.

Covers live architecture graph generation.
"""

from __future__ import annotations

import pytest

from cohezion.api.services.architecture import (
    _scan_packages,
    get_architecture_graph,
)


def test_scan_packages():
    """[P0] Should scan packages and build graph."""
    graph = _scan_packages()
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
    
    # Check for core packages
    node_ids = [n.id for n in graph.nodes]
    assert "compound" in node_ids
    assert "swarm" in node_ids

@pytest.mark.asyncio
async def test_get_architecture_graph():
    """[P0] Should return architecture graph."""
    graph = await get_architecture_graph(refresh=True)
    assert graph is not None
    assert len(graph.nodes) > 0
