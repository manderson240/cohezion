"""Tests for SurpriseActionGate — gating active-inference decisions through the Quadrature Nexus.

Unit tests use a fake nexus so the gate's own logic (risk classification, proposal mapping,
approval passthrough) is deterministic and isolated. One integration test exercises the real
``QuadratureNexus`` to prove the wiring and that the Resource voice responds to budget — without
coupling the test to the Nexus's exact consensus threshold.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cohezion.world_model.surprise_action_gate import GateOutcome, SurpriseActionGate
from cohezion.world_model.surprise_router import ActionMode, SurpriseDecision


def _decision(mode: ActionMode, tier: str, normalized: float = 0.9) -> SurpriseDecision:
    return SurpriseDecision(
        mode=mode,
        tier=tier,
        surprise=normalized,
        normalized=normalized,
        rationale="test",
    )


@dataclass
class _FakeResult:
    approved: bool
    consensus_score: float
    rejection_reason: str | None = None


class _FakeNexus:
    """Records the last proposal and returns a configurable deliberation result."""

    def __init__(self, approved: bool, consensus: float, reason: str | None = None):
        self._approved = approved
        self._consensus = consensus
        self._reason = reason
        self.last_proposal = None
        self.calls = 0

    async def deliberate(self, proposal):
        self.calls += 1
        self.last_proposal = proposal
        return _FakeResult(self._approved, self._consensus, self._reason)


# -- construction --------------------------------------------------------------


def test_rejects_bad_base_tier():
    with pytest.raises(ValueError):
        SurpriseActionGate(nexus=_FakeNexus(True, 0.9), base_tier="gpu")


# -- low-risk path passes ungated ---------------------------------------------


@pytest.mark.asyncio
async def test_exploit_at_base_tier_passes_ungated():
    nexus = _FakeNexus(approved=False, consensus=0.0)  # would reject if consulted
    gate = SurpriseActionGate(nexus=nexus, base_tier="npu")
    out = await gate.gate(_decision(ActionMode.EXPLOIT, "npu"))
    assert isinstance(out, GateOutcome)
    assert out.approved is True  # auto-approved despite the rejecting nexus
    assert out.gated is False
    assert out.consensus_score is None
    assert nexus.calls == 0  # nexus never consulted for low-risk


# -- risky paths are gated -----------------------------------------------------


@pytest.mark.asyncio
async def test_explore_is_gated():
    nexus = _FakeNexus(approved=True, consensus=0.9)
    gate = SurpriseActionGate(nexus=nexus, base_tier="npu")
    out = await gate.gate(_decision(ActionMode.EXPLORE, "cpu"))
    assert out.gated is True
    assert out.approved is True
    assert out.consensus_score == 0.9
    assert nexus.calls == 1


@pytest.mark.asyncio
async def test_tier_escalation_while_exploiting_is_gated():
    """EXPLOIT held by hysteresis but tier climbed above base => still risky, still gated."""
    nexus = _FakeNexus(approved=True, consensus=0.88)
    gate = SurpriseActionGate(nexus=nexus, base_tier="npu")
    out = await gate.gate(_decision(ActionMode.EXPLOIT, "igpu"))
    assert out.gated is True
    assert nexus.calls == 1


@pytest.mark.asyncio
async def test_rejection_passthrough():
    nexus = _FakeNexus(approved=False, consensus=0.72, reason="resource veto")
    gate = SurpriseActionGate(nexus=nexus, base_tier="npu")
    out = await gate.gate(_decision(ActionMode.EXPLORE, "cpu"))
    assert out.approved is False
    assert out.consensus_score == 0.72
    assert out.reason == "resource veto"


# -- proposal mapping carries the active-inference context ---------------------


@pytest.mark.asyncio
async def test_proposal_carries_budget_and_surprise_context():
    nexus = _FakeNexus(approved=True, consensus=0.9)
    gate = SurpriseActionGate(nexus=nexus, base_tier="npu")
    await gate.gate(_decision(ActionMode.EXPLORE, "cpu", normalized=0.95), budget_available=True)
    p = nexus.last_proposal
    assert p is not None
    assert p.context["budget_available"] is True
    assert p.context["tier"] == "cpu"
    assert p.context["normalized_surprise"] == 0.95
    assert p.priority == 0.95  # urgency reflects how broken the prediction is
    assert "cpu" in p.action


@pytest.mark.asyncio
async def test_outcome_to_dict():
    nexus = _FakeNexus(approved=True, consensus=0.9)
    gate = SurpriseActionGate(nexus=nexus)
    out = await gate.gate(_decision(ActionMode.EXPLORE, "cpu"))
    d = out.to_dict()
    assert set(d) == {"approved", "gated", "consensus_score", "reason", "decision"}
    assert d["decision"]["tier"] == "cpu"


# -- integration: real QuadratureNexus ----------------------------------------


@pytest.mark.asyncio
async def test_integration_real_nexus_budget_raises_consensus():
    """Against the real Nexus: a bare surprise escalation is conservative, and making budget
    available raises consensus (the Resource voice responds). No threshold coupling."""
    gate_no_budget = SurpriseActionGate(base_tier="npu")  # real QuadratureNexus
    gate_budget = SurpriseActionGate(base_tier="npu")
    out_no = await gate_no_budget.gate(_decision(ActionMode.EXPLORE, "cpu"), budget_available=False)
    out_yes = await gate_budget.gate(_decision(ActionMode.EXPLORE, "cpu"), budget_available=True)

    assert out_no.gated and out_yes.gated
    assert isinstance(out_no.consensus_score, float)
    # Resource voice rewards available budget -> consensus is monotonic in budget.
    assert out_yes.consensus_score > out_no.consensus_score
    # Governor default: a bare surprise spike with no budget does not clear consensus.
    assert out_no.approved is False
