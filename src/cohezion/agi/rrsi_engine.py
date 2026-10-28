"""RRSI: Regularized Recursive Self-Improvement of Agent Harnesses (arXiv:2609.24972).

Implements the regularization principles from Google Research (Sept 2026):
1. Annealed Edit Budget: b_t = max(1, floor(b_0 * gamma^t)), bounding candidate complexity.
2. Critic (Pre-Eval Screening): Screen out benchmark leakage and hardcoded task-specific heuristics.
3. Noise-Adjusted Selection: Candidate accepted only if Delta Score > delta_noise + lambda_cost * max(0, Delta Cost).
4. Pruner: Identify and retire dormant or ineffective harness machinery to achieve -30% token overhead.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HarnessEdit:
    """An individual atomic edit to an agent harness."""

    edit_id: str
    target_component: str  # 'prompt', 'tool', 'control_flow', 'memory', 'verifier'
    description: str
    diff_patch: str
    added_tokens: int = 0


@dataclass
class CandidateHarness:
    """A proposed harness variation comprising one or more bundled edits."""

    candidate_id: str
    parent_id: str
    iteration: int
    edits: list[HarnessEdit]
    estimated_cost_tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def edit_count(self) -> int:
        return len(self.edits)


class RRSIBudgetScheduler:
    """Computes the annealed edit budget b_t and tracks iteration stalling."""

    def __init__(
        self, initial_budget: int = 5, decay_gamma: float = 0.85, min_budget: int = 1
    ) -> None:
        self.initial_budget = initial_budget
        self.decay_gamma = decay_gamma
        self.min_budget = min_budget

    def compute_budget(self, iteration: int) -> int:
        """Compute maximum allowable bundled edits for the given iteration: b_t = max(1, floor(b_0 * gamma^t))."""
        raw_budget = math.floor(self.initial_budget * (self.decay_gamma**iteration))
        return max(self.min_budget, raw_budget)


class RRSICritic:
    """Pre-evaluation screening for benchmark leakage and superficial overfitting."""

    # Patterns indicating hardcoded solutions rather than generalizable skills
    LEAKAGE_PATTERNS = (
        r"\b(test_case_\d+|task_\d{3,}|sample_\d+)\b",
        r"\b(hardcoded|override_for_benchmark|if\s+problem_id\s*==)\b",
        r"\b(benchmark_secret|eval_only_flag)\b",
    )

    def __init__(self, custom_denylist: list[str] | None = None) -> None:
        self.denylist = list(self.LEAKAGE_PATTERNS) + (custom_denylist or [])
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.denylist]

    def screen(self, candidate: CandidateHarness) -> tuple[bool, str]:
        """Screen candidate for data leakage before wasting expensive evaluation budget.

        Returns (passed, reason).
        """
        for edit in candidate.edits:
            for pattern in self._compiled:
                match = pattern.search(edit.diff_patch) or pattern.search(edit.description)
                if match:
                    reason = f"Rejected by Critic: edit '{edit.edit_id}' matched leakage pattern '{match.group(0)}'"
                    logger.warning(reason)
                    return False, reason

        return True, "Passed critic screening: no benchmark leakage detected."


@dataclass
class EvaluationOutcome:
    """Measured performance and cost of a harness evaluation."""

    empirical_score: float  # [0.0, 1.0]
    total_tokens_consumed: int
    execution_time_ms: float
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RRSISelector:
    """Noise-adjusted selection rule with cost-regularization."""

    def __init__(self, noise_delta: float = 0.015, cost_lambda: float = 0.00005) -> None:
        self.noise_delta = noise_delta
        self.cost_lambda = cost_lambda

    def should_accept(
        self,
        baseline_eval: EvaluationOutcome,
        candidate_eval: EvaluationOutcome,
    ) -> tuple[bool, str]:
        """Determine if candidate gain exceeds noise floor and pays for token cost.

        Accept condition: Delta Score > delta_noise + lambda_cost * max(0, Delta Cost)
        """
        delta_score = candidate_eval.empirical_score - baseline_eval.empirical_score
        delta_cost = candidate_eval.total_tokens_consumed - baseline_eval.total_tokens_consumed

        cost_penalty = self.cost_lambda * max(0, delta_cost)
        threshold = self.noise_delta + cost_penalty

        if delta_score > threshold:
            msg = (
                f"Accepted: Delta score {delta_score:.4f} exceeds noise threshold {threshold:.4f} "
                f"(Delta cost: {delta_cost:+d} tokens)."
            )
            return True, msg

        if delta_score <= 0.0:
            msg = f"Rejected: Score regressed or unchanged ({delta_score:+.4f})."
        elif delta_score <= self.noise_delta:
            msg = f"Rejected: Gain ({delta_score:.4f}) is within evaluation noise band ({self.noise_delta:.4f})."
        else:
            msg = f"Rejected: Gain ({delta_score:.4f}) insufficient to justify token cost penalty ({cost_penalty:.4f})."

        return False, msg


class RRSIPruner:
    """Identifies and prunes dormant, ineffective, or token-bloating harness machinery."""

    def __init__(self, dormancy_threshold_cycles: int = 5) -> None:
        self.dormancy_threshold = dormancy_threshold_cycles
        # edit_id -> last_useful_iteration
        self.component_last_used: dict[str, int] = {}

    def record_usage(self, edit_id: str, current_iteration: int) -> None:
        self.component_last_used[edit_id] = current_iteration

    def identify_prunable_edits(
        self, active_edit_ids: list[str], current_iteration: int
    ) -> list[str]:
        """Return edit IDs that have not contributed for > dormancy_threshold cycles."""
        prune_candidates = []
        for eid in active_edit_ids:
            last_used = self.component_last_used.get(eid, 0)
            if current_iteration - last_used >= self.dormancy_threshold:
                prune_candidates.append(eid)
        return prune_candidates


class RRSIRegularizedEngine:
    """Master orchestrator combining proposal, critic screening, selection, and pruning."""

    def __init__(
        self,
        initial_budget: int = 5,
        decay_gamma: float = 0.85,
        noise_delta: float = 0.015,
        cost_lambda: float = 0.00005,
    ) -> None:
        self.scheduler = RRSIBudgetScheduler(initial_budget, decay_gamma)
        self.critic = RRSICritic()
        self.selector = RRSISelector(noise_delta, cost_lambda)
        self.pruner = RRSIPruner()
        self.iteration = 0
        self.active_edits: dict[str, HarnessEdit] = {}

    def propose_candidate(
        self,
        candidate_id: str,
        parent_id: str,
        proposed_edits: list[HarnessEdit],
    ) -> tuple[CandidateHarness | None, str]:
        """Create and regularize a candidate harness under the annealed budget."""
        budget = self.scheduler.compute_budget(self.iteration)
        if len(proposed_edits) > budget:
            msg = f"Proposal rejected: {len(proposed_edits)} edits exceed annealed budget {budget} for iteration {self.iteration}."
            logger.warning(msg)
            return None, msg

        candidate = CandidateHarness(
            candidate_id=candidate_id,
            parent_id=parent_id,
            iteration=self.iteration,
            edits=proposed_edits,
            estimated_cost_tokens=sum(e.added_tokens for e in proposed_edits),
        )

        # Screen through critic
        passed, reason = self.critic.screen(candidate)
        if not passed:
            return None, reason

        return (
            candidate,
            f"Candidate {candidate_id} approved with {len(proposed_edits)} edits (budget: {budget}).",
        )

    def evaluate_and_step(
        self,
        candidate: CandidateHarness,
        baseline_eval: EvaluationOutcome,
        candidate_eval: EvaluationOutcome,
    ) -> tuple[bool, str]:
        """Apply noise-adjusted selection rule and advance iteration."""
        accepted, msg = self.selector.should_accept(baseline_eval, candidate_eval)
        self.iteration += 1

        if accepted:
            for e in candidate.edits:
                self.active_edits[e.edit_id] = e
                self.pruner.record_usage(e.edit_id, self.iteration)

        return accepted, msg
