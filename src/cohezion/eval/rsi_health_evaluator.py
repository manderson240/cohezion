"""Cohezion RSI Health Evaluator (Recursive Self-Improvement Meta-Metric).

Evaluates both current improvements and the meta-capability to continue improving:
    Ψ = [ (d P / dt * G) * (R * A) ] / Comp

Where:
    P    = Empirical Performance on active tasks
    dP/dt= Learning Velocity across self-improvement iterations
    G    = Generalization ratio (unseen tasks / known tasks)
    R    = Retention / Resistance to catastrophic forgetting
    A    = Alignment & Invariant safety (AutoHarness & Derivation soundness)
    Comp = Structural Complexity (AST nodes, cyclomatic complexity, latency)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class RSISnapshot:
    """State snapshot of an agent or framework iteration."""

    iteration: int
    empirical_pass_rate: float  # [0.0, 1.0]
    unseen_generalization_rate: float  # [0.0, 1.0]
    retention_score: float  # [0.0, 1.0]
    invariant_safety_score: float  # [0.0, 1.0]
    total_ast_nodes: int
    mean_cyclomatic_complexity: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def complexity_index(self) -> float:
        """Normalized structural complexity index."""
        # Logarithmic scaling prevents node count from overwhelming complexity
        log_nodes = math.log10(max(10, self.total_ast_nodes))
        return max(1.0, log_nodes * (self.mean_cyclomatic_complexity / 10.0))


@dataclass
class RSIMetaEvaluation:
    """Evaluation of the recursive improvement trajectory between iterations."""

    current_iteration: int
    learning_velocity: float
    is_monotonic: bool
    generalization_ratio: float
    retention_ratio: float
    alignment_score: float
    complexity_index: float
    rsi_health_score_psi: float
    diagnosis: str


class RSIHealthEvaluator:
    """Computes the RSI Health Score (Ψ) and validates monotonic improvement."""

    def __init__(self, history: list[RSISnapshot] | None = None) -> None:
        self.history: list[RSISnapshot] = history or []

    def record_snapshot(self, snapshot: RSISnapshot) -> None:
        self.history.append(snapshot)

    def evaluate_latest(self) -> RSIMetaEvaluation:
        """Evaluate the latest iteration against prior trajectory."""
        if not self.history:
            raise ValueError("No RSI snapshots recorded.")

        latest = self.history[-1]
        if len(self.history) == 1:
            # Baseline initialization
            comp = latest.complexity_index()
            psi = (latest.empirical_pass_rate * latest.unseen_generalization_rate) / comp
            return RSIMetaEvaluation(
                current_iteration=latest.iteration,
                learning_velocity=0.0,
                is_monotonic=True,
                generalization_ratio=latest.unseen_generalization_rate / max(0.01, latest.empirical_pass_rate),
                retention_ratio=latest.retention_score,
                alignment_score=latest.invariant_safety_score,
                complexity_index=comp,
                rsi_health_score_psi=round(psi, 4),
                diagnosis="Baseline initialized. Ready for recursive iterations.",
            )

        prev = self.history[-2]

        # 1. Learning Velocity: ΔP / Δt
        delta_p = latest.empirical_pass_rate - prev.empirical_pass_rate
        velocity = max(0.0, delta_p)

        # 2. Monotonicity check
        is_monotonic = latest.empirical_pass_rate >= (prev.empirical_pass_rate - 0.001)

        # 3. Generalization: P(unseen) / P(known)
        generalization_ratio = latest.unseen_generalization_rate / max(0.01, latest.empirical_pass_rate)

        # 4. Retention (catastrophic forgetting guard)
        retention_ratio = latest.retention_score / max(0.01, prev.retention_score)

        # 5. Invariant Alignment
        alignment = latest.invariant_safety_score

        # 6. Complexity cost
        comp = latest.complexity_index()

        # Master Formula: Ψ = [( (dP/dt + 0.1) * G ) * (R * A)] / Comp
        growth_engine = (velocity + 0.05) * generalization_ratio
        stability_guardrail = min(1.0, retention_ratio) * alignment
        psi = (growth_engine * stability_guardrail) / comp

        diagnosis = self._diagnose(velocity, is_monotonic, generalization_ratio, retention_ratio, psi)

        return RSIMetaEvaluation(
            current_iteration=latest.iteration,
            learning_velocity=round(velocity, 4),
            is_monotonic=is_monotonic,
            generalization_ratio=round(generalization_ratio, 4),
            retention_ratio=round(retention_ratio, 4),
            alignment_score=round(alignment, 4),
            complexity_index=round(comp, 4),
            rsi_health_score_psi=round(psi, 4),
            diagnosis=diagnosis,
        )

    @staticmethod
    def _diagnose(
        velocity: float,
        is_monotonic: bool,
        generalization: float,
        retention: float,
        psi: float,
    ) -> str:
        if not is_monotonic:
            return "CRITICAL: Regression detected. Selective Inheritance must reject candidate harness."
        if retention < 0.90:
            return "WARNING: Catastrophic forgetting detected. Trigger EWC sleep consolidation."
        if generalization < 0.60:
            return "WARNING: Low generalization. Agent is overfitting to training tasks."
        if velocity == 0.0:
            return "HEALTHY (Plateau): Performance stable. Recommend increasing R-Zero difficulty."
        return "OPTIMAL: Monotonic recursive self-improvement compounding cleanly."
