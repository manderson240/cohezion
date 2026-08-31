"""Cost optimization for ResearchAgent.

Token-aware budgeting, cost tracking, and budget enforcement.
Elegant simplification with ~200 lines.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.models import ExecutionMetrics


logger = logging.getLogger(__name__)


# Token cost assumptions (per 1K tokens)
# Dollars per 1K INPUT tokens. `CostTracker.track_experiment` computes
# `(tokens / 1000) * cost_per_1k`, so these MUST be per-1K, not per-MTok.
#
# Every entry here was previously the per-MILLION-token list price while the
# comments claimed per-1K — a silent 1000x overestimate on every model. The
# comments matching the code's unit is exactly what hid it: only the numbers
# were wrong. Measured before the fix: one 1M-token claude-3-sonnet experiment
# reported $3,000.00 against a $10 budget (true cost: $3.00), so any non-trivial
# run blew its budget on the first call and forced a downgrade.
#
# Anthropic rates verified 2026-08-30 against
# platform.claude.com/docs/en/about-claude/pricing.
DEFAULT_COSTS = {
    "ollama/phi3:mini": 0.0,  # Local = free
    "ollama/llama3.1:8b": 0.0,  # Local = free
    "ollama/qwen2.5:7b": 0.0,  # Local = free
    # Current Anthropic models ($/MTok input -> /1000).
    "anthropic/claude-opus-5": 0.005,  # $5 / MTok
    "anthropic/claude-opus-4-8": 0.005,  # $5 / MTok
    "anthropic/claude-sonnet-5": 0.002,  # $2 / MTok
    "anthropic/claude-sonnet-4-6": 0.003,  # $3 / MTok
    "anthropic/claude-haiku-4-5": 0.001,  # $1 / MTok
    # Retired, kept so historical experiment logs still price correctly.
    "anthropic/claude-3-haiku": 0.00025,  # $0.25 / MTok
    "anthropic/claude-3-sonnet": 0.003,  # $3 / MTok
    "openai/gpt-4o-mini": 0.00015,  # $0.15 / MTok
    "openai/gpt-4o": 0.0025,  # $2.50 / MTok
}

# Charged when a model is absent from the table. Deliberately NOT 0.0: this feeds
# a budget enforcer, and pricing an unknown model free means the limit never
# trips. Mirrors the conservative default in cost_optimization/cost_tracker.py,
# and sits above every current model's rate.
UNKNOWN_MODEL_COST_PER_1K = 0.015  # $15 / MTok


@dataclass
class CostBudget:
    """Budget configuration for research sessions."""

    max_cost_usd: float = 100.0  # Maximum cost per session
    max_tokens: int = 1_000_000  # Maximum tokens per session
    max_experiments: int = 100  # Maximum experiments
    warning_threshold: float = 0.8  # Warn at 80% of budget
    hard_limit: bool = True  # Hard stop at limit

    def __post_init__(self):
        """Validate budget parameters (Issue #6)."""
        if self.max_cost_usd <= 0:
            raise ValueError("max_cost_usd must be > 0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if self.max_experiments <= 0:
            raise ValueError("max_experiments must be > 0")
        if not (0.0 < self.warning_threshold <= 1.0):
            raise ValueError("warning_threshold must be between 0.0 and 1.0")

    def is_within_budget(
        self,
        current_cost: float,
        current_tokens: int,
        current_experiments: int,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if within budget.

        Args:
            current_cost: Current cost in USD
            current_tokens: Current token count
            current_experiments: Current experiment count

        Returns:
            (within_budget, status_info)
        """
        status = {
            "cost_ok": True,
            "tokens_ok": True,
            "experiments_ok": True,
            "cost_percent": current_cost / self.max_cost_usd,
            "token_percent": current_tokens / self.max_tokens,
            "warning_triggered": False,
        }

        # Check cost
        if current_cost >= self.max_cost_usd:
            status["cost_ok"] = False
            if self.hard_limit:
                return False, status

        # Check tokens
        if current_tokens >= self.max_tokens:
            status["tokens_ok"] = False
            if self.hard_limit:
                return False, status

        # Check experiments
        if current_experiments >= self.max_experiments:
            status["experiments_ok"] = False
            if self.hard_limit:
                return False, status

        # Check warning threshold
        if (
            status["cost_percent"] >= self.warning_threshold
            or status["token_percent"] >= self.warning_threshold
        ):
            status["warning_triggered"] = True

        return True, status


@dataclass
class ExperimentCost:
    """Cost tracking for a single experiment."""

    experiment_id: str
    timestamp: str
    tokens_used: int
    cost_usd: float
    model_used: str
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "timestamp": self.timestamp,
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "model_used": self.model_used,
            "duration_seconds": self.duration_seconds,
        }


class CostTracker:
    """Track costs across research sessions.

    Token-aware budgeting with per-experiment tracking.
    """

    def __init__(
        self,
        budget: CostBudget | None = None,
        costs_per_1k: dict[str, float] | None = None,
        log_file: Path | None = None,
    ):
        """Initialize cost tracker.

        Args:
            budget: Budget configuration
            costs_per_1k: Cost per 1K tokens per model
            log_file: Path to cost log
        """
        self.budget = budget or CostBudget()
        self.costs_per_1k = costs_per_1k or DEFAULT_COSTS.copy()
        self.log_file = log_file or Path("data/research/costs.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Running totals
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_experiments = 0
        self.experiment_costs: list[ExperimentCost] = []

    def calculate_cost(
        self,
        tokens: int,
        model: str = "ollama/phi3:mini",
    ) -> float:
        """Calculate cost for token usage.

        Args:
            tokens: Number of tokens
            model: Model used

        Returns:
            Cost in USD
        """
        cost_per_1k = self.costs_per_1k.get(model)
        if cost_per_1k is None:
            # Fail SAFE, not free. This value feeds a budget enforcer that decides
            # when to stop spending: pricing an unknown model at $0.00 means the
            # limit never trips, so an unrecognised model could run unbounded.
            # 0.015 ($15/MTok) matches the conservative default the sibling
            # SessionCostTracker already uses, and exceeds every current model.
            logger.warning(
                "No cost entry for %s — using the conservative default "
                "$%.5f per 1K tokens. Add it to DEFAULT_COSTS.",
                model,
                UNKNOWN_MODEL_COST_PER_1K,
            )
            cost_per_1k = UNKNOWN_MODEL_COST_PER_1K
        return (tokens / 1000) * cost_per_1k

    def record_experiment(
        self,
        experiment_id: str,
        metrics: ExecutionMetrics,
        model: str = "ollama/phi3:mini",
    ) -> ExperimentCost:
        """Record experiment cost.

        Args:
            experiment_id: Experiment identifier
            metrics: Execution metrics
            model: Model used

        Returns:
            Experiment cost record
        """
        tokens = metrics.total_tokens or metrics.prompt_tokens + metrics.completion_tokens
        cost = self.calculate_cost(tokens, model)

        experiment_cost = ExperimentCost(
            experiment_id=experiment_id,
            timestamp=datetime.now().isoformat(),
            tokens_used=tokens,
            cost_usd=cost,
            model_used=model,
            duration_seconds=metrics.duration_seconds,
        )

        # Update totals
        self.total_cost += cost
        self.total_tokens += tokens
        self.total_experiments += 1
        self.experiment_costs.append(experiment_cost)

        # Log to file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(experiment_cost.to_dict()) + "\n")

        logger.info(
            f"Experiment {experiment_id}: {tokens} tokens, ${cost:.6f} "
            f"(total: ${self.total_cost:.6f})"
        )

        return experiment_cost

    def check_budget(self) -> tuple[bool, dict[str, Any]]:
        """Check if within budget.

        Returns:
            (within_budget, status_info)
        """
        return self.budget.is_within_budget(
            self.total_cost,
            self.total_tokens,
            self.total_experiments,
        )

    def get_cost_report(self) -> dict[str, Any]:
        """Get comprehensive cost report.

        Returns:
            Cost report dictionary
        """
        within_budget, status = self.check_budget()

        # Calculate per-model costs
        model_costs: dict[str, dict[str, Any]] = {}
        for exp in self.experiment_costs:
            if exp.model_used not in model_costs:
                model_costs[exp.model_used] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "experiments": 0,
                }
            model_costs[exp.model_used]["tokens"] += exp.tokens_used
            model_costs[exp.model_used]["cost"] += exp.cost_usd
            model_costs[exp.model_used]["experiments"] += 1

        return {
            "total_cost_usd": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "total_experiments": self.total_experiments,
            "budget": {
                "max_cost_usd": self.budget.max_cost_usd,
                "max_tokens": self.budget.max_tokens,
                "max_experiments": self.budget.max_experiments,
            },
            "usage_percent": {
                "cost": round(self.total_cost / self.budget.max_cost_usd * 100, 2),
                "tokens": round(self.total_tokens / self.budget.max_tokens * 100, 2),
                "experiments": round(self.total_experiments / self.budget.max_experiments * 100, 2),
            },
            "within_budget": within_budget,
            "status": status,
            "per_model": model_costs,
            "avg_cost_per_experiment": round(self.total_cost / max(1, self.total_experiments), 6),
            "avg_tokens_per_experiment": round(
                self.total_tokens / max(1, self.total_experiments), 2
            ),
        }

    def get_experiment_costs(self) -> list[ExperimentCost]:
        """Get all experiment costs.

        Returns:
            List of experiment costs
        """
        return self.experiment_costs.copy()

    def export_costs_csv(self, path: Path) -> None:
        """Export costs to CSV.

        Args:
            path: Output CSV path
        """
        import csv

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "experiment_id",
                    "timestamp",
                    "tokens_used",
                    "cost_usd",
                    "model_used",
                    "duration_seconds",
                ]
            )
            for exp in self.experiment_costs:
                writer.writerow(
                    [
                        exp.experiment_id,
                        exp.timestamp,
                        exp.tokens_used,
                        exp.cost_usd,
                        exp.model_used,
                        exp.duration_seconds,
                    ]
                )

        logger.info(f"Cost data exported to {path}")


class CostAwareRouter:
    """Route experiments to models based on cost constraints.

    Automatically downgrades models when budget is tight.
    """

    def __init__(
        self,
        cost_tracker: CostTracker,
        cost_threshold: float = 0.9,
    ):
        """Initialize cost-aware router.

        Args:
            cost_tracker: Cost tracker instance
            cost_threshold: Threshold to switch to cheaper models
        """
        self.cost_tracker = cost_tracker
        self.cost_threshold = cost_threshold

        # Model tiers
        self.tiers = [
            ["ollama/phi3:mini"],  # Free tier
            ["ollama/llama3.1:8b", "ollama/qwen2.5:7b"],  # Local tier
            ["anthropic/claude-3-haiku", "openai/gpt-4o-mini"],  # Cheap API tier
            ["anthropic/claude-3-sonnet", "openai/gpt-4o"],  # Expensive tier
        ]

    def select_model(
        self,
        preferred_model: str,
        complexity: float = 0.5,
    ) -> str:
        """Select model based on cost constraints.

        Args:
            preferred_model: Preferred model
            complexity: Task complexity 0-1

        Returns:
            Selected model
        """
        # Check budget status
        _within_budget, status = self.cost_tracker.check_budget()
        cost_percent = status.get("cost_percent", 0.0)

        # If under threshold, use preferred
        if cost_percent < self.cost_threshold:
            return preferred_model

        # Find current tier
        current_tier = 0
        for i, tier in enumerate(self.tiers):
            if preferred_model in tier:
                current_tier = i
                break

        # Downgrade to cheaper tier
        if current_tier > 0:
            cheaper_tier = self.tiers[current_tier - 1]
            # Pick based on complexity
            if complexity > 0.7 and len(cheaper_tier) > 1:
                selected = cheaper_tier[1]  # More capable in tier
            else:
                selected = cheaper_tier[0]  # Cheapest in tier

            logger.warning(
                f"Budget at {cost_percent:.1%}, downgraded {preferred_model} to {selected}"
            )
            return selected

        return preferred_model  # Already at cheapest

    def should_continue(self) -> tuple[bool, str]:
        """Check if should continue experiments.

        Returns:
            (should_continue, reason)
        """
        within_budget, status = self.cost_tracker.check_budget()

        if not within_budget:
            if not status.get("cost_ok", True):
                return False, "Cost budget exceeded"
            if not status.get("tokens_ok", True):
                return False, "Token budget exceeded"
            if not status.get("experiments_ok", True):
                return False, "Experiment limit reached"

        if status.get("warning_triggered", False):
            return True, "Budget warning: consider reducing model cost"

        return True, "Within budget"


# Integration with ResearchAgent
def create_cost_tracker(
    max_cost: float = 100.0,
    max_tokens: int = 1_000_000,
    max_experiments: int = 100,
) -> CostTracker:
    """Factory for creating cost tracker.

    Args:
        max_cost: Maximum cost in USD
        max_tokens: Maximum tokens
        max_experiments: Maximum experiments

    Returns:
        Configured CostTracker
    """
    budget = CostBudget(
        max_cost_usd=max_cost,
        max_tokens=max_tokens,
        max_experiments=max_experiments,
    )
    return CostTracker(budget=budget)


def integrate_with_research_agent(agent: Any) -> CostTracker:
    """Integrate cost tracking with ResearchAgent.

    Args:
        agent: ResearchAgent instance

    Returns:
        Configured CostTracker
    """
    tracker = create_cost_tracker(
        max_cost=agent.config.max_experiments * 0.5,  # $0.50 per experiment
        max_experiments=agent.config.max_experiments,
    )

    # Store on agent
    agent.cost_tracker = tracker
    agent.cost_router = CostAwareRouter(tracker)

    logger.info(f"Cost tracking integrated: budget ${tracker.budget.max_cost_usd:.2f}")
    return tracker


# Cost optimization utilities
def estimate_experiment_cost(
    model: str,
    tokens: int = 1000,
    costs_per_1k: dict[str, float] | None = None,
) -> float:
    """Estimate cost for an experiment.

    Args:
        model: Model to use
        tokens: Expected tokens
        costs_per_1k: Cost per 1K tokens

    Returns:
        Estimated cost in USD
    """
    costs = costs_per_1k or DEFAULT_COSTS
    cost_per_1k = costs.get(model, 0.0)
    return (tokens / 1000) * cost_per_1k


def get_cheapest_model(models: list[str]) -> str:
    """Get cheapest model from list.

    Args:
        models: List of model names

    Returns:
        Cheapest model
    """
    return min(models, key=lambda m: DEFAULT_COSTS.get(m, float("inf")))


def calculate_session_budget(
    num_experiments: int,
    avg_tokens_per_experiment: int = 1000,
    model: str = "ollama/phi3:mini",
) -> dict[str, Any]:
    """Calculate expected budget for a session.

    Args:
        num_experiments: Number of experiments
        avg_tokens_per_experiment: Average tokens per experiment
        model: Default model

    Returns:
        Budget estimate
    """
    cost_per_exp = estimate_experiment_cost(model, avg_tokens_per_experiment)
    total_cost = cost_per_exp * num_experiments
    total_tokens = avg_tokens_per_experiment * num_experiments

    return {
        "num_experiments": num_experiments,
        "estimated_cost_usd": round(total_cost, 2),
        "estimated_tokens": total_tokens,
        "model": model,
        "cost_per_experiment": round(cost_per_exp, 4),
        "recommendation": "OK" if total_cost < 50 else "Consider cheaper model",
    }
