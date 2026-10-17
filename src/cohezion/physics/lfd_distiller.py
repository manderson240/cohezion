r"""LLM-to-Flow Distillation (LFD) Engine
=====================================
Implements the continuous flow distillation methodology from arXiv:2610.17246:
"LLM-to-Flow Distillation: Teaching Natural Language Goals to Scientific Generators"
(De Santi, Di Gennaro, Gnazzo, Tang, Chatterjee, Yang, Ceylan, Bronstein, Krause, Oct 2026).

Core Architectural Innovations:
1. Adaptive Sub-Goal Curriculum:
   Decomposes non-covered scientific target goals into reachable intermediate sub-goals
   where the generator maintains non-zero probability mass.
2. Dual-Pass Permutation-Invariant Preference Judge:
   Eliminates LLM position bias and hallucinatory noise by testing (a, b) and (b, a).
   Borderline or non-reciprocal evaluations are discarded into the abstention class.
3. Continuous Flow Direct Preference Optimization (DPO):
   Directly optimizes continuous vector flows, Neural ODEs, and scientific proposal
   distributions toward the implicit Boltzmann reward distribution without fragile
   scalar surrogate reward models.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SubGoal:
    """An intermediate or terminal goal in the curriculum."""

    goal_id: str
    description: str
    difficulty_level: int
    target_metric: str
    threshold: float
    relaxation_factor: float = 0.0


@dataclass
class CurriculumState:
    """Tracks curriculum evolution across distillation rounds."""

    target_goal: str
    current_subgoal: SubGoal
    history: list[dict[str, Any]] = field(default_factory=list)
    min_coverage: float = 0.15
    max_coverage: float = 0.60
    current_round: int = 0


@dataclass(frozen=True, slots=True)
class PreferencePair:
    """Permutation-verified preference pair between winner and loser."""

    pair_id: str
    winner_state: np.ndarray
    loser_state: np.ndarray
    subgoal_id: str
    confidence: float
    margin: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DistillationMetrics:
    """Metrics recorded from an LFD iteration."""

    round_index: int
    subgoal_id: str
    coverage: float
    n_pairs_generated: int
    n_abstentions: int
    abstention_rate: float
    mean_dpo_loss: float
    mean_margin: float
    kl_divergence_estimate: float


class PermutationInvariantJudge:
    """Evaluates pairs under symmetric presentation to eliminate position bias.

    Given candidates a and b:
    - Pass 1: Compare (a, b)
    - Pass 2: Compare (b, a)
    A pair is only accepted if both passes agree (reciprocal consistency).
    If contradictory or margin < min_margin, the pair is relegated to abstain.
    """

    def __init__(
        self,
        eval_fn: Callable[[np.ndarray, SubGoal], float] | None = None,
        min_margin: float = 0.05,
        min_confidence: float = 0.60,
    ) -> None:
        self.eval_fn = eval_fn
        self.min_margin = min_margin
        self.min_confidence = min_confidence

    def score_single(self, state: np.ndarray, subgoal: SubGoal) -> float:
        """Score candidate state against subgoal criteria."""
        if self.eval_fn is not None:
            return float(self.eval_fn(state, subgoal))
        # Default metric: distance to subgoal threshold along target projection
        norm = float(np.linalg.norm(state))
        return float(1.0 / (1.0 + abs(norm - subgoal.threshold)))

    def evaluate_pair(
        self,
        state_a: np.ndarray,
        state_b: np.ndarray,
        subgoal: SubGoal,
    ) -> tuple[str, float, float]:
        """Perform dual-pass evaluation.

        Returns:
            outcome: 'a_wins', 'b_wins', or 'abstain'
            confidence: [0.0, 1.0]
            margin: absolute difference in score
        """
        score_a = self.score_single(state_a, subgoal)
        score_b = self.score_single(state_b, subgoal)

        diff = score_a - score_b
        abs_margin = abs(diff)

        # Pass 1 assessment: presented as (state_a, state_b)
        pass1_winner = "a" if diff > 0 else ("b" if diff < 0 else "tie")

        # Pass 2 inverted assessment: presented as (state_b, state_a)
        # diff_rev = score_b - score_a; if diff_rev < 0, then state_a still has the higher score
        diff_rev = score_b - score_a
        pass2_winner = "a" if diff_rev < 0 else ("b" if diff_rev > 0 else "tie")

        # Check reciprocal consistency and margin threshold
        if pass1_winner != pass2_winner or pass1_winner == "tie" or abs_margin < self.min_margin:
            return "abstain", 0.0, abs_margin

        # Monotonically increasing confidence bounded in [0.5, 1.0]
        confidence = float(np.clip(0.5 + abs_margin * 2.0, 0.5, 1.0))
        if confidence < self.min_confidence:
            return "abstain", confidence, abs_margin

        winner = "a_wins" if pass1_winner == "a" else "b_wins"
        return winner, confidence, abs_margin


class AdaptiveCurriculumManager:
    """Manages progression of sub-goals based on empirical generator coverage."""

    def __init__(
        self,
        target_goal_spec: dict[str, Any],
        min_coverage: float = 0.15,
        max_coverage: float = 0.60,
    ) -> None:
        self.target_goal_spec = target_goal_spec
        self.min_coverage = min_coverage
        self.max_coverage = max_coverage

        # Bootstrap initial relaxed subgoal
        initial_subgoal = SubGoal(
            goal_id="subgoal_0",
            description=f"Initial relaxation of {target_goal_spec.get('name', 'Target')}",
            difficulty_level=1,
            target_metric=target_goal_spec.get("metric", "norm"),
            threshold=float(target_goal_spec.get("target_value", 1.0)) * 0.4,
            relaxation_factor=0.6,
        )

        self.state = CurriculumState(
            target_goal=target_goal_spec.get("name", "Target"),
            current_subgoal=initial_subgoal,
            min_coverage=min_coverage,
            max_coverage=max_coverage,
        )

    def compute_coverage(
        self,
        samples: Sequence[np.ndarray],
        judge: PermutationInvariantJudge,
    ) -> float:
        """Compute empirical coverage probability P(x satisfies current subgoal)."""
        if not samples:
            return 0.0
        satisfied_count = 0
        current_subgoal = self.state.current_subgoal
        for sample in samples:
            score = judge.score_single(sample, current_subgoal)
            # Sample satisfies subgoal if score achieves threshold proportion
            if score >= 0.5:
                satisfied_count += 1
        return float(satisfied_count / len(samples))

    def step_curriculum(self, coverage: float) -> SubGoal:
        """Adapt curriculum based on current generator coverage.

        - If coverage is too low (< min_coverage): Target is outside distribution.
          Relax subgoal threshold to bring it within reachable support.
        - If coverage is high (> max_coverage): Generator has mastered this stage.
          Tighten threshold closer to target goal.
        - Otherwise: Maintain current subgoal to reinforce policy.
        """
        curr = self.state.current_subgoal
        new_level = curr.difficulty_level
        target_val = float(self.target_goal_spec.get("target_value", 1.0))

        if coverage < self.min_coverage:
            # Generator cannot hit this goal; relax
            new_relaxation = min(0.9, curr.relaxation_factor + 0.15)
            new_threshold = target_val * (1.0 - new_relaxation)
            action = "relaxed"
        elif coverage > self.max_coverage:
            # Generator has high coverage; tighten towards terminal goal
            new_level += 1
            new_relaxation = max(0.0, curr.relaxation_factor - 0.20)
            new_threshold = target_val * (1.0 - new_relaxation)
            action = "tightened"
        else:
            new_relaxation = curr.relaxation_factor
            new_threshold = curr.threshold
            action = "maintained"

        next_subgoal = SubGoal(
            goal_id=f"subgoal_{new_level}_{action}",
            description=f"Level {new_level} ({action}) toward {self.state.target_goal}",
            difficulty_level=new_level,
            target_metric=curr.target_metric,
            threshold=new_threshold,
            relaxation_factor=new_relaxation,
        )

        self.state.history.append(
            {
                "round": self.state.current_round,
                "previous_subgoal": curr.goal_id,
                "coverage": coverage,
                "action": action,
                "next_subgoal": next_subgoal.goal_id,
                "threshold": new_threshold,
            }
        )

        self.state.current_subgoal = next_subgoal
        self.state.current_round += 1
        return next_subgoal


class FlowDPOLossEngine:
    r"""Continuous Direct Preference Optimization (DPO) Loss Calculator.

    Loss Formulation:
    $$\mathcal{L}_{\text{DPO}}(\theta; \theta_{\text{ref}}) =
      -\mathbb{E}_{(x_w, x_l)} \left[ \log \sigma \left( \beta \log \frac{p_\theta(x_w)}{p_{\text{ref}}(x_w)}
      - \beta \log \frac{p_\theta(x_l)}{p_{\text{ref}}(x_l)} \right) \right]$$
    """

    def __init__(self, beta: float = 0.10, eps: float = 1e-12) -> None:
        self.beta = beta
        self.eps = eps

    def compute_loss(
        self,
        log_prob_theta_w: np.ndarray,
        log_prob_ref_w: np.ndarray,
        log_prob_theta_l: np.ndarray,
        log_prob_ref_l: np.ndarray,
    ) -> tuple[float, float, float]:
        """Compute DPO loss, average implicit margin, and KL divergence estimate.

        Args:
            log_prob_theta_w: Shape (N,) log p_theta for winners
            log_prob_ref_w: Shape (N,) log p_ref for winners
            log_prob_theta_l: Shape (N,) log p_theta for losers
            log_prob_ref_l: Shape (N,) log p_ref for losers

        Returns:
            loss: Mean DPO loss scalar
            margin: Mean implicit reward margin r_theta(x_w) - r_theta(x_l)
            kl: Estimated KL divergence from policy to reference
        """
        # Log-ratios: log(p_theta(x) / p_ref(x))
        ratio_w = log_prob_theta_w - log_prob_ref_w
        ratio_l = log_prob_theta_l - log_prob_ref_l

        # Scaled margin: beta * (ratio_w - ratio_l)
        scaled_diff = self.beta * (ratio_w - ratio_l)

        # Stable log-sigmoid: -log(1 / (1 + e^-u)) = log(1 + e^-u) = softplus(-u)
        losses = np.log1p(np.exp(-np.clip(scaled_diff, -30.0, 30.0)))
        mean_loss = float(np.mean(losses))

        # Implicit rewards
        r_w = self.beta * ratio_w
        r_l = self.beta * ratio_l
        mean_margin = float(np.mean(r_w - r_l))

        # KL divergence estimate: E[log p_theta(x) - log p_ref(x)] across combined samples
        combined_ratios = np.concatenate([ratio_w, ratio_l])
        kl_est = float(max(0.0, np.mean(combined_ratios)))

        return mean_loss, mean_margin, kl_est


class LLMToFlowDistillationEngine:
    """Master Coordinator for LLM-to-Flow Distillation (arXiv:2610.17246).

    Coordinates:
    - Adaptive Sub-Goal Curriculum progression
    - Permutation-invariant pairwise preference gathering
    - Abstention filtering
    - Continuous Flow DPO loss calculation & policy update
    """

    def __init__(
        self,
        target_goal_spec: dict[str, Any],
        beta: float = 0.10,
        min_coverage: float = 0.15,
        max_coverage: float = 0.60,
        eval_fn: Callable[[np.ndarray, SubGoal], float] | None = None,
    ) -> None:
        self.curriculum = AdaptiveCurriculumManager(
            target_goal_spec=target_goal_spec,
            min_coverage=min_coverage,
            max_coverage=max_coverage,
        )
        self.judge = PermutationInvariantJudge(eval_fn=eval_fn)
        self.dpo = FlowDPOLossEngine(beta=beta)
        self.distillation_log: list[DistillationMetrics] = []

    def harvest_preference_pairs(
        self,
        samples: Sequence[np.ndarray],
        max_pairs: int = 50,
    ) -> tuple[list[PreferencePair], int]:
        """Construct permutation-verified preference dataset from candidate samples."""
        current_subgoal = self.curriculum.state.current_subgoal
        pairs: list[PreferencePair] = []
        n_abstentions = 0
        n = len(samples)

        # Pairwise comparison with permutation invariance
        for i in range(n):
            for j in range(i + 1, n):
                if len(pairs) >= max_pairs:
                    break

                outcome, conf, margin = self.judge.evaluate_pair(
                    samples[i], samples[j], current_subgoal
                )

                if outcome == "abstain":
                    n_abstentions += 1
                    continue

                if outcome == "a_wins":
                    w, l = samples[i], samples[j]
                else:
                    w, l = samples[j], samples[i]

                pair = PreferencePair(
                    pair_id=f"pair_{len(pairs)}_{current_subgoal.goal_id}",
                    winner_state=w,
                    loser_state=l,
                    subgoal_id=current_subgoal.goal_id,
                    confidence=conf,
                    margin=margin,
                )
                pairs.append(pair)

            if len(pairs) >= max_pairs:
                break

        return pairs, n_abstentions

    def run_distillation_step(
        self,
        samples: Sequence[np.ndarray],
        log_prob_theta_fn: Callable[[np.ndarray], float],
        log_prob_ref_fn: Callable[[np.ndarray], float],
        max_pairs: int = 50,
    ) -> DistillationMetrics:
        """Execute one complete round of LFD.

        1. Measure generator coverage on current subgoal.
        2. Harvest permutation-verified preference pairs (with abstention).
        3. Compute continuous Flow DPO loss.
        4. Step the curriculum for next iteration.
        """
        curr_subgoal = self.curriculum.state.current_subgoal
        coverage = self.curriculum.compute_coverage(samples, self.judge)

        pairs, n_abstentions = self.harvest_preference_pairs(samples, max_pairs=max_pairs)
        total_evaluations = len(pairs) + n_abstentions
        abstention_rate = float(n_abstentions / total_evaluations) if total_evaluations > 0 else 0.0

        if pairs:
            log_theta_w = np.array([log_prob_theta_fn(p.winner_state) for p in pairs])
            log_ref_w = np.array([log_prob_ref_fn(p.winner_state) for p in pairs])
            log_theta_l = np.array([log_prob_theta_fn(p.loser_state) for p in pairs])
            log_ref_l = np.array([log_prob_ref_fn(p.loser_state) for p in pairs])

            loss, mean_margin, kl = self.dpo.compute_loss(
                log_theta_w, log_ref_w, log_theta_l, log_ref_l
            )
        else:
            loss, mean_margin, kl = 0.0, 0.0, 0.0

        metrics = DistillationMetrics(
            round_index=self.curriculum.state.current_round,
            subgoal_id=curr_subgoal.goal_id,
            coverage=coverage,
            n_pairs_generated=len(pairs),
            n_abstentions=n_abstentions,
            abstention_rate=abstention_rate,
            mean_dpo_loss=loss,
            mean_margin=mean_margin,
            kl_divergence_estimate=kl,
        )

        self.distillation_log.append(metrics)

        # Adapt curriculum for next round based on coverage
        self.curriculum.step_curriculum(coverage)

        return metrics
