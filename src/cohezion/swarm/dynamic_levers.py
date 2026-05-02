"""Dynamic levers - tunable parameters for system optimization.

Provides configurable parameters with:
- Clear goal definitions
- Measurable metrics
- Safe adjustment ranges
- Automatic guards
- Persistence

Levers can be "pushed" (increase) or "pulled" (decrease) to optimize
toward specific goals.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class LeverGoal:
    """Goal definition for a lever."""

    target_value: float
    tolerance: float = 0.1  # ±10%
    optimize_direction: str = "maximize"  # or "minimize"

    def is_achieved(self, current: float) -> bool:
        """Check if goal is achieved."""
        if self.optimize_direction == "maximize":
            return current >= self.target_value * (1 - self.tolerance)
        else:
            return current <= self.target_value * (1 + self.tolerance)


@dataclass
class LeverRange:
    """Safe adjustment range for a lever."""

    min_value: float
    max_value: float
    default_value: float
    step_size: float = 0.1

    def clamp(self, value: float) -> float:
        """Clamp value to safe range."""
        return max(self.min_value, min(self.max_value, value))

    def validate(self, value: float) -> tuple[bool, str]:
        """Validate value is in range."""
        if value < self.min_value:
            return False, f"Value {value} below minimum {self.min_value}"
        if value > self.max_value:
            return False, f"Value {value} above maximum {self.max_value}"
        return True, "OK"


@dataclass
class DynamicLever:
    """A tunable parameter with goals, metrics, and safety guards."""

    name: str
    description: str
    current_value: float
    range: LeverRange
    goal: LeverGoal | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    last_adjusted: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    adjustment_history: list[dict[str, Any]] = field(default_factory=list)

    def push(self, amount: float | None = None) -> float:
        """Increase lever value (toward max).

        Args:
            amount: Amount to increase (default: step_size)

        Returns:
            New value
        """
        step = amount or self.range.step_size
        new_value = self.range.clamp(self.current_value + step)

        self._record_adjustment("push", step, new_value)
        self.current_value = new_value

        logger.info(f"Lever '{self.name}': PUSH +{step} → {new_value}")
        return new_value

    def pull(self, amount: float | None = None) -> float:
        """Decrease lever value (toward min).

        Args:
            amount: Amount to decrease (default: step_size)

        Returns:
            New value
        """
        step = amount or self.range.step_size
        new_value = self.range.clamp(self.current_value - step)

        self._record_adjustment("pull", step, new_value)
        self.current_value = new_value

        logger.info(f"Lever '{self.name}': PULL -{step} → {new_value}")
        return new_value

    def set(self, value: float) -> tuple[bool, str]:
        """Set lever to specific value (with validation).

        Args:
            value: Target value

        Returns:
            (success, message)
        """
        valid, msg = self.range.validate(value)
        if not valid:
            logger.warning(f"Lever '{self.name}': Invalid value {value} - {msg}")
            return False, msg

        old_value = self.current_value
        self.current_value = value
        self._record_adjustment("set", value - old_value, value)

        logger.info(f"Lever '{self.name}': SET {old_value} → {value}")
        return True, "OK"

    def reset(self) -> float:
        """Reset to default value."""
        old_value = self.current_value
        self.current_value = self.range.default_value
        self._record_adjustment(
            "reset", self.range.default_value - old_value, self.range.default_value
        )

        logger.info(f"Lever '{self.name}': RESET → {self.range.default_value}")
        return self.range.default_value

    def _record_adjustment(self, action: str, delta: float, new_value: float):
        """Record adjustment in history."""
        self.adjustment_history.append(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "action": action,
                "delta": delta,
                "new_value": new_value,
                "metrics_snapshot": self.metrics.copy(),
            }
        )
        self.last_adjusted = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def update_metric(self, name: str, value: float):
        """Update a metric for this lever."""
        self.metrics[name] = value

    def get_progress_toward_goal(self) -> float | None:
        """Get progress toward goal (0-1, or None if no goal)."""
        if not self.goal:
            return None

        metric_value = self.metrics.get("current", self.current_value)

        if self.goal.optimize_direction == "maximize":
            if metric_value >= self.goal.target_value:
                return 1.0
            return metric_value / self.goal.target_value
        else:
            if metric_value <= self.goal.target_value:
                return 1.0
            return self.goal.target_value / metric_value

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "current_value": self.current_value,
            "range": asdict(self.range),
            "goal": asdict(self.goal) if self.goal else None,
            "metrics": self.metrics,
            "last_adjusted": self.last_adjusted,
            "progress": self.get_progress_toward_goal(),
        }


class DynamicLeverSystem:
    """System of dynamic levers for optimization."""

    def __init__(self, config_path: Path | None = None):
        self.levers: dict[str, DynamicLever] = {}
        self.config_path = (
            config_path or Path("~/.config/cohezion/dynamic_levers.json").expanduser()
        )
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize with predefined levers
        self._initialize_default_levers()

    def _initialize_default_levers(self):
        """Initialize system with default levers."""

        # Lever 1: Deterministic Ratio
        self.add_lever(
            DynamicLever(
                name="deterministic_ratio",
                description="Ratio of deterministic parsing vs heuristic fallback",
                current_value=0.081,  # Current 8.1%
                range=LeverRange(
                    min_value=0.0,
                    max_value=1.0,
                    default_value=0.80,  # Target 80%
                    step_size=0.05,
                ),
                goal=LeverGoal(target_value=0.80, tolerance=0.10, optimize_direction="maximize"),
            )
        )

        # Lever 2: Heuristic Confidence Threshold
        self.add_lever(
            DynamicLever(
                name="heuristic_confidence_threshold",
                description="Minimum confidence to trust heuristic parsing",
                current_value=0.70,
                range=LeverRange(min_value=0.0, max_value=1.0, default_value=0.70, step_size=0.05),
                goal=LeverGoal(target_value=0.85, tolerance=0.05, optimize_direction="maximize"),
            )
        )

        # Lever 3: Discovery Timeout
        self.add_lever(
            DynamicLever(
                name="discovery_timeout_seconds",
                description="Timeout for model discovery operations",
                current_value=10.0,
                range=LeverRange(min_value=1.0, max_value=60.0, default_value=10.0, step_size=5.0),
                goal=LeverGoal(
                    target_value=5.0,  # Faster discovery
                    tolerance=0.50,
                    optimize_direction="minimize",
                ),
            )
        )

        # Lever 4: Validation Sample Size
        self.add_lever(
            DynamicLever(
                name="validation_sample_size",
                description="Number of models to validate with inference",
                current_value=0.0,  # Currently no validation
                range=LeverRange(min_value=0.0, max_value=50.0, default_value=10.0, step_size=5.0),
                goal=LeverGoal(target_value=10.0, tolerance=0.20, optimize_direction="maximize"),
            )
        )

        # Lever 5: Memory Safety Threshold
        self.add_lever(
            DynamicLever(
                name="memory_safety_threshold_percent",
                description="Max system memory % before stopping operations",
                current_value=70.0,
                range=LeverRange(min_value=50.0, max_value=90.0, default_value=70.0, step_size=5.0),
                goal=LeverGoal(
                    target_value=80.0,  # Higher threshold (more headroom)
                    tolerance=0.10,
                    optimize_direction="maximize",
                ),
            )
        )

        # Lever 6: Capability Validation
        self.add_lever(
            DynamicLever(
                name="capability_validation_enabled",
                description="Enable inference-based capability validation",
                current_value=0.0,  # 0 or 1 (disabled)
                range=LeverRange(min_value=0.0, max_value=1.0, default_value=0.0, step_size=1.0),
                goal=LeverGoal(
                    target_value=1.0,  # Enable validation
                    tolerance=0.0,
                    optimize_direction="maximize",
                ),
            )
        )

        # Lever 7: Parallel Discovery Workers
        self.add_lever(
            DynamicLever(
                name="parallel_discovery_workers",
                description="Number of parallel workers for discovery",
                current_value=1.0,
                range=LeverRange(min_value=1.0, max_value=8.0, default_value=1.0, step_size=1.0),
                goal=LeverGoal(
                    target_value=4.0,  # Balance speed vs resource
                    tolerance=0.25,
                    optimize_direction="maximize",
                ),
            )
        )

        # Lever 8: Heuristic Fallback Limit
        self.add_lever(
            DynamicLever(
                name="max_heuristic_fallbacks",
                description="Maximum allowed heuristic fallbacks per session",
                current_value=10.0,
                range=LeverRange(min_value=0.0, max_value=100.0, default_value=10.0, step_size=5.0),
                goal=LeverGoal(
                    target_value=0.0,  # Zero fallbacks (pure deterministic)
                    tolerance=0.10,
                    optimize_direction="minimize",
                ),
            )
        )

    def add_lever(self, lever: DynamicLever):
        """Add a lever to the system."""
        self.levers[lever.name] = lever
        logger.debug(f"Added lever: {lever.name}")

    def get_lever(self, name: str) -> DynamicLever | None:
        """Get a lever by name."""
        return self.levers.get(name)

    def push(self, name: str, amount: float | None = None) -> float | None:
        """Push (increase) a lever."""
        lever = self.get_lever(name)
        if not lever:
            logger.error(f"Lever '{name}' not found")
            return None
        return lever.push(amount)

    def pull(self, name: str, amount: float | None = None) -> float | None:
        """Pull (decrease) a lever."""
        lever = self.get_lever(name)
        if not lever:
            logger.error(f"Lever '{name}' not found")
            return None
        return lever.pull(amount)

    def set(self, name: str, value: float) -> bool:
        """Set a lever to specific value."""
        lever = self.get_lever(name)
        if not lever:
            logger.error(f"Lever '{name}' not found")
            return False
        success, _ = lever.set(value)
        return success

    def get_dashboard(self) -> dict[str, Any]:
        """Get system dashboard view."""
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_levers": len(self.levers),
            "levers": {name: lever.to_dict() for name, lever in self.levers.items()},
            "goals_achieved": sum(
                1 for l in self.levers.values() if l.goal and l.get_progress_toward_goal() == 1.0
            ),
            "goals_in_progress": sum(
                1
                for l in self.levers.values()
                if l.goal
                and l.get_progress_toward_goal() is not None
                and l.get_progress_toward_goal() < 1.0
            ),
        }

    def print_dashboard(self):
        """Print visual dashboard."""
        dashboard = self.get_dashboard()

        print("\n" + "=" * 70)
        print("DYNAMIC LEVER SYSTEM DASHBOARD")
        print("=" * 70)
        print(f"Timestamp: {dashboard['timestamp']}")
        print(f"Total Levers: {dashboard['total_levers']}")
        print(f"Goals Achieved: {dashboard['goals_achieved']}")
        print(f"Goals In Progress: {dashboard['goals_in_progress']}")

        print("\n" + "-" * 70)
        print("LEVERS:")
        print("-" * 70)

        for name, data in dashboard["levers"].items():
            value = data["current_value"]
            goal = data["goal"]
            progress = data.get("progress")

            if goal:
                target = goal["target_value"]
                bar = self._progress_bar(progress or 0)
                print(f"  {name:40} | {value:6.2f} / {target:6.2f} | {bar}")
            else:
                print(f"  {name:40} | {value:6.2f} | (no goal)")

        print("=" * 70)

    def _progress_bar(self, progress: float, width: int = 20) -> str:
        """Generate ASCII progress bar."""
        filled = int(width * min(progress, 1.0))
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {progress:.0%}"

    def save(self):
        """Persist lever state."""
        data = {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "levers": {name: lever.to_dict() for name, lever in self.levers.items()},
        }
        self.config_path.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved lever state to {self.config_path}")

    def load(self):
        """Load lever state."""
        if not self.config_path.exists():
            logger.info("No saved lever state found")
            return

        try:
            data = json.loads(self.config_path.read_text())
            for name, lever_data in data.get("levers", {}).items():
                if name in self.levers:
                    # Update current values
                    self.levers[name].current_value = lever_data.get(
                        "current_value", self.levers[name].current_value
                    )
                    self.levers[name].metrics = lever_data.get("metrics", {})

            logger.info(f"Loaded lever state from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load lever state: {e}")

    def optimize_all(self):
        """Auto-optimize all levers toward goals."""
        print("\n🎯 Optimizing all levers toward goals...")

        for name, lever in self.levers.items():
            if not lever.goal:
                continue

            progress = lever.get_progress_toward_goal()
            if progress is None:
                continue

            if progress >= 1.0:
                print(f"  ✓ {name}: Goal achieved ({progress:.0%})")
                continue

            if lever.goal.optimize_direction == "maximize":
                if progress < 0.5:
                    lever.push(lever.range.step_size * 2)  # Push harder
                    print(f"  ↑ {name}: Pushed aggressively ({progress:.0%} → goal)")
                else:
                    lever.push()
                    print(f"  ↑ {name}: Pushed ({progress:.0%} → goal)")
            else:
                if progress < 0.5:
                    lever.pull(lever.range.step_size * 2)  # Pull harder
                    print(f"  ↓ {name}: Pulled aggressively ({progress:.0%} → goal)")
                else:
                    lever.pull()
                    print(f"  ↓ {name}: Pulled ({progress:.0%} → goal)")

        self.save()


# Convenience functions


def create_default_lever_system() -> DynamicLeverSystem:
    """Create system with default levers."""
    system = DynamicLeverSystem()
    system.load()  # Load saved state if exists
    return system


def demo_levers():
    """Demonstrate lever system."""
    print("=" * 70)
    print("DYNAMIC LEVER SYSTEM DEMO")
    print("=" * 70)

    system = create_default_lever_system()

    # Show initial state
    system.print_dashboard()

    # Demonstrate push/pull
    print("\n🔧 Adjusting levers...")

    # Push deterministic ratio (increase)
    system.push("deterministic_ratio", 0.2)

    # Pull timeout (decrease)
    system.pull("discovery_timeout_seconds", 5.0)

    # Enable capability validation
    system.set("capability_validation_enabled", 1.0)

    # Show updated state
    print("\n" + "=" * 70)
    print("AFTER ADJUSTMENTS:")
    print("=" * 70)
    system.print_dashboard()

    # Save
    system.save()


if __name__ == "__main__":
    demo_levers()
