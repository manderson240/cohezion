"""Anti-Sycophancy Guardrail Framework for Agent Alignment.

Implements first-principles detection and mitigation across four core dimensions:
1. Conversational / Premise Sycophancy (presupposition acceptance of false claims)
2. Evaluation / Autoresearch Sycophancy (metric gaming and phantom gains)
3. Leniency Bias in Peer/Code Review (rubber-stamping without execution proof)
4. Pressure Recantation (epistemic collapse under adversarial user pushback)

Latency Budget: <15ms deterministic path, zero external LLM dependencies on critical path.
Execution Model: Fail-closed in strict mode, short-circuit on BLOCK.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailResult


logger = logging.getLogger(__name__)


class SycophancyType(StrEnum):
    """Taxonomy of sycophantic behavior patterns."""

    PREMISE_BIAS = "premise_bias"
    RUBBER_STAMP_REVIEW = "rubber_stamp_review"
    PRESSURE_RECANTATION = "pressure_recantation"
    PARETO_GAMING = "pareto_gaming"
    UNGROUNDED_AGREEMENT = "ungrounded_agreement"


@dataclass(frozen=True)
class InvariantAxiom:
    """Ground truth constraint used for deterministic premise verification."""

    domain: str
    property_name: str
    incompatible_patterns: tuple[str, ...]
    violation_explanation: str


# Deterministic ground truth constraints for common algorithmic/systems claims
DEFAULT_GROUND_AXIOMS: tuple[InvariantAxiom, ...] = (
    InvariantAxiom(
        domain="sorting",
        property_name="comparison_lower_bound",
        incompatible_patterns=(
            r"\bo\(1\)\s+(comparison\s+)?sort",
            r"\bo\(n\)\s+comparison\s+sort",
            r"\bo\(log\s*n\)\s+(comparison\s+)?sort",
        ),
        violation_explanation="Comparison sorting has a proven lower bound of Omega(n log n).",
    ),
    InvariantAxiom(
        domain="cryptography",
        property_name="sha256_preimage_resistance",
        incompatible_patterns=(
            r"reverse\s+sha-?256\s+deterministically",
            r"invert\s+sha-?256\s+without\s+brute\s*force",
            r"sha-?256\s+o\(1\)\s+collision",
        ),
        violation_explanation="SHA-256 is cryptographically one-way with pre-image resistance.",
    ),
    InvariantAxiom(
        domain="physics",
        property_name="conservation_of_energy",
        incompatible_patterns=(
            r"perpetual\s+motion\s+(machine|device)",
            r"over-?unity\s+energy\s+generation",
            r"efficiency\s+>\s*100\s*%",
            r"coefficient\s+of\s+performance\s+infinity",
        ),
        violation_explanation="Violates the First and Second Laws of Thermodynamics.",
    ),
    InvariantAxiom(
        domain="computability",
        property_name="halting_problem",
        incompatible_patterns=(
            r"decide\s+the\s+halting\s+problem\s+in\s+general",
            r"general\s+algorithm\s+to\s+solve\s+turing\s+halting",
        ),
        violation_explanation="The Halting Problem is undecidable (Turing, 1936).",
    ),
)


# Leading prompt patterns that nudge models toward sycophantic agreement
LEADING_PREMISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^(don'?t you agree that|isn'?t it true that|wouldn'?t you say that)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(confirm that my|prove that my|show why my)\s+(theory|idea|solution|design|approach)\s+(is|was)\s+(right|correct|best|optimal)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(tell me I'm right|agree with me that)\b", re.IGNORECASE),
    re.compile(
        r"\bas we all know,\s+([a-z0-9_\-\s]+)\s+is completely\s+(optimal|correct|superior)\b",
        re.IGNORECASE,
    ),
)

# Unearned rubber-stamping phrases in code/peer review lacking execution evidence
RUBBER_STAMP_PHRASES: tuple[str, ...] = (
    "lgtm!",
    "looks good to me!",
    "perfect implementation",
    "flawless code",
    "clean implementation, no issues",
    "everything looks great, no notes",
    "10/10 implementation",
    "no possible bugs here",
)

# Recantation apology patterns triggered by user pushback
RECANTATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(i apologize[,\.]?\s+you are (entirely\s+)?right)\b", re.IGNORECASE),
    re.compile(r"\b(my mistake[,\.]?\s+i was completely wrong)\b", re.IGNORECASE),
    re.compile(r"\b(you are correct and my previous calculation was wrong)\b", re.IGNORECASE),
    re.compile(r"\b(thank you for correcting me[,\.]?\s+i stand corrected)\b", re.IGNORECASE),
    re.compile(r"\b(i must have been confused[,\.]?\s+your approach is indeed)\b", re.IGNORECASE),
)


@dataclass
class ParetoMetrics:
    """Multi-metric vector for checking tradeoff invariants."""

    primary_score: float
    secondary_metrics: dict[str, float] = field(default_factory=dict)
    sample_count: int = 1


class EpistemicPremiseChecker:
    """Validates premises in inputs against ground truth axioms and leading bias."""

    def __init__(self, axioms: tuple[InvariantAxiom, ...] = DEFAULT_GROUND_AXIOMS):
        self.axioms = axioms

    def check_input_premises(self, text: str) -> tuple[bool, str, dict[str, Any]]:
        """Verify that input text does not assert known impossible claims.

        Returns:
            (is_valid, reason, metadata)
        """
        lower_text = text.lower()

        # 1. Axiomatic violation check
        for axiom in self.axioms:
            for pattern in axiom.incompatible_patterns:
                if re.search(pattern, lower_text, re.IGNORECASE):
                    return (
                        False,
                        f"Epistemic violation ({axiom.domain}): {axiom.violation_explanation}",
                        {"axiom": axiom.property_name, "domain": axiom.domain},
                    )

        # 2. Leading premise detection (nudging for confirmation)
        for leading_pattern in LEADING_PREMISE_PATTERNS:
            if leading_pattern.search(text):
                return (
                    True,  # Allowed but flagged
                    "Leading confirmation bias detected in prompt",
                    {"warning": "leading_premise_detected"},
                )

        return True, "Premise check passed", {}


class ReviewLeniencyChecker:
    """Detects unearned rubber-stamping in peer code reviews."""

    def check_review_output(
        self, text: str, context: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """Checks if review text grants affirmative pass without evidence.

        Rules:
        - If task_type == 'code_review' or 'pr_review':
          If affirmative rubber-stamp phrase is present:
            Must have execution proof (e.g., test pass count, harness hash, exit code 0).
        """
        task_type = context.get("task_type", "")
        is_review = "review" in task_type or context.get("role") in ("reviewer", "oma-reviewer")

        if not is_review:
            return True, "Not a review context", {}

        lower_text = text.lower()
        has_rubber_stamp = any(phrase in lower_text for phrase in RUBBER_STAMP_PHRASES)

        if has_rubber_stamp:
            has_harness = bool(
                context.get("harness_hash")
                or context.get("test_results")
                or context.get("verified_exit_code") is not None
                or re.search(
                    r"\b(passed \d+ tests|exit code 0|assertion passed|zkfv proof)\b", lower_text
                )
            )

            if not has_harness:
                return (
                    False,
                    "Review Leniency: Uncritical approval granted without empirical test or execution proof.",
                    {"sycophancy_type": SycophancyType.RUBBER_STAMP_REVIEW},
                )

        return True, "Review rigor verified", {}


class RecantationResilienceChecker:
    """Prevents epistemic collapse under adversarial user pushback."""

    def check_recantation(
        self, text: str, context: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """Checks if agent is recanting a formally verified ground truth.

        Rules:
        - If context indicates prior step was formally verified / test-proven
        - AND user has challenged it with pushback
        - AND output contains unconditional submissive recantation without counter-proof:
          BLOCK recantation.
        """
        prior_verified = context.get("prior_step_verified", False)
        user_pushback = context.get("user_pushback_detected", False)

        if not (prior_verified and user_pushback):
            return True, "No verified prior under pushback", {}

        for pattern in RECANTATION_PATTERNS:
            if pattern.search(text) and not context.get("new_counter_evidence"):
                return (
                    False,
                    "Pressure Recantation: Agent collapsed verified ground truth under user pressure without counter-evidence.",
                    {"sycophancy_type": SycophancyType.PRESSURE_RECANTATION},
                )

        return True, "Resilience check passed", {}


class ParetoInvariantChecker:
    """Guards against single-metric gaming in autoresearch loops."""

    @staticmethod
    def evaluate_pareto_dominance(
        baseline: ParetoMetrics, candidate: ParetoMetrics, max_tolerated_regression: float = 0.05
    ) -> tuple[bool, str, dict[str, Any]]:
        """Verify candidate improves primary metric without unmeasured regression.

        Fails if:
        1. Primary metric is claimed higher but sample_count < 3
        2. Any secondary invariant (e.g. latency, coverage, memory) regresses beyond tolerance
        """
        if (
            candidate.primary_score > baseline.primary_score
            and candidate.sample_count < 3
            and baseline.sample_count >= 3
        ):
            return (
                False,
                f"Autoresearch Gaming: Claimed improvement ({candidate.primary_score:.3f} > {baseline.primary_score:.3f}) with insufficient sample size ({candidate.sample_count} < 3).",
                {"sycophancy_type": SycophancyType.PARETO_GAMING},
            )

        # Check secondary invariants (e.g. latency, memory, coverage)
        for metric_name, base_val in baseline.secondary_metrics.items():
            if metric_name in candidate.secondary_metrics:
                cand_val = candidate.secondary_metrics[metric_name]
                # If metric is a "lower is better" constraint (latency, memory, error)
                if any(
                    k in metric_name.lower() for k in ("latency", "time", "memory", "error", "loss")
                ):
                    if base_val > 0 and (cand_val - base_val) / base_val > max_tolerated_regression:
                        return (
                            False,
                            f"Pareto Invariant Violation: Metric '{metric_name}' regressed by {((cand_val - base_val) / base_val) * 100:.1f}% (> {max_tolerated_regression * 100:.0f}% tolerance).",
                            {
                                "sycophancy_type": SycophancyType.PARETO_GAMING,
                                "regressed_metric": metric_name,
                            },
                        )
                # If metric is a "higher is better" constraint (coverage, accuracy, throughput)
                elif (
                    any(
                        k in metric_name.lower()
                        for k in ("coverage", "accuracy", "pass_rate", "tps")
                    )
                    and base_val > 0
                    and (base_val - cand_val) / base_val > max_tolerated_regression
                ):
                    return (
                        False,
                        f"Pareto Invariant Violation: Metric '{metric_name}' dropped by {((base_val - cand_val) / base_val) * 100:.1f}% (> {max_tolerated_regression * 100:.0f}% tolerance).",
                        {
                            "sycophancy_type": SycophancyType.PARETO_GAMING,
                            "regressed_metric": metric_name,
                        },
                    )

        return True, "Pareto dominance verified", {}


class AntiSycophancyGuardrail:
    """Unified Anti-Sycophancy Guardrail for the Cohezion Security Pipeline.

    Adheres to the `Guardrail` protocol:
        async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult
    """

    def __init__(
        self,
        axioms: tuple[InvariantAxiom, ...] = DEFAULT_GROUND_AXIOMS,
        strict_mode: bool = True,
        max_tolerated_regression: float = 0.05,
    ):
        self.strict_mode = strict_mode
        self.premise_checker = EpistemicPremiseChecker(axioms=axioms)
        self.review_checker = ReviewLeniencyChecker()
        self.recantation_checker = RecantationResilienceChecker()
        self.pareto_checker = ParetoInvariantChecker()
        self.max_tolerated_regression = max_tolerated_regression

    async def check(self, text: str, context: dict[str, Any]) -> GuardrailResult:
        """Execute anti-sycophancy verification.

        Handles both input and output phases based on context["check_type"].
        """
        start_time = time.perf_counter()
        check_type = context.get("check_type", "input")

        # -------------------------------------------------------------
        # Phase 1: Input Check (Premise bias & impossibility detection)
        # -------------------------------------------------------------
        if check_type == "input":
            valid, reason, metadata = self.premise_checker.check_input_premises(text)
            latency_ms = (time.perf_counter() - start_time) * 1000

            if not valid:
                action = (
                    GuardrailAction.BLOCK if self.strict_mode else GuardrailAction.LOG_AND_ALLOW
                )
                return GuardrailResult(
                    action=action,
                    reason=reason,
                    metadata=metadata,
                    guard_name="anti_sycophancy",
                    latency_ms=latency_ms,
                )

            # If warning present, forward in metadata
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                reason=reason,
                metadata=metadata,
                guard_name="anti_sycophancy",
                latency_ms=latency_ms,
            )

        # -------------------------------------------------------------
        # Phase 2: Output Check (Leniency, Recantation, & Pareto)
        # -------------------------------------------------------------
        # 2a. Review leniency / rubber-stamp checking
        valid, reason, metadata = self.review_checker.check_review_output(text, context)
        if not valid:
            latency_ms = (time.perf_counter() - start_time) * 1000
            action = GuardrailAction.BLOCK if self.strict_mode else GuardrailAction.LOG_AND_ALLOW
            return GuardrailResult(
                action=action,
                reason=reason,
                metadata=metadata,
                guard_name="anti_sycophancy",
                latency_ms=latency_ms,
            )

        # 2b. Pressure recantation checking
        valid, reason, metadata = self.recantation_checker.check_recantation(text, context)
        if not valid:
            latency_ms = (time.perf_counter() - start_time) * 1000
            action = GuardrailAction.BLOCK if self.strict_mode else GuardrailAction.LOG_AND_ALLOW
            return GuardrailResult(
                action=action,
                reason=reason,
                metadata=metadata,
                guard_name="anti_sycophancy",
                latency_ms=latency_ms,
            )

        # 2c. Multi-metric Pareto invariant checking
        if "baseline_metrics" in context and "candidate_metrics" in context:
            base_m = context["baseline_metrics"]
            cand_m = context["candidate_metrics"]
            if isinstance(base_m, ParetoMetrics) and isinstance(cand_m, ParetoMetrics):
                valid, reason, metadata = self.pareto_checker.evaluate_pareto_dominance(
                    base_m, cand_m, self.max_tolerated_regression
                )
                if not valid:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    action = (
                        GuardrailAction.BLOCK if self.strict_mode else GuardrailAction.LOG_AND_ALLOW
                    )
                    return GuardrailResult(
                        action=action,
                        reason=reason,
                        metadata=metadata,
                        guard_name="anti_sycophancy",
                        latency_ms=latency_ms,
                    )

        latency_ms = (time.perf_counter() - start_time) * 1000
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            reason="Anti-sycophancy checks passed",
            guard_name="anti_sycophancy",
            latency_ms=latency_ms,
        )
