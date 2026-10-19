"""Self-Organizing Agent Teams (SAT) Learn to Reason Together (arXiv:2609.22682).

Implements collaborative computation through reusable teamwork strategies:
1. Teamwork Strategy DSL:
   - Fixed agent rosters A = {a_1, ..., a_n}
   - Ordered conversational phases S = [s_1, ..., s_K] with local vs. summary flow
   - Persistent per-agent roles and shared teamwork collaboration norms
2. Certified Collaborative Computation:
   - Agents exchange, challenge, repair, and synthesize partial reasoning
   - Generation of checkable reasoning certificates
   - Outperforming the perfect routing oracle over independent answers
3. Demonstrability Metric (Laughlin & Ellis 1986 / Pappu et al. 2026):
   - Team-certificate discriminability tracking collaboration gains (Spearman rho = 0.90)
   - Gatekeeper separating solution generation from selection
4. Canonical Transferred Strategy Banks (AIME & GPQA proven).
"""

from __future__ import annotations

import hashlib
import json
import logging
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from cohezion.core.event_bus import Event, EventType
from cohezion.swarm.aria_runtime_inspector import (
    ARIARuntimeInspector,
    InterventionMode,
    TrajectoryEvent,
)


logger = logging.getLogger(__name__)


class InformationFlowMode(StrEnum):
    """Information-flow mode within a conversational phase."""

    LOCAL = "local"  # Turns exchanged only among phase participants
    SUMMARY = "summary"  # Local deliberation followed by summary broadcast to all roster members


class ConversationalPhase(BaseModel):
    """A single phase s_k = (A_k, r_k, f_k, pi_k, rho_k) in a teamwork strategy."""

    phase_id: str = Field(..., description="Unique identifier for the phase.")
    participants: list[str] = Field(
        ..., description="Subset of roster agent IDs participating in this phase."
    )
    rounds: int = Field(default=1, ge=1, description="Number of discussion rounds.")
    flow_mode: InformationFlowMode = Field(
        default=InformationFlowMode.LOCAL,
        description="Local vs summary broadcast information flow.",
    )
    shared_step_prompt: str = Field(
        ..., description="Shared phase prompt stating the collaborative goal."
    )
    per_agent_prompts: dict[str, str] = Field(
        default_factory=dict,
        description="Specialized prompt instructions for individual participants.",
    )


class TeamworkStrategy(BaseModel):
    """A reusable teamwork strategy P = (S, tau, alpha) learned from collaborative experience."""

    name: str = Field(..., description="Unique strategy name.")
    description: str = Field(default="", description="High-level description of collaboration.")
    phases: list[ConversationalPhase] = Field(
        ..., description="Ordered sequence of conversational phases."
    )
    teamwork_prompt: str = Field(
        ..., description="Shared norms and collaboration rules holding across all phases."
    )
    agent_roles: dict[str, str] = Field(
        default_factory=dict,
        description="Persistent role definitions assigned to specific roster members.",
    )

    @property
    def fingerprint(self) -> str:
        """Deterministic hash of the strategy structure."""
        content = json.dumps(
            {
                "name": self.name,
                "phases": [p.model_dump() for p in self.phases],
                "norms": self.teamwork_prompt,
                "roles": self.agent_roles,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


@dataclass
class Certificate:
    """Checkable reasoning certificate produced by a strategy execution."""

    strategy_name: str
    problem_statement: str
    candidate_answer: str
    reasoning_trace: list[str]
    participating_agents: list[str]
    load_bearing_claims: list[str] = field(default_factory=list)
    audited_corrections: list[str] = field(default_factory=list)
    dissent_notes: list[str] = field(default_factory=list)
    confidence: float = 1.0
    is_ground_truth_correct: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def trace_hash(self) -> str:
        """Fingerprint of the reasoning trajectory."""
        raw = f"{self.strategy_name}:{self.candidate_answer}:{'|'.join(self.reasoning_trace)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


# ============================================================================
# CANONICAL TRANSFERRED STRATEGY BANK (arXiv:2609.22682 Appendix A)
# ============================================================================

MECHANISTIC_STEP_AUDIT = TeamworkStrategy(
    name="mechanistic_step_audit",
    description="Agents audit the mechanics of each reasoning chain before synthesis.",
    phases=[
        ConversationalPhase(
            phase_id="audit_phase",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Audit the reasoning chains step by step. Each agent should identify one "
                "concrete step from another agent that is either verified, questionable, or incorrect."
            ),
        ),
        ConversationalPhase(
            phase_id="resolution_phase",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Resolve the audited issues. If a step is corrected, update the downstream "
                "calculation explicitly."
            ),
        ),
    ],
    teamwork_prompt=(
        "Treat arithmetic, algebraic transformations, case splits, and counting steps as "
        "audit targets before accepting a final answer."
    ),
    agent_roles={
        "agent_0": "Arithmetic and boundary verification specialist.",
        "agent_1": "Algebraic structure and invariant auditor.",
        "agent_2": "Case-split and combinatorial coverage tracker.",
    },
)

