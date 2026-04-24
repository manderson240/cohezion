"""QuadratureNexus - Central orchestrator for 4-voice consensus governance.

The Quadrature Nexus is the consensus mechanism of the Swarm. It prevents
hallucinated, dangerous, or inefficient actions by forcing every major decision
through 4 opposing perspectives:

1. Architect: "What is beautiful and structurally sound?" (Gemini)
2. Engineer: "What is efficient and possible?" (DeepSeek/Qwen)
3. Ethicist: "What is safe and aligned?" (Claude/Llama)
4. Resource: "What can we afford?" (ResourceMonitor)

Action is only taken when Alignment > 0.85.

Architecture:
    QuadratureNexus
        ├── propose(action) → QuadratureProposal
        ├── debate(proposal) → QuadratureResult
        ├── vote(result) → ConsensusScore
        └── ratify(score) → StrategicDirective or Rejection

References:
    - Smith's HIHO: consensus at 0.5 coherence (balanced perspectives)
    - Percival's Triune Self: Architect(Knower), Engineer(Thinker), Ethicist(Douer)
    - Noether's theorem: consensus symmetry → action conservation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class VoiceType(Enum):
    """The 4 voices of the Quadrature Nexus."""

    ARCHITECT = "architect"  # Beauty, structure, elegance
    ENGINEER = "engineer"  # Efficiency, feasibility, implementation
    ETHICIST = "ethicist"  # Safety, alignment, ethics
    RESOURCE = "resource"  # Cost, budget, constraints


@dataclass
class QuadratureProposal:
    """A proposal submitted to the Quadrature Nexus for debate."""

    action: str
    description: str
    context: dict[str, Any]
    submitted_by: str
    timestamp: float = field(default_factory=datetime.now().timestamp)
    priority: float = 0.5  # HIHO default: balanced urgency


@dataclass
class VoiceResponse:
    """Response from a single voice in the Quadrature debate."""

    voice: VoiceType
    approval_score: float  # 0.0-1.0, how much this voice approves
    concerns: list[str]
    recommendations: list[str]
    reasoning: str
    confidence: float


@dataclass
class QuadratureResult:
    """Result of a complete Quadrature Nexus deliberation."""

    proposal: QuadratureProposal
    responses: list[VoiceResponse]
    consensus_score: float  # Weighted average of all voices
    alignment_score: float  # How aligned voices are with each other
    approved: bool  # True if consensus > 0.85
    directive: str | None  # Approved action directive
    rejection_reason: str | None  # Why rejected if not approved
    timestamp: float = field(default_factory=datetime.now().timestamp)


@dataclass
class StrategicDirective:
    """An approved strategic directive from the Quadrature Nexus."""

    directive_id: str
    action: str
    description: str
    consensus_score: float
    approved_at: datetime
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class QuadratureNexus:
    """Central orchestrator for 4-voice consensus governance.

    The Nexus ensures that all major decisions pass through quadrature
    assessment - 4 perpendicular perspectives that prevent hallucination,
    danger, inefficiency, and resource waste.

    The consensus mechanism implements Smith's HIHO principle:
    - Maximum reality precipitation at 0.5 coherence (balanced perspectives)
    - Action requires > 0.85 consensus (strong alignment across all voices)
    - Dissent is recorded and weighted (minority concerns preserved)

    Example:
        ```python
        nexus = QuadratureNexus()

        proposal = QuadratureProposal(
            action="refactor_database_layer",
            description="Migrate from SQLite to SurrealDB",
            context={"current_load": "high", "team_size": 5},
            submitted_by="architect_agent",
        )

        result = await nexus.deliberate(proposal)

        if result.approved:
            directive = nexus.ratify(result)
            execute(directive)
        else:
            logger.warning(f"Rejected: {result.rejection_reason}")
        ```
    """

    # Consensus threshold for approval (HIHO band: 0.85 = strong alignment)
    CONSENSUS_THRESHOLD: float = 0.85

    # Voice weights (can be adjusted based on context). QuadratureNexus is not a
    # dataclass, so DEFAULT_WEIGHTS is a plain class-level dict.
    DEFAULT_WEIGHTS: dict[VoiceType, float] = {
        VoiceType.ARCHITECT: 0.25,
        VoiceType.ENGINEER: 0.25,
        VoiceType.ETHICIST: 0.25,
        VoiceType.RESOURCE: 0.25,
    }

    def __init__(
        self,
        weights: dict[VoiceType, float] | None = None,
        universe_id: str | None = None,
    ):
        """Initialize Quadrature Nexus.

        Args:
            weights: Optional custom voice weights. Defaults to equal weighting.
            universe_id: Optional universe this nexus operates within. Used when
                emitting CONSENSUS_RATIFIED precipitation events.
        """
        self._weights = weights or dict(self.DEFAULT_WEIGHTS)
        self._directives: list[StrategicDirective] = []
        self._deliberation_history: list[QuadratureResult] = []
        self.universe_id = universe_id or "uncontained"

    async def deliberate(self, proposal: QuadratureProposal) -> QuadratureResult:
        """Deliberate on a proposal through all 4 voices.

        Args:
            proposal: Proposal to deliberate on

        Returns:
            QuadratureResult with consensus score, approval status, directive
        """
        logger.info("Starting Quadrature deliberation on: %s", proposal.action)

        # Phase 1: Collect responses from all voices
        responses = await self._collect_voice_responses(proposal)

        # Phase 2: Compute consensus score
        consensus_score = self._compute_consensus_score(responses)

        # Phase 3: Compute alignment score (how much voices agree)
        alignment_score = self._compute_alignment_score(responses)

        # Phase 4: Determine approval
        approved = consensus_score >= self.CONSENSUS_THRESHOLD

        # Phase 5: Generate directive or rejection reason
        if approved:
            directive = self._generate_directive(proposal, consensus_score)
            rejection_reason = None
        else:
            directive = None
            rejection_reason = self._generate_rejection_reason(responses, consensus_score)

        result = QuadratureResult(
            proposal=proposal,
            responses=responses,
            consensus_score=consensus_score,
            alignment_score=alignment_score,
            approved=approved,
            directive=directive,
            rejection_reason=rejection_reason,
        )

        self._deliberation_history.append(result)
        logger.info(
            "Quadrature deliberation complete: approved=%s, consensus=%.3f",
            approved,
            consensus_score,
        )

        return result

    async def _collect_voice_responses(
        self,
        proposal: QuadratureProposal,
    ) -> list[VoiceResponse]:
        """Collect responses from all 4 voices.

        In production, this would call actual LLM agents for each voice.
        For now, returns simulated responses based on proposal context.

        Args:
            proposal: Proposal to evaluate

        Returns:
            List of VoiceResponse from all 4 voices
        """
        responses: list[VoiceResponse] = []

        # ARCHITECT: Focus on beauty, structure, elegance
        architect_response = VoiceResponse(
            voice=VoiceType.ARCHITECT,
            approval_score=self._evaluate_architect(proposal),
            concerns=self._architect_concerns(proposal),
            recommendations=self._architect_recommendations(proposal),
            reasoning=self._architect_reasoning(proposal),
            confidence=0.8,
        )
        responses.append(architect_response)

        # ENGINEER: Focus on efficiency, feasibility, implementation
        engineer_response = VoiceResponse(
            voice=VoiceType.ENGINEER,
            approval_score=self._evaluate_engineer(proposal),
            concerns=self._engineer_concerns(proposal),
            recommendations=self._engineer_recommendations(proposal),
            reasoning=self._engineer_reasoning(proposal),
            confidence=0.85,
        )
        responses.append(engineer_response)

        # ETHICIST: Focus on safety, alignment, ethics
        ethicist_response = VoiceResponse(
            voice=VoiceType.ETHICIST,
            approval_score=self._evaluate_ethicist(proposal),
            concerns=self._ethicist_concerns(proposal),
            recommendations=self._ethicist_recommendations(proposal),
            reasoning=self._ethicist_reasoning(proposal),
            confidence=0.9,
        )
        responses.append(ethicist_response)

        # RESOURCE: Focus on cost, budget, constraints
        resource_response = VoiceResponse(
            voice=VoiceType.RESOURCE,
            approval_score=self._evaluate_resource(proposal),
            concerns=self._resource_concerns(proposal),
            recommendations=self._resource_recommendations(proposal),
            reasoning=self._resource_reasoning(proposal),
            confidence=0.75,
        )
        responses.append(resource_response)

        return responses

    def _evaluate_architect(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Architect perspective."""
        # Architects value structure, elegance, beauty
        base_score = 0.7
        if "architecture" in proposal.description.lower():
            base_score += 0.1
        if proposal.priority > 0.6:
            base_score += 0.1
        return min(1.0, base_score)

    def _evaluate_engineer(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Engineer perspective."""
        # Engineers value feasibility, efficiency, implementation
        base_score = 0.75
        if (
            "efficient" in proposal.description.lower()
            or "optimize" in proposal.description.lower()
        ):
            base_score += 0.1
        return min(1.0, base_score)

    def _evaluate_ethicist(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Ethicist perspective."""
        # Ethicists value safety, alignment, ethics
        base_score = 0.8
        if "safe" in proposal.description.lower() or "align" in proposal.description.lower():
            base_score += 0.1
        return min(1.0, base_score)

    def _evaluate_resource(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Resource perspective."""
        # Resources value cost, budget, constraints
        base_score = 0.65
        if proposal.context.get("budget_available", False):
            base_score += 0.15
        return min(1.0, base_score)

    def _architect_concerns(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Architect concerns."""
        concerns = []
        if "refactor" in proposal.action:
            concerns.append("Ensure structural integrity is maintained")
        return concerns

    def _architect_recommendations(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Architect recommendations."""
        return ["Maintain elegance", "Document architectural decisions"]

    def _architect_reasoning(self, proposal: QuadratureProposal) -> str:
        """Generate Architect reasoning."""
        return "Architecture must balance beauty with maintainability"

    def _engineer_concerns(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Engineer concerns."""
        concerns = []
        if "migrate" in proposal.action:
            concerns.append("Ensure backward compatibility")
        return concerns

    def _engineer_recommendations(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Engineer recommendations."""
        return ["Profile performance", "Add integration tests"]

    def _engineer_reasoning(self, proposal: QuadratureProposal) -> str:
        """Generate Engineer reasoning."""
        return "Implementation must be efficient and maintainable"

    def _ethicist_concerns(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Ethicist concerns."""
        concerns = []
        if "user" in proposal.context:
            concerns.append("Ensure user privacy is protected")
        return concerns

    def _ethicist_recommendations(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Ethicist recommendations."""
        return ["Add safety guardrails", "Document ethical considerations"]

    def _ethicist_reasoning(self, proposal: QuadratureProposal) -> str:
        """Generate Ethicist reasoning."""
        return "Safety and alignment must be prioritized"

    def _resource_concerns(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Resource concerns."""
        concerns = []
        if proposal.context.get("budget_available", False):
            concerns.append("Monitor budget consumption")
        else:
            concerns.append("Secure budget before proceeding")
        return concerns

    def _resource_recommendations(self, proposal: QuadratureProposal) -> list[str]:
        """Generate Resource recommendations."""
        return ["Track resource usage", "Set budget alerts"]

    def _resource_reasoning(self, proposal: QuadratureProposal) -> str:
        """Generate Resource reasoning."""
        return "Resources must be allocated efficiently"

    def _compute_consensus_score(self, responses: list[VoiceResponse]) -> float:
        """Compute weighted consensus score from all voice responses.

        Args:
            responses: List of VoiceResponse from all 4 voices

        Returns:
            Weighted average approval score (0.0-1.0)
        """
        total = 0.0
        for response in responses:
            weight = self._weights.get(response.voice, 0.25)
            total += weight * response.approval_score
        return total

    def _compute_alignment_score(self, responses: list[VoiceResponse]) -> float:
        """Compute alignment score (how much voices agree with each other).

        Uses variance of approval scores - low variance = high alignment.

        Args:
            responses: List of VoiceResponse from all 4 voices

        Returns:
            Alignment score (0.0-1.0, higher = more aligned)
        """
        scores = [r.approval_score for r in responses]
        variance = float(np.var(scores))
        # Low variance = high alignment
        alignment = 1.0 - min(variance * 4.0, 1.0)
        return alignment

    def _generate_directive(
        self,
        proposal: QuadratureProposal,
        consensus_score: float,
    ) -> str:
        """Generate approved directive string.

        Args:
            proposal: Original proposal
            consensus_score: Final consensus score

        Returns:
            Directive action string
        """
        return f"APPROVED: {proposal.action} (consensus={consensus_score:.3f})"

    def _generate_rejection_reason(
        self,
        responses: list[VoiceResponse],
        consensus_score: float,
    ) -> str:
        """Generate rejection reason string.

        Args:
            responses: All voice responses
            consensus_score: Final consensus score

        Returns:
            Rejection reason string
        """
        # Find the most concerned voice
        min_response = min(responses, key=lambda r: r.approval_score)
        concerns = "; ".join(min_response.concerns[:2])
        return (
            f"Rejected (consensus={consensus_score:.3f} < {self.CONSENSUS_THRESHOLD}): "
            f"{min_response.voice.value} raised concerns: {concerns}"
        )

    def ratify(
        self, result: QuadratureResult, expires_hours: float | None = None
    ) -> StrategicDirective:
        """Ratify an approved QuadratureResult into a StrategicDirective.

        Args:
            result: Approved QuadratureResult
            expires_hours: Optional expiration time in hours

        Returns:
            StrategicDirective for execution

        Raises:
            ValueError: If result was not approved
        """
        if not result.approved:
            raise ValueError(f"Cannot ratify unapproved result: {result.rejection_reason}")

        directive = StrategicDirective(
            directive_id=f"directive_{int(datetime.now().timestamp())}",
            action=result.proposal.action,
            description=result.proposal.description,
            consensus_score=result.consensus_score,
            approved_at=datetime.now(),
            expires_at=datetime.now() if expires_hours else None,
            metadata={
                "proposal": result.proposal,
                "alignment_score": result.alignment_score,
                "voice_responses": [r.voice.value for r in result.responses],
            },
        )

        self._directives.append(directive)
        logger.info("Ratified directive: %s", directive.directive_id)

        # Precipitation emission — ratified consensus is a witness mark
        _emit_consensus_ratified(self.universe_id, result, directive)

        return directive

    def get_directives(self) -> list[StrategicDirective]:
        """Get all ratified directives."""
        return list(self._directives)

    def get_history(self) -> list[QuadratureResult]:
        """Get all deliberation history."""
        return list(self._deliberation_history)

    def get_consensus_statistics(self) -> dict[str, float]:
        """Compute consensus statistics from deliberation history.

        Returns:
            Dict with mean_consensus, std_consensus, approval_rate, mean_alignment
        """
        if not self._deliberation_history:
            return {
                "mean_consensus": 0.0,
                "std_consensus": 0.0,
                "approval_rate": 0.0,
                "mean_alignment": 0.0,
            }

        consensus_scores = [r.consensus_score for r in self._deliberation_history]
        alignment_scores = [r.alignment_score for r in self._deliberation_history]
        approved_count = sum(1 for r in self._deliberation_history if r.approved)

        return {
            "mean_consensus": float(np.mean(consensus_scores)),
            "std_consensus": float(np.std(consensus_scores)),
            "approval_rate": approved_count / len(self._deliberation_history),
            "mean_alignment": float(np.mean(alignment_scores)),
        }


def _emit_consensus_ratified(
    universe_id: str,
    result: QuadratureResult,
    directive: StrategicDirective,
) -> None:
    """Emit a CONSENSUS_RATIFIED precipitation event. Best-effort."""
    try:
        from cohezion.precipitation import (
            PrecipitationEvent,
            PrecipitationKind,
            emit,
        )

        emit(
            PrecipitationEvent(
                kind=PrecipitationKind.CONSENSUS_RATIFIED,
                universe_id=universe_id,
                coherence=max(0.0, min(1.0, result.consensus_score)),
                payload={
                    "directive_id": directive.directive_id,
                    "action": result.proposal.action,
                    "description": result.proposal.description,
                    "consensus_score": result.consensus_score,
                    "alignment_score": result.alignment_score,
                    "voice_breakdown": {r.voice.value: r.approval_score for r in result.responses},
                    "submitted_by": result.proposal.submitted_by,
                },
            )
        )
    except Exception:
        logger.debug("Precipitation emit failed for consensus ratification", exc_info=True)
