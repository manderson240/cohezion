"""Tests for reliability/residency_awareness.py.

Covers system hardware truth anchors.
"""

from __future__ import annotations

from cohezion.reliability.residency_awareness import (
    ResidencyAnchorBase,
    get_residency_anchors,
)


def test_get_anchors():
    """[P0] Should return correct hardware anchors."""
    anchors = get_residency_anchors()
    assert anchors["cpu"] == "AMD RYZEN AI MAX+ 395 (Strix Halo)"
    assert anchors["ram_gb"] == 128
    assert "/home/mike-anderson/dev/cohezion" in anchors["project_root"]

def test_get_context_block():
    """[P0] Should generate formatted context block."""
    block = ResidencyAnchorBase.get_context_block()
    assert "[SYSTEM RESIDENCY ANCHORS]" in block
    assert "128GB" in block
    assert "Strix Halo" in block