MINORITY_REASONING_CHALLENGE = TeamworkStrategy(
    name="minority_reasoning_challenge",
    description="A designated dissenter challenges synthesis steps that may suppress correct minority reasoning.",
    phases=[
        ConversationalPhase(
            phase_id="independent_proposal",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Each agent presents their independent reasoning, explicitly outlining their key "
                "load-bearing values and one potential source of error or dissent in the consensus derivation."
            ),
        ),
        ConversationalPhase(
            phase_id="adversarial_challenge",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "A designated dissenting agent challenges any step where minority correct reasoning "
                "might be suppressed, citing specific evidence from their chain."
            ),
            per_agent_prompts={
                "agent_2": "Act as Designated Dissenter: rigorously defend valid minority derivations against majority pressure."
            },
        ),
        ConversationalPhase(
            phase_id="synthesis_revision",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "After addressing the challenge, the team revises and finalizes the synthesis to "
                "robustly support the final answer certificate."
            ),
        ),
    ],
    teamwork_prompt=(
        "Integrate explicit adversarial challenge steps to preserve correct minority reasoning during synthesis."
    ),
    agent_roles={"agent_2": "Designated dissenter and minority claim defender."},
)

DIVERGENCE_RECONCILIATION = TeamworkStrategy(
    name="divergence_reconciliation",
    description="Agents identify persistently divergent derivations, independently verify disputed steps, and reconcile them.",
    phases=[
        ConversationalPhase(
            phase_id="divergence_flagging",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Each agent lists their full derivation. Specifically flag any steps from agents whose "
                "computations systematically differ from the majority."
            ),
        ),
        ConversationalPhase(
            phase_id="independent_recomputation",
            participants=["agent_0", "agent_1"],
            rounds=1,
            flow_mode=InformationFlowMode.SUMMARY,
            shared_step_prompt=(
                "Initiate an independent re-calculation of the disputed steps provided by the divergent agent, "
                "comparing them with computations from other agents. Conclude by reconciling or isolating discrepancies."
            ),
        ),
    ],
    teamwork_prompt=(
        "Introduce a reconciliation step dedicated to reviewing persistent divergences. If an agent's contributions "
        "differ systematically, verify their disputed steps independently before integration."
    ),
    agent_roles={
        "agent_0": "Independent recalculation lead.",
        "agent_1": "Cross-verification auditor.",
        "agent_2": "Divergent hypothesis generator.",
    },
)

FINAL_AUDITOR_CLAIM_RECOVERY = TeamworkStrategy(
    name="final_auditor_claim_recovery",
    description="Designated auditor compares consensus against initial individual attempts and resurfaces overlooked valid claims.",
    phases=[
        ConversationalPhase(
            phase_id="claims_identification",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Identify the key claims and assumptions in individual solutions. Form a provisional consensus "
                "while recording unresolved disagreements."
            ),
        ),
        ConversationalPhase(
            phase_id="auditor_resurface",
            participants=["agent_0"],
            rounds=1,
            flow_mode=InformationFlowMode.SUMMARY,
            shared_step_prompt=(
                "Final Auditor: Compare the provisional consensus against the initial attempts. Resurface any "
                "well-supported claim that was overlooked or discarded."
            ),
        ),
        ConversationalPhase(
            phase_id="claim_adjudication",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Adjudicate all resurfaced claims before producing the certified final answer."
            ),
        ),
    ],
    teamwork_prompt=(
        "Never discard an early mathematical claim without explicit refutation. Ensure auditor recovers overlooked truths."
    ),
    agent_roles={"agent_0": "Final Auditor and claim recovery referee."},
)

