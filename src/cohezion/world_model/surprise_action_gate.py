"""Gate Active-Inference action decisions through the Quadrature Nexus consensus.

Free-energy action selection on its own (``SurpriseRouter``) is a greedy controller: it will
escalate to a more capable -- and more expensive -- tier whenever model surprise spikes. The
Quadrature Nexus is cohezion's governor: every major action passes 4 opposing voices
(Architect / Engineer / Ethicist / Resource) and is taken only at > 0.85 consensus.

``SurpriseActionGate`` composes the two: **surprise proposes, the Nexus disposes.**

    SurpriseRouter.observe(surprise) -> SurpriseDecision   (free-energy: explore vs exploit)
        -> SurpriseActionGate.gate(decision)               (4-voice consensus governor)
            -> GateOutcome(approved, consensus_score, ...)

Only *risky* decisions are gated: an EXPLORE decision, or any tier escalation above the base
tier, spends extra compute and so must clear consensus. Low-risk EXPLOIT-at-base-tier decisions
pass through ungated (the governor should not tax the cheap, confident path). The Resource voice
("what can we afford?") is the natural veto: with no budget available a bare surprise spike scores
~0.725 consensus and is rejected -- the controller cannot escalate just because it is surprised.

The gate is dependency-light: ``QuadratureNexus.deliberate`` scores its voices deterministically
(no LLM calls), so gating a routing decision is a pure async computation -- fast and testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.world_model.surprise_router import ActionMode, SurpriseDecision


__all__ = ["GateOutcome", "SurpriseActionGate"]

# Fleet tiers, cheapest -> most capable. Mirrors SurpriseRouter._TIERS.
_TIER_RANK = {"npu": 0, "igpu": 1, "cpu": 2}


@dataclass(frozen=True)
class GateOutcome:
    """Result of gating one SurpriseDecision through the Nexus."""

    approved: bool  # may the action be taken?
    gated: bool  # True if it went through the Nexus; False if auto-passed as low-risk
    decision: SurpriseDecision  # the originating active-inference decision
    consensus_score: float | None  # Nexus consensus (None when ungated)
    reason: str

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "gated": self.gated,
            "consensus_score": self.consensus_score,
            "reason": self.reason,
            "decision": self.decision.to_dict(),
        }


class SurpriseActionGate:
    """Gate surprise-driven EXPLORE / tier-escalation actions through 4-voice consensus.

    Parameters
    ----------
    nexus:
        A ``QuadratureNexus`` instance (or compatible object exposing async ``deliberate``).
        Defaults to a fresh ``QuadratureNexus`` with equal voice weights.
    base_tier:
        The tier below which exploitation is considered low-risk and passes ungated
        (default ``"npu"`` -- the cheapest fleet tier).
    """

    def __init__(self, nexus: object | None = None, base_tier: str = "npu") -> None:
        if base_tier not in _TIER_RANK:
            raise ValueError(f"base_tier must be one of {tuple(_TIER_RANK)}")
        if nexus is None:
            from cohezion.swarm.quadrature_nexus import QuadratureNexus

            nexus = QuadratureNexus()
        self._nexus = nexus
        self._base_tier = base_tier

    def _is_escalation(self, tier: str) -> bool:
        """True if `tier` is more capable (and costlier) than the base tier."""
        return _TIER_RANK.get(tier, 0) > _TIER_RANK[self._base_tier]

    def _is_risky(self, decision: SurpriseDecision) -> bool:
        """A decision is risky (worth gating) if it explores or escalates the tier."""
        return decision.mode is ActionMode.EXPLORE or self._is_escalation(decision.tier)

    def _to_proposal(
        self, decision: SurpriseDecision, *, budget_available: bool, submitted_by: str
    ) -> object:
        """Map an active-inference decision into a QuadratureProposal.

        The description names the cost/resource tradeoff honestly so the Resource and Engineer
        voices can weigh it; priority carries the normalized surprise so urgency reflects how
        far the world model's prediction has broken down.
        """
        from cohezion.swarm.quadrature_nexus import QuadratureProposal

        action = f"surprise_{decision.mode.value}_tier_{decision.tier}"
        description = (
            f"Active-Inference {decision.mode.value}: route to {decision.tier} tier to resolve "
            f"high model surprise (normalized={decision.normalized:.2f}). Resource/cost tradeoff: "
            f"escalating tier spends more compute; gate on whether the budget can afford it."
        )
        return QuadratureProposal(
            action=action,
            description=description,
            context={
                "budget_available": budget_available,
                "surprise": decision.surprise,
                "normalized_surprise": decision.normalized,
                "tier": decision.tier,
                "mode": decision.mode.value,
            },
            submitted_by=submitted_by,
            priority=decision.normalized,
        )

    async def gate(
        self,
        decision: SurpriseDecision,
        *,
        budget_available: bool = False,
        submitted_by: str = "surprise_router",
    ) -> GateOutcome:
        """Decide whether an active-inference action may be taken.

        Low-risk decisions (EXPLOIT at/below base tier) auto-pass ungated. Risky ones
        (EXPLORE or tier escalation) are deliberated by the Nexus and approved only at
        > 0.85 consensus -- so the Resource voice can veto an unaffordable escalation.
        """
        if not self._is_risky(decision):
            return GateOutcome(
                approved=True,
                gated=False,
                decision=decision,
                consensus_score=None,
                reason="low-risk exploit at base tier; ungated",
            )
        proposal = self._to_proposal(
            decision, budget_available=budget_available, submitted_by=submitted_by
        )
        result = await self._nexus.deliberate(proposal)
        reason = (
            result.rejection_reason
            if not result.approved and result.rejection_reason
            else (
                "ratified by quadrature consensus"
                if result.approved
                else "below consensus threshold"
            )
        )
        return GateOutcome(
            approved=bool(result.approved),
            gated=True,
            decision=decision,
            consensus_score=float(result.consensus_score),
            reason=reason,
        )
