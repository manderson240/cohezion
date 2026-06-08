"""Regression guard: the swarm reaches the 225-skill registry (extend-to-all-skills).

`plan_team(intent)` searches the CapabilityRegistry and composes the MATCHING skills into
the team. Verified 2026-06-07: skill-specific intents pull their domain skills, so the
swarm already reaches all skills — this locks that in so a registry regression (or a
generic-only matcher) is caught.
"""

from __future__ import annotations

import pytest

from cohezion.swarm.team_orchestrator import TeamOrchestrator


@pytest.mark.parametrize(
    "intent,tokens",
    [
        ("optimize AMD GEMM MXFP4 kernels on the iGPU", ("amd", "gemm", "mxfp4")),
        ("audit SurrealDB schema and bitemporal writes", ("surreal",)),
        ("run adversarial TDD on a new module", ("adversarial", "tdd")),
    ],
)
def test_plan_team_reaches_domain_skill(intent, tokens):
    plan = TeamOrchestrator().plan_team(intent, max_agents=3)
    names = " ".join(a.name for a in plan.agents).lower()
    # DISCRIMINATING: a registry missing the 225 skills (or matching generically)
    # would not surface a domain-specific agent for these intents.
    assert any(t in names for t in tokens), f"{intent!r} -> {names!r}"
    assert len(plan.agents) >= 1