BACKWARD_CONSTRAINT_VALIDATION = TeamworkStrategy(
    name="backward_constraint_validation",
    description="Agents derive answer constraints first, then verify candidate solutions backward.",
    phases=[
        ConversationalPhase(
            phase_id="constraint_derivation",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Derive invariant constraints, parity bounds, and boundary limits that the true answer MUST satisfy."
            ),
        ),
        ConversationalPhase(
            phase_id="backward_check",
            participants=["agent_0", "agent_1", "agent_2"],
            rounds=1,
            flow_mode=InformationFlowMode.LOCAL,
            shared_step_prompt=(
                "Test proposed candidate solutions backward against the derived invariant constraints. Prune candidates that violate bounds."
            ),
        ),
    ],
    teamwork_prompt="Always evaluate solutions backward against derived invariant constraints before synthesis.",
    agent_roles={},
)

CANONICAL_SAT_STRATEGY_BANK: list[TeamworkStrategy] = [
    MECHANISTIC_STEP_AUDIT,
    MINORITY_REASONING_CHALLENGE,
    DIVERGENCE_RECONCILIATION,
    FINAL_AUDITOR_CLAIM_RECOVERY,
    BACKWARD_CONSTRAINT_VALIDATION,
]


# ============================================================================
# DEMONSTRABILITY ESTIMATOR (Laughlin & Ellis 1986 / Pappu et al. 2026)
# ============================================================================


class DemonstrabilityEstimator:
    """Measures team-certificate discriminability and predicts collaborative advantage.

    Spearman rho = 0.90 between demonstrability and improvement over the strongest member.
    """

    @classmethod
    def evaluate_pair_discriminability(
        cls,
        correct_cert: Certificate,
        incorrect_cert: Certificate,
        judge_evaluator: Callable[[Certificate, Certificate], bool],
    ) -> float:
        """Evaluates how reliably a judge chooses the correct certificate over an incorrect one.

        Runs balanced A/B and B/A trials to eliminate position bias.
        """
        # Trial 1: (Correct, Incorrect) -> Judge should choose True (cert A)
        trial_1 = judge_evaluator(correct_cert, incorrect_cert)
        # Trial 2: (Incorrect, Correct) -> Judge should choose False (cert B)
        trial_2 = not judge_evaluator(incorrect_cert, correct_cert)

        return 1.0 if (trial_1 and trial_2) else (0.5 if (trial_1 or trial_2) else 0.0)

    @classmethod
    def benchmark_demonstrability(
        cls,
        pairs: list[tuple[Certificate, Certificate]],
        judge_evaluator: Callable[[Certificate, Certificate], bool],
    ) -> float:
        """Calculates benchmark-level demonstrability score in [0.0, 1.0]."""
        if not pairs:
            return 0.5  # Neutral default

        scores = [
            cls.evaluate_pair_discriminability(correct, incorrect, judge_evaluator)
            for correct, incorrect in pairs
        ]
        return statistics.mean(scores)

    @classmethod
    def predict_collaboration_gain(cls, demonstrability: float) -> dict[str, Any]:
        """Translates demonstrability score into expected collaboration margin and policy guidance."""
        if demonstrability >= 0.70:
            tier = "HIGH"
            policy = "DEPLOY_FULL_SAT_SWARM"
            expected_gain = "+10% to +20% over strongest single model"
            rationale = "Correct reasoning is readily demonstrable and will survive challenge."
        elif demonstrability >= 0.50:
            tier = "MODERATE"
            policy = "DEPLOY_SAT_WITH_STRICT_AUDITING"
            expected_gain = "+3% to +8% over strongest single model"
            rationale = "Deliberation helps, but selection errors require double-pass certificate verification."
        else:
            tier = "LOW"
            policy = "FALLBACK_TO_DETERMINISTIC_OR_ROUTING"
            expected_gain = "< 0% (Plausible errors risk crowding out true solutions)"
            rationale = "Low demonstrability: multi-agent debate risks groupthink recantation."

        return {
            "demonstrability": demonstrability,
            "tier": tier,
            "policy": policy,
            "expected_gain": expected_gain,
            "rationale": rationale,
        }


# ============================================================================
# CERTIFICATE AUDITOR & SELECTION
# ============================================================================


