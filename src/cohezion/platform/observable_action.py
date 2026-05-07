# ruff: noqa: SIM105, S110  # best-effort: ignored exceptions are intentional in init/cleanup paths
"""
Observable AI action proposer.
Charter requirement: "Expose internal states and confidence levels *before* action"
"""

import uuid
from collections.abc import Callable

import numpy as np
from pydantic import BaseModel

from cohezion.flume.vae_encoder import get_encoder
from cohezion.platform.coherence_tracker import CoherenceMetrics, get_coherence_tracker
from cohezion.platform.journey_logger import get_journey_logger


class ActionProposal(BaseModel):
    """Proposed action with full transparency."""

    action_id: str
    action_type: str
    description: str
    rationale: str
    confidence: float
    coherence_impact: float  # Expected change to system coherence
    flume_state: list[float]  # Current 256D latent state
    risks: list[str]
    benefits: list[str]
    reversible: bool
    auto_approvable: bool  # Can auto-approve if confidence > threshold


class ObservableActionProposer:
    """Propose actions with full transparency before execution."""

    def __init__(self):
        self.coherence_tracker = get_coherence_tracker()
        self.journey_logger = get_journey_logger()
        self.vae = get_encoder()
        self._current_journey_id: str | None = None

    async def propose_action(
        self,
        action_type: str,
        description: str,
        rationale: str,
        confidence: float,
        action_fn: Callable,
        risks: list[str] | None = None,
        benefits: list[str] | None = None,
        reversible: bool = True,
        approval_callback: Callable[[ActionProposal], bool] | None = None,
    ) -> bool:
        """
        Propose an action with full transparency.

        Charter Compliance:
        - Exposes reasoning BEFORE action
        - Shows confidence and coherence impact
        - Displays FLUME state
        - Requires approval if confidence < threshold

        Args:
            action_type: Type of action (e.g., 'update', 'delete', 'refactor')
            description: What the action does
            rationale: Why we're doing it
            confidence: Agent confidence (0-1)
            action_fn: The action to execute if approved
            risks: List of identified risks
            benefits: List of expected benefits
            reversible: Whether the action can be undone
            approval_callback: Optional callback for approval (defaults to print + input)

        Returns:
            True if action was approved and executed, False otherwise
        """

        # Measure current coherence
        current_coherence = await self.coherence_tracker.measure_system_coherence()

        # Encode current state in FLUME space
        context = f"{action_type}: {description}\nRationale: {rationale}"
        flume_state = self.vae.encode(context)

        # Convert numpy array to list for JSON serialization
        if isinstance(flume_state, np.ndarray):
            flume_state = flume_state.tolist()

        # Estimate coherence impact
        coherence_impact = await self._estimate_coherence_impact(
            action_type, description, current_coherence.coherence
        )

        # Create proposal
        proposal = ActionProposal(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            description=description,
            rationale=rationale,
            confidence=confidence,
            coherence_impact=coherence_impact,
            flume_state=flume_state,
            risks=risks or [],
            benefits=benefits or [],
            reversible=reversible,
            auto_approvable=(
                confidence > 0.9 and reversible and abs(coherence_impact) < 0.1
            ),  # Small impact
        )

        # Display proposal (Observable AI)
        await self._display_proposal(proposal, current_coherence)

        # Auto-approve or request approval
        if proposal.auto_approvable:
            print(f"✅ AUTO-APPROVED (confidence {confidence:.2f} > 0.9)")
            approved = True
        else:
            if approval_callback:
                approved = approval_callback(proposal)
            else:
                approved = await self._request_approval(proposal)

        if approved:
            # Log decision to current journey (if one exists)
            if self._current_journey_id:
                try:
                    await self.journey_logger.log_decision(
                        journey_id=self._current_journey_id,
                        decision=description,
                        rationale=rationale,
                    )
                except Exception:
                    # Non-blocking if journey doesn't exist
                    pass

            # Execute action
            await action_fn()

            return True
        else:
            print("❌ Action rejected")
            return False

    async def _display_proposal(
        self,
        proposal: ActionProposal,
        current_coherence: CoherenceMetrics,
    ):
        """Display proposal with full transparency."""
        hiho_status = "HIHO Stable ✅" if current_coherence.hiho_stable else "Outside HIHO ⚠️"
        reversible = "Yes" if proposal.reversible else "No"
        new_coh = current_coherence.coherence + proposal.coherence_impact
        risks = (
            chr(10).join("- " + r for r in proposal.risks)
            if proposal.risks
            else "- None identified"
        )
        benefits = (
            chr(10).join("- " + b for b in proposal.benefits)
            if proposal.benefits
            else "- None specified"
        )
        decision = (
            "AUTO-APPROVABLE (high confidence, reversible, low impact)"
            if proposal.auto_approvable
            else "REQUIRES APPROVAL (low confidence or high impact)"
        )

        print(
            f"""
{"=" * 70}
OBSERVABLE AI: ACTION PROPOSAL
{"=" * 70}

Action Type: {proposal.action_type}
Description: {proposal.description}

REASONING:
{proposal.rationale}

METRICS:
- Confidence: {proposal.confidence:.2%}
- Current Coherence: {current_coherence.coherence:.3f} ({hiho_status})
- Expected Coherence Impact: {proposal.coherence_impact:+.3f}
- New Coherence: ~{new_coh:.3f}
- Reversible: {reversible}

FLUME STATE (256D):
{proposal.flume_state[:5]}... (showing first 5 dimensions)

RISKS:
{risks}

BENEFITS:
{benefits}

DECISION:
{decision}

{"=" * 70}
"""
        )

    async def _request_approval(self, proposal: ActionProposal) -> bool:
        """Request human approval for action."""
        # In production, this would integrate with UI/CLI approval system
        # For testing, we can provide a callback or simulate
        try:
            response = input("Approve this action? (yes/no): ").strip().lower()
            return response in ["yes", "y"]
        except EOFError:
            # Non-interactive environment (e.g., tests)
            return False

    async def _estimate_coherence_impact(
        self, action_type: str, description: str, current_coherence: float
    ) -> float:
        """Estimate impact on system coherence."""

        # Simplified heuristic
        # In production, would use ML model or historical data

        description_lower = description.lower()

        if "update" in description_lower or "patch" in description_lower:
            return 0.01  # Small positive impact
        elif "refactor" in description_lower:
            return 0.05  # Moderate positive impact
        elif "delete" in description_lower:
            return -0.02  # Small negative impact
        else:
            return 0.0  # Neutral

    def set_current_journey(self, journey_id: str):
        """Set the current journey ID for logging decisions."""
        self._current_journey_id = journey_id

    def get_current_journey_id(self) -> str | None:
        """Get current journey ID."""
        return self._current_journey_id


# Singleton accessor
_observable_proposer = None


def get_observable_proposer() -> ObservableActionProposer:
    """Get global observable proposer instance."""
    global _observable_proposer
    if _observable_proposer is None:
        _observable_proposer = ObservableActionProposer()
    return _observable_proposer


def reset_observable_proposer():
    """Reset global observable proposer (for testing)."""
    global _observable_proposer
    _observable_proposer = None
