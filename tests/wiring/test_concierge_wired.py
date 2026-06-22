"""Discriminating test for the wiring-sweep edge: governance → concierge (2026-06-06).

`concierge` was a genuine production orphan in governance/ — `ConciergeAgent` (a documented
core governance component, CLAUDE.md Governance layer) had ZERO importers anywhere in src
(only its test), and governance/__init__ re-exported nothing. Wired non-destructively via a
guarded `cohezion.governance` __init__ re-export. Cycle-safe (concierge imports no swarm/compound
at module scope). This test fails if the static edge is removed: the public surface must resolve
FROM the package AND be concierge's own objects (an identity check a stale shadow would fail).
"""

from __future__ import annotations

import cohezion.governance as governance
import cohezion.governance.concierge as src


_PUBLIC = ("ConciergeAgent", "SessionBriefing", "RoutingSuggestion", "RoutingRecord")


def test_concierge_surface_reexported_from_governance() -> None:
    for name in _PUBLIC:
        assert hasattr(governance, name), f"governance.{name} unreachable — wiring edge missing"
        assert getattr(governance, name) is getattr(src, name), f"{name} is not the source object"


def test_concierge_agent_is_the_real_class() -> None:
    assert governance.ConciergeAgent is src.ConciergeAgent