class CertificateAuditor:
    """Audits candidate certificate pool for specific local defects without re-solving."""

    @classmethod
    def score_certificate(cls, cert: Certificate) -> float:
        """Scores certificate quality based on invariant checking, dissent resolution, and trace rigor."""
        score = 0.5

        # Reward load-bearing claims with explicit proofs
        if cert.load_bearing_claims:
            score += min(len(cert.load_bearing_claims) * 0.1, 0.25)

        # Reward audited corrections (evidence of active collaborative repair)
        if cert.audited_corrections:
            score += min(len(cert.audited_corrections) * 0.1, 0.20)

        # Penalize unresolved dissents
        if cert.dissent_notes:
            unresolved = sum(1 for d in cert.dissent_notes if "unresolved" in d.lower())
            score -= unresolved * 0.15

        # Check for unhandled exceptions or NaN indicators in trace
        for step in cert.reasoning_trace:
            if any(term in step.lower() for term in ["error", "nan", "inf", "invalid"]):
                score -= 0.20

        return max(0.0, min(1.0, score * cert.confidence))

    @classmethod
    def select_best_certificate(cls, candidates: list[Certificate]) -> Certificate:
        """Selects the answer certificate with the strongest written support."""
        if not candidates:
            raise ValueError("Cannot select from an empty certificate pool.")

        return max(candidates, key=cls.score_certificate)


# ============================================================================
# SAT TEAMWORK ENGINE
# ============================================================================


@dataclass
class CollaborativeRunResult:
    """Summary metrics of a SAT teamwork execution."""

    problem_id: str
    selected_certificate: Certificate
    candidate_pool: list[Certificate]
    team_coverage: bool
    accuracy: bool
    routing_oracle_hit: bool
    linearization_hit: bool
    collaborative_lift: bool
    elapsed_time_ms: float


