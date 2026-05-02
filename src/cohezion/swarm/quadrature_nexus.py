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

    # Voice weights (can be adjusted based on context)
    DEFAULT_WEIGHTS: dict[VoiceType, float] = {
        VoiceType.ARCHITECT: 0.25,
        VoiceType.ENGINEER: 0.25,
        VoiceType.ETHICIST: 0.25,
        VoiceType.RESOURCE: 0.25,
    }

    def __init__(self, weights: dict[VoiceType, float] | None = None):
        """Initialize Quadrature Nexus.

        Args:
            weights: Optional custom voice weights. Defaults to equal weighting.
        """
        self._weights = weights or dict(self.DEFAULT_WEIGHTS)
        self._directives: list[StrategicDirective] = []
        self._deliberation_history: list[QuadratureResult] = []
        # E2: EVO lifecycle — one EVO per action type, reused across deliberations
        self._evo_registry: dict[str, Any] = {}  # action_key → ExoticVacuumObject
        # E5/E6: Mycelium feedback — tracks alignment/consensus before/after injection
        self._baseline_alignments: list[float] = []
        self._post_mycelium_alignments: list[float] = []
        self._baseline_consensus: list[float] = []
        self._post_mycelium_consensus: list[float] = []
        self._mycelium_applied = False
        # E6: score adjustments — Mycelium writes per-voice corrections here
        self._score_adjustments: dict[VoiceType, float] = dict.fromkeys(VoiceType, 0.0)

    def apply_mycelium_feedback(
        self, synthesized_skill_content: str, learning_rate: float = 0.5
    ) -> dict:
        """Apply Mycelium-synthesized patterns as per-voice score adjustments (E6/E8).

        Reads per-voice mean scores from the synthesized skill content.
        For each voice scoring below the consensus target, applies a positive
        score adjustment to lift consensus toward the HIHO threshold.

        Args:
            synthesized_skill_content: Skill content from MyceliumRegistry.
            learning_rate: Fraction of gap-to-target to apply as adjustment (E8 sweep).

        This is Path A (state injection): `_score_adjustments[voice]` is added
        to the base score in each `_evaluate_*` method, closing the feedback loop.

        Returns a dict describing the adjustments applied.
        """
        import re

        # Voice heuristic baselines (from _evaluate_* methods)
        baselines = {
            "architect": 0.7,
            "engineer": 0.75,
            "ethicist": 0.8,
            "resource": 0.65,
        }
        voice_type_map = {
            "architect": VoiceType.ARCHITECT,
            "engineer": VoiceType.ENGINEER,
            "ethicist": VoiceType.ETHICIST,
            "resource": VoiceType.RESOURCE,
        }

        # Parse mean consensus from synthesized content
        cons_m = re.search(r"consensus=(\d+\.\d+)", synthesized_skill_content)
        mean_consensus = float(cons_m.group(1)) if cons_m else 0.5

        # Parse per-voice mean scores from synthesized skill
        # E6/E8 rule: ONLY apply positive adjustments — never penalize high-scoring voices.
        # Goal: lift the floor so consensus rises toward CONSENSUS_THRESHOLD (0.85).
        adjustments_applied = {}
        consensus_gap = max(0.0, self.CONSENSUS_THRESHOLD - mean_consensus)
        for voice_name, baseline in baselines.items():
            pattern = rf"{voice_name}: mean_score=(\d+\.\d+)"
            m = re.search(pattern, synthesized_skill_content)
            if m:
                observed_mean = float(m.group(1))
                # Target = observed + proportional share of consensus gap
                target = min(1.0, observed_mean + consensus_gap * 0.5)
                gap_to_target = target - observed_mean
                # Boost = learning_rate × gap, always positive, capped at 0.15
                adjustment = max(0.0, min(0.15, gap_to_target * learning_rate))
                vt = voice_type_map[voice_name]
                self._score_adjustments[vt] = adjustment
                adjustments_applied[voice_name] = {
                    "baseline": baseline,
                    "observed": observed_mean,
                    "target": round(target, 4),
                    "adjustment": round(adjustment, 5),
                }

        self._mycelium_applied = True
        logger.info("Mycelium E6 score adjustments: %s", adjustments_applied)
        return {
            "adjustments": adjustments_applied,
            "mechanism": "score_injection",
        }

    def get_alignment_trend(self) -> dict:
        """Return alignment and consensus scores before/after Mycelium feedback (E5)."""
        b_align = self._baseline_alignments
        p_align = self._post_mycelium_alignments
        b_cons = self._baseline_consensus
        p_cons = self._post_mycelium_consensus

        def safe_mean(lst: list[float]) -> float:
            return sum(lst) / len(lst) if lst else 0.0

        align_delta = safe_mean(p_align) - safe_mean(b_align) if b_align and p_align else 0.0
        cons_delta = safe_mean(p_cons) - safe_mean(b_cons) if b_cons and p_cons else 0.0
        return {
            "baseline_count": len(b_align),
            "baseline_alignment_mean": safe_mean(b_align),
            "baseline_consensus_mean": safe_mean(b_cons),
            "post_mycelium_count": len(p_align),
            "post_mycelium_alignment_mean": safe_mean(p_align),
            "post_mycelium_consensus_mean": safe_mean(p_cons),
            "alignment_delta": align_delta,
            "consensus_delta": cons_delta,
        }

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

        # E5: Track alignment and consensus for closed-loop measurement
        if self._mycelium_applied:
            self._post_mycelium_alignments.append(alignment_score)
            self._post_mycelium_consensus.append(consensus_score)
        else:
            self._baseline_alignments.append(alignment_score)
            self._baseline_consensus.append(consensus_score)

        # --- E2: EVO LIFECYCLE TRACKING ---
        evo_biography: dict | None = None
        try:
            from cohezion.physics.evo_model import ExoticVacuumObject

            # Get or create EVO for this action type
            evo = self._evo_registry.get(proposal.action)
            if evo is None or evo.state == "vacuum":
                evo = ExoticVacuumObject(agent_id=f"nexus_{proposal.action[:24]}")
                self._evo_registry[proposal.action] = evo

            # Lifecycle: condense (vacuum → coherent)
            if evo.state == "vacuum":
                evo.condense()

            # Tick coherence once per voice response
            for r in responses:
                evo.coherent_phase(coherence=r.approval_score)

            # Produce a witness mark for each deliberation outcome
            mark_type = "directive" if approved else "rejection"
            mark_content = directive or rejection_reason or "deliberation_complete"
            evo.produce_witness_mark(mark_type, mark_content[:120])

            # Dissolve and capture biography, then reset for next deliberation
            evo_biography = evo.dissolve()
            logger.debug(
                "EVO biography: agent=%s evo_coherence=%.3f lifetime=%d marks=%d",
                evo_biography["agent_id"],
                evo_biography["evo_coherence_metric"],
                evo_biography["lifetime_ticks"],
                len(evo_biography["witness_marks"]),
            )
        except Exception as evo_err:
            logger.debug("EVO lifecycle tracking skipped: %s", evo_err)

        # --- JOURNEY TELEMETRY INSTRUMENTATION (E1: real FLUME encoding) ---
        try:
            from cohezion.core.telemetry_bus import get_telemetry_bus
            from cohezion.data_mesh.journey_telemetry import (
                FlumeJourneyEvent,
                HardwareTier,
                QuadratureFabrics,
                RZeroMetrics,
                SwarmExpert,
            )
            from cohezion.flume.experience_encoder import ExperienceEncoder

            # Build deliberation experience for FLUME encoding.
            # Dims [0:12] = trajectory (voice scores projected to 12D),
            # [12:24] = execution metrics (consensus, alignment, etc.)
            voice_scores = {r.voice.value: r.approval_score for r in responses}
            deliberation_experience = {
                # 12D trajectory: 4 voice scores + 8 context scalars
                "trajectory": [
                    voice_scores.get("architect", 0.5),
                    voice_scores.get("engineer", 0.5),
                    voice_scores.get("ethicist", 0.5),
                    voice_scores.get("resource", 0.5),
                    consensus_score,
                    alignment_score,
                    float(approved),
                    proposal.priority,
                    # 4 context signals derived from proposal
                    min(len(proposal.description) / 500.0, 1.0),
                    min(len(proposal.context) / 10.0, 1.0),
                    float("migrate" in proposal.action or "refactor" in proposal.action),
                    float(proposal.priority > 0.6),
                ],
                # Scalar execution metrics (dims [12:24])
                "phi_score": consensus_score,
                "anomaly_score": 1.0 - alignment_score,
                "misalignment_score": abs(consensus_score - 0.5),
                "intent_confidence": alignment_score,
                "duration_s": 0.0,
                "tokens_used": 0,
                "cache_hit_rate": 0.0,
                "success": float(approved),
                "token_efficiency": consensus_score,
                "trajectory_smoothness": alignment_score,
                "trajectory_convergence": consensus_score,
                "cost_usd": 0.0,
                # Semantic fingerprint seed
                "operation_type": "analyze",
            }
            encoder = ExperienceEncoder()
            z_arr = encoder.encode(deliberation_experience)
            z_vector = z_arr.tolist()  # 256D real encoding
            state_12d = z_arr[:12].tolist()  # first 12 dims = trajectory

            # Map 4 voices to 4 QuadratureFabrics fields
            fabrics = QuadratureFabrics(
                space=voice_scores.get("architect", 0.5),  # geometric structure
                field=voice_scores.get("engineer", 0.5),  # energy/efficiency
                control=1.0 - voice_scores.get("ethicist", 0.5),  # safety overhead
                precipitation=voice_scores.get("resource", 0.5),  # value generation
            )

            bus = get_telemetry_bus()
            event = FlumeJourneyEvent(
                event_id=f"evt_{int(datetime.now().timestamp())}_{proposal.action[:10]}",
                journey_id=proposal.action,
                z_vector=z_vector,
                state_12d=state_12d,
                coherence=alignment_score,
                fabrics=fabrics,
                awareness_parameter=consensus_score,
                expert_stream=SwarmExpert.ARCHITECT,
                hardware_tier=HardwareTier.IGPU,
                latency_ms=0.0,
                r_zero=RZeroMetrics(
                    success_rate=consensus_score,
                    iteration_count=len(responses),
                    difficulty_adjustment=1.0 - alignment_score,
                ),
                # E2+E6: embed EVO biography + per-voice scores for Mycelium learning
                metadata={
                    **({"evo_biography": evo_biography} if evo_biography else {}),
                    "voice_scores": voice_scores,  # per-voice approval scores for E6
                    "consensus_score": consensus_score,
                    "approved": approved,
                },
            )
            await bus.emit(event)
        except Exception as te:
            logger.error("Failed to emit journey telemetry: %s", te)

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
        base_score = 0.7
        if "architecture" in proposal.description.lower():
            base_score += 0.1
        if proposal.priority > 0.6:
            base_score += 0.1
        # E6: apply Mycelium score adjustment (clamped to keep score in [0, 1])
        return min(1.0, max(0.0, base_score + self._score_adjustments[VoiceType.ARCHITECT]))

    def _evaluate_engineer(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Engineer perspective."""
        base_score = 0.75
        if (
            "efficient" in proposal.description.lower()
            or "optimize" in proposal.description.lower()
        ):
            base_score += 0.1
        return min(1.0, max(0.0, base_score + self._score_adjustments[VoiceType.ENGINEER]))

    def _evaluate_ethicist(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Ethicist perspective."""
        base_score = 0.8
        if "safe" in proposal.description.lower() or "align" in proposal.description.lower():
            base_score += 0.1
        return min(1.0, max(0.0, base_score + self._score_adjustments[VoiceType.ETHICIST]))

    def _evaluate_resource(self, proposal: QuadratureProposal) -> float:
        """Evaluate proposal from Resource perspective."""
        base_score = 0.65
        if proposal.context.get("budget_available", False):
            base_score += 0.15
        desc_lower = proposal.description.lower()
        if any(kw in desc_lower for kw in ("cost", "budget", "efficient", "resource", "reduce")):
            base_score += 0.10
        return min(1.0, max(0.0, base_score + self._score_adjustments[VoiceType.RESOURCE]))

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
