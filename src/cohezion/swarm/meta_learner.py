"""MetaLearner - Recursive self-improvement layer for AGI.

Optimizes the learning strategies of base learners by analyzing
improvement history and suggesting algorithmic changes.
"""

import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class LearningStrategy:
    """A learning strategy that can be evaluated and optimized."""

    name: str
    parameters: dict[str, Any]
    success_rate: float = 0.0
    samples_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parameters": self.parameters,
            "success_rate": self.success_rate,
            "samples_count": self.samples_count,
            "last_updated": self.last_updated,
        }


@dataclass
class MetaLearningRecord:
    """Record of a meta-learning intervention."""

    timestamp: str
    base_learner: str
    previous_strategy: str
    new_strategy: str
    reason: str
    expected_improvement: float
    actual_improvement: float | None = None
    validated: bool = False


class MetaLearner:
    """Learns how to learn - optimizes learning strategies."""

    def __init__(
        self,
        base_learner: Any,
        strategy_pool: list[LearningStrategy] | None = None,
        data_path: Path | None = None,
    ):
        self.base_learner = base_learner
        self.strategy_pool = strategy_pool or self._default_strategies()
        self.current_strategy: LearningStrategy | None = None
        self.learning_history: list[dict[str, Any]] = []
        self.meta_interventions: list[MetaLearningRecord] = []

        self.data_path = data_path or Path("~/.config/cohezion/meta_learner.jsonl").expanduser()
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        self._load_history()
        self._initialize_strategy()

    def _default_strategies(self) -> list[LearningStrategy]:
        """Default pool of learning strategies."""
        return [
            LearningStrategy(
                name="pattern_matching",
                parameters={"threshold": 0.7, "max_patterns": 50},
                success_rate=0.75,
            ),
            LearningStrategy(
                name="statistical_learning",
                parameters={"confidence_level": 0.95, "min_samples": 10},
                success_rate=0.80,
            ),
            LearningStrategy(
                name="adaptive_threshold",
                parameters={"initial_threshold": 0.8, "adaptation_rate": 0.1},
                success_rate=0.78,
            ),
            LearningStrategy(
                name="ensemble_learning",
                parameters={"num_learners": 3, "voting": "soft"},
                success_rate=0.82,
            ),
        ]

    def _initialize_strategy(self):
        """Initialize with best strategy from pool."""
        if not self.strategy_pool:
            return

        # Sort by success rate
        self.strategy_pool.sort(key=lambda s: s.success_rate, reverse=True)
        self.current_strategy = self.strategy_pool[0]

        logger.info(f"MetaLearner initialized with strategy: {self.current_strategy.name}")

    def meta_optimize(self) -> MetaLearningRecord | None:
        """Optimize the base learner's learning strategy.

        Analyzes base learner performance and suggests/generates
        improved learning strategies.

        Returns:
            MetaLearningRecord if optimization occurred, None otherwise
        """
        # Calculate current base learner success rate
        current_success = self._calculate_base_success_rate()

        # If success rate is good, no need to optimize
        if current_success >= 0.85:
            logger.debug(
                f"Base learner success rate {current_success:.2%} - no optimization needed"
            )
            return None

        # Find better strategy from pool
        better_strategy = self._find_better_strategy(current_success)

        if better_strategy:
            # Record the intervention
            record = MetaLearningRecord(
                timestamp=datetime.now().isoformat(),
                base_learner=self.base_learner.__class__.__name__,
                previous_strategy=self.current_strategy.name if self.current_strategy else "None",
                new_strategy=better_strategy.name,
                reason=f"Base success rate {current_success:.2%} below threshold 85%",
                expected_improvement=better_strategy.success_rate - current_success,
            )

            # Apply the new strategy
            self._apply_strategy(better_strategy)

            # Save and log
            self.meta_interventions.append(record)
            self._save_history()

            logger.info(
                f"Meta-optimization applied: {record.previous_strategy} -> {record.new_strategy}"
            )
            logger.info(f"Expected improvement: {record.expected_improvement:.2%}")

            return record

        # If no better strategy in pool, try to generate one
        new_strategy = self._generate_new_strategy()
        if new_strategy:
            record = MetaLearningRecord(
                timestamp=datetime.now().isoformat(),
                base_learner=self.base_learner.__class__.__name__,
                previous_strategy=self.current_strategy.name if self.current_strategy else "None",
                new_strategy=new_strategy.name,
                reason=f"Generated new strategy for {current_success:.2%} success rate",
                expected_improvement=0.1,  # Conservative estimate
            )

            self._apply_strategy(new_strategy)
            self.strategy_pool.append(new_strategy)
            self.meta_interventions.append(record)
            self._save_history()

            logger.info(f"Generated and applied new strategy: {new_strategy.name}")

            return record

        return None

    def _calculate_base_success_rate(self) -> float:
        """Calculate current success rate of base learner."""
        if not hasattr(self.base_learner, "improvement_history"):
            return 0.0

        history = self.base_learner.improvement_history
        if not history:
            return 0.0

        # Look at recent performance
        recent = history[-20:] if len(history) >= 20 else history

        successes = sum(1 for h in recent if h.get("success", False))
        return successes / len(recent) if recent else 0.0

    def _find_better_strategy(self, current_success: float) -> LearningStrategy | None:
        """Find a strategy with better expected success rate."""
        if not self.current_strategy:
            return self.strategy_pool[0] if self.strategy_pool else None

        # Find strategies better than current
        for strategy in self.strategy_pool:
            if strategy.success_rate > current_success + 0.05:  # Need 5% improvement
                return strategy

        return None

    def _generate_new_strategy(self) -> LearningStrategy | None:
        """Generate a new learning strategy based on analysis."""
        if not self.current_strategy:
            return None

        _current_success = self._calculate_base_success_rate()

        # Analyze what has worked in history
        successful_patterns = self._extract_successful_patterns()

        if not successful_patterns:
            return None

        # Create new strategy combining successful elements
        new_params = self.current_strategy.parameters.copy()

        # Adapt parameters based on success patterns
        if "threshold" in new_params:
            # If high threshold had low success, try lower
            new_params["threshold"] = max(0.5, new_params["threshold"] - 0.1)

        if "adaptation_rate" in new_params:
            # Faster adaptation if struggling
            new_params["adaptation_rate"] = min(0.3, new_params["adaptation_rate"] * 1.5)

        return LearningStrategy(
            name=f"generated_{len(self.strategy_pool)}",
            parameters=new_params,
            success_rate=self.current_strategy.success_rate + 0.05,
        )

    def _extract_successful_patterns(self) -> list[dict[str, Any]]:
        """Extract patterns from successful learning attempts."""
        if not self.learning_history:
            return []

        successful = [h for h in self.learning_history if h.get("success", False)]
        return successful

    def _apply_strategy(self, strategy: LearningStrategy):
        """Apply a learning strategy to the base learner."""
        self.current_strategy = strategy

        # Update base learner if it supports strategy updates
        if hasattr(self.base_learner, "set_learning_strategy"):
            self.base_learner.set_learning_strategy(strategy.parameters)

        logger.info(f"Applied learning strategy: {strategy.name}")

    def record_learning_outcome(self, success: bool, details: dict[str, Any]):
        """Record outcome of a learning attempt."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "strategy": self.current_strategy.name if self.current_strategy else "None",
            "details": details,
        }

        self.learning_history.append(record)

        # Update strategy success rate
        if self.current_strategy:
            self._update_strategy_stats(self.current_strategy, success)

        self._save_history()

    def _update_strategy_stats(self, strategy: LearningStrategy, success: bool):
        """Update success statistics for a strategy."""
        strategy.samples_count += 1

        # Running average
        current = strategy.success_rate
        n = strategy.samples_count
        new_success = 1.0 if success else 0.0
        strategy.success_rate = (current * (n - 1) + new_success) / n

        strategy.last_updated = datetime.now().isoformat()

    def get_optimization_report(self) -> dict[str, Any]:
        """Get report on meta-learning activities."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_interventions": len(self.meta_interventions),
            "current_strategy": self.current_strategy.name if self.current_strategy else "None",
            "strategy_pool_size": len(self.strategy_pool),
            "avg_strategy_success": statistics.mean(s.success_rate for s in self.strategy_pool)
            if self.strategy_pool
            else 0.0,
            "recent_interventions": [
                {
                    "timestamp": r.timestamp,
                    "from": r.previous_strategy,
                    "to": r.new_strategy,
                    "expected": r.expected_improvement,
                }
                for r in self.meta_interventions[-5:]
            ],
            "learning_history_size": len(self.learning_history),
        }

    def _load_history(self):
        """Load meta-learning history from disk."""
        if not self.data_path.exists():
            return

        try:
            with open(self.data_path) as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("type") == "intervention":
                        self.meta_interventions.append(MetaLearningRecord(**data["record"]))
                    elif data.get("type") == "learning":
                        self.learning_history.append(data["record"])
        except Exception as e:
            logger.warning(f"Failed to load meta-learning history: {e}")

    def _save_history(self):
        """Save meta-learning history to disk."""
        records = []

        for intervention in self.meta_interventions:
            records.append({"type": "intervention", "record": intervention.__dict__})

        for learning in self.learning_history:
            records.append({"type": "learning", "record": learning})

        with open(self.data_path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")


def demo_meta_learner():
    """Demonstrate meta-learner functionality."""
    print("=" * 70)
    print("METALEARNER DEMONSTRATION")
    print("=" * 70)

    # Create a mock base learner
    class MockLearner:
        def __init__(self):
            self.improvement_history = []
            self.current_strategy = None

        def set_learning_strategy(self, params):
            print(f"  Base learner: Strategy updated to {params}")

    base = MockLearner()

    # Add some history
    for i in range(30):
        base.improvement_history.append(
            {
                "success": i % 3 != 0,  # 66% success rate
                "iteration": i,
            }
        )

    # Create meta-learner
    meta = MetaLearner(base)

    print("\nInitial state:")
    print(f"  Base success rate: {meta._calculate_base_success_rate():.2%}")
    print(f"  Current strategy: {meta.current_strategy.name}")

    # Try to optimize
    print("\nMeta-optimization:")
    result = meta.meta_optimize()

    if result:
        print("  ✅ Optimization applied!")
        print(f"     From: {result.previous_strategy}")
        print(f"     To: {result.new_strategy}")
        print(f"     Expected improvement: {result.expected_improvement:.2%}")
    else:
        print("  ℹ No optimization needed (success rate sufficient)")

    # Report
    print("\nMeta-Learning Report:")
    report = meta.get_optimization_report()
    print(f"  Total interventions: {report['total_interventions']}")
    print(f"  Strategy pool size: {report['strategy_pool_size']}")

    print("\n" + "=" * 70)
    print("✅ METALEARNER DEMONSTRATION COMPLETE")
    print("=" * 70)

    return meta


if __name__ == "__main__":
    demo_meta_learner()