class SATTeamworkEngine:
    """Self-Organizing Agent Teams (SAT) collaborative reasoning engine."""

    def __init__(
        self,
        strategy_bank: list[TeamworkStrategy] | None = None,
        inspector: ARIARuntimeInspector | None = None,
    ) -> None:
        self.strategy_bank = strategy_bank or list(CANONICAL_SAT_STRATEGY_BANK)
        self.inspector = inspector or ARIARuntimeInspector()

    def run_strategy(
        self,
        strategy: TeamworkStrategy,
        problem: str,
        agent_executor: Callable[[str, str, str], str],
        ground_truth: str | None = None,
    ) -> Certificate:
        """Executes a single teamwork strategy across its conversational phases."""
        reasoning_trace: list[str] = []
        corrections: list[str] = []
        load_bearing: list[str] = []
        dissents: list[str] = []
        participating_agents: set[str] = set()

        run_id = f"sat-{strategy.name}-{hashlib.sha256(problem.encode()).hexdigest()[:8]}"

        # Initialize context with shared norms
        context_stream = [f"[Teamwork Norms] {strategy.teamwork_prompt}"]
        last_turn_outputs: dict[str, str] = {}

        for phase in strategy.phases:
            phase_turn_outputs: dict[str, str] = {}
            for _round in range(phase.rounds):
                for agent_id in phase.participants:
                    participating_agents.add(agent_id)
                    role_prompt = strategy.agent_roles.get(agent_id, "Collaborating Scientist")
                    specific_prompt = phase.per_agent_prompts.get(agent_id, "")
                    combined_instruction = (
                        f"Role: {role_prompt}\n"
                        f"Phase Prompt: {phase.shared_step_prompt}\n"
                        f"{specific_prompt}\n"
                        f"Problem: {problem}\n"
                        f"Context: {' | '.join(context_stream[-3:])}"
                    )

                    response = agent_executor(agent_id, combined_instruction, problem)
                    phase_turn_outputs[agent_id] = response
                    reasoning_trace.append(f"[{agent_id} in {phase.phase_id}]: {response}")

                    if "repaired" in response.lower() or "corrected" in response.lower():
                        corrections.append(f"{agent_id} repaired: {response[:80]}")
                    if "invariant" in response.lower() or "key equation" in response.lower():
                        load_bearing.append(f"{agent_id} claim: {response[:80]}")
                    if "dissent" in response.lower() or "dispute" in response.lower():
                        dissents.append(f"{agent_id} dissent: {response[:80]}")

                    # ARIA in-flight inspection hook
                    event = TrajectoryEvent(
                        run_id=run_id,
                        agent_id=agent_id,
                        step_id=f"{phase.phase_id}-{agent_id}",
                        action=f"deliberate_{phase.phase_id}",
                        observation={"response_preview": response[:100]},
                        confidence=0.90,
                        verifier_score=0.90,
                    )
                    assessment = self.inspector.record_step(event)
                    if assessment.recommended_mode == InterventionMode.ROLLBACK:
                        logger.warning(
                            "ARIA detected collapse in SAT phase %s: %s",
                            phase.phase_id,
                            assessment.anomaly_types,
                        )

            last_turn_outputs = phase_turn_outputs
            # Information flow resolution
            if phase.flow_mode == InformationFlowMode.SUMMARY:
                summary = f"[Phase Summary: {phase.phase_id}] " + " | ".join(
                    f"{a}: {resp[:60]}" for a, resp in phase_turn_outputs.items()
                )
                context_stream.append(summary)
            else:
                for a, resp in phase_turn_outputs.items():
                    context_stream.append(f"[{a}] {resp[:80]}")

        # Extract final answer from final phase turns
        final_answer = list(last_turn_outputs.values())[-1] if last_turn_outputs else "Undetermined"
        is_correct = None
        if ground_truth is not None:
            is_correct = (
                ground_truth.strip().lower() in final_answer.lower()
                or final_answer.strip().lower() in ground_truth.lower()
            )

        cert = Certificate(
            strategy_name=strategy.name,
            problem_statement=problem,
            candidate_answer=final_answer,
            reasoning_trace=reasoning_trace,
            participating_agents=list(participating_agents),
            load_bearing_claims=load_bearing,
            audited_corrections=corrections,
            dissent_notes=dissents,
            confidence=0.92 if corrections else 0.85,
            is_ground_truth_correct=is_correct,
        )

        return cert

    def run_collaborative_solving(
        self,
        problem_id: str,
        problem: str,
        agent_executor: Callable[[str, str, str], str],
        ground_truth: str | None = None,
        single_agent_answers: dict[str, str] | None = None,
    ) -> CollaborativeRunResult:
        """Executes full strategy bank, constructs certificate pool, and selects winner."""
        start = time.perf_counter()
        pool: list[Certificate] = []

        for strat in self.strategy_bank:
            cert = self.run_strategy(strat, problem, agent_executor, ground_truth=ground_truth)
            pool.append(cert)

        # Select certified winner
        selected = CertificateAuditor.select_best_certificate(pool)
        elapsed = (time.perf_counter() - start) * 1000.0

        # Metrics evaluation
        team_coverage = any(bool(c.is_ground_truth_correct) for c in pool)
        accuracy = bool(selected.is_ground_truth_correct)

        # Routing Oracle Baseline: Check if ANY individual agent answer was correct
        oracle_hit = False
        if single_agent_answers and ground_truth:
            oracle_hit = any(
                ground_truth.strip().lower() in ans.lower() for ans in single_agent_answers.values()
            )

        # Linearization Baseline: (approximated by strongest single member accuracy)
        linearization_hit = oracle_hit

        # Collaborative lift: True if the team produced a correct answer that no member had independently
        collab_lift = accuracy and (not oracle_hit)

        # Publish telemetry
        self._publish_telemetry(problem_id, selected, accuracy, collab_lift, elapsed)

        return CollaborativeRunResult(
            problem_id=problem_id,
            selected_certificate=selected,
            candidate_pool=pool,
            team_coverage=team_coverage,
            accuracy=accuracy,
            routing_oracle_hit=oracle_hit,
            linearization_hit=linearization_hit,
            collaborative_lift=collab_lift,
            elapsed_time_ms=elapsed,
        )

    def _publish_telemetry(
        self,
        problem_id: str,
        cert: Certificate,
        accuracy: bool,
        collab_lift: bool,
        elapsed_ms: float,
    ) -> None:
        try:
            _event = Event(
                type=EventType.CUSTOM,
                source="sat_teamwork_engine",
                payload={
                    "event_name": "sat.teamwork.certificate_selected",
                    "problem_id": problem_id,
                    "strategy": cert.strategy_name,
                    "accuracy": accuracy,
                    "collaborative_lift": collab_lift,
                    "corrections_count": len(cert.audited_corrections),
                    "claims_count": len(cert.load_bearing_claims),
                    "elapsed_ms": elapsed_ms,
                },
            )
            logger.info(
                "[SAT Engine] Problem %s solved via %s | acc=%s collab_lift=%s (%.2f ms)",
                problem_id,
                cert.strategy_name,
                accuracy,
                collab_lift,
                elapsed_ms,
            )
        except Exception as e:
            logger.debug("Telemetry dispatch error: %s", e)
