"""Compound integration for FLUME journey benchmarks.

Provides BenchmarkSessionManager and SelfImprovingBenchmarkLoop for integrating
FLUME benchmarks with the Cohezion compound engineering framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.benchmarks.benchmark_suite import BenchmarkSuite, Policy
    from cohezion.eval.capability_scorecard import CapabilityScorecard


class CurriculumState(Enum):
    """Curriculum progression states."""

    INITIAL = auto()
    WARMING = auto()
    IMPROVING = auto()
    PLATEAUED = auto()
    MASTERED = auto()


@dataclass
class BenchmarkSessionManager:
    """Manages FLUME benchmark sessions with vault persistence.

    Coordinates benchmark execution, scorecard tracking, and checkpoint
    persistence through the compound session lifecycle.
    """

    scorecard: CapabilityScorecard | None = None
    run_history: dict[str, Any] = field(default_factory=dict)
    _current_run_id: str | None = None

    def start_session(self, run_id: str | None = None) -> str:
        """Start a new benchmark session.

        Args:
            run_id: Optional run ID. Auto-generated if not provided.

        Returns:
            The run ID for this session.
        """
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        self._current_run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.scorecard = CapabilityScorecard()
        return self._current_run_id

    def record_episode(
        self,
        episode_id: int,
        coherence: float,
        reward: float,
        success: bool,
        biography: list[dict[str, Any]],
    ) -> None:
        """Record a single episode result.

        Args:
            episode_id: Episode number.
            coherence: Mean coherence for episode.
            reward: Total reward for episode.
            success: Whether task succeeded.
            biography: EVO biography from episode.
        """
        if self.scorecard is None:
            msg = "Session not started. Call start_session() first."
            raise RuntimeError(msg)

        self.scorecard.record_run(
            run_id=f"{self._current_run_id}_ep{episode_id}",
            episodes=[{"coherence": coherence, "reward": reward, "success": success}],
            biographies=biography,
        )

    def end_session(self) -> dict[str, Any]:
        """End the current session and return summary.

        Returns:
            Session summary with final scores and trends.
        """
        if self.scorecard is None:
            msg = "Session not started. Call start_session() first."
            raise RuntimeError(msg)

        report = self.scorecard.generate_report()
        return {
            "run_id": self._current_run_id,
            "completed_at": datetime.now().isoformat(),
            "report": report,
        }


@dataclass
class SelfImprovingBenchmarkLoop:
    """Autonomous benchmark loop with curriculum-based skill refinement.

    Implements a closed-loop improvement cycle:
        1. Run benchmarks at current difficulty
        2. Analyze weakest capability axis
        3. Adjust curriculum (easier/harder tasks)
        4. Refine via compound execution guidance
        5. Repeat until mastered
    """

    suite: BenchmarkSuite
    session_manager: BenchmarkSessionManager
    curriculum_state: CurriculumState = CurriculumState.INITIAL
    difficulty_weights: dict[str, float] = field(
        default_factory=lambda: {
            "easy": 0.3,
            "medium": 0.4,
            "hard": 0.3,
        }
    )
    weak_threshold: float = 0.5
    strong_threshold: float = 0.8
    max_iterations: int = 100

    def run_iteration(
        self,
        policy: Policy,
        num_episodes: int = 10,
    ) -> dict[str, Any]:
        """Run one iteration of the improvement loop.

        Args:
            policy: Policy to evaluate.
            num_episodes: Episodes per task.

        Returns:
            Iteration results with scores and recommendations.
        """
        from cohezion.eval.capability_scorecard import LongitudinalTracker

        results = self.suite.run(
            policy=policy,
            tasks=self._select_tasks(),
            num_episodes=num_episodes,
        )

        tracker = LongitudinalTracker()
        for task_name, task_result in results.items():
            tracker.record(
                run_id=task_name,
                scores={
                    "coherence": task_result.mean_coherence,
                    "success_rate": task_result.success_rate,
                },
            )

        weakest = tracker.get_weakest_axis()
        strongest = tracker.get_strongest_axis()

        curriculum_changed = self._update_curriculum(weakest, strongest)

        return {
            "results": results,
            "weakest_axis": weakest,
            "strongest_axis": strongest,
            "curriculum_state": self.curriculum_state,
            "curriculum_changed": curriculum_changed,
            "difficulty_weights": self.difficulty_weights.copy(),
        }

    def _select_tasks(self) -> list[str]:
        """Select tasks based on current difficulty weights.

        Returns:
            List of task names to evaluate.
        """
        all_tasks = list(self.suite._tasks.keys())
        selected = []

        for difficulty, weight in self.difficulty_weights.items():
            count = max(1, int(len(all_tasks) * weight))
            difficulty_tasks = [t for t in all_tasks if difficulty in t.lower()]
            selected.extend(difficulty_tasks[:count])

        return selected

    def _update_curriculum(
        self,
        weakest: str | None,
        strongest: str | None,
    ) -> bool:
        """Update curriculum based on performance.

        Args:
            weakest: Name of weakest capability axis.
            strongest: Name of strongest capability axis.

        Returns:
            True if curriculum was changed.
        """
        if weakest is None or strongest is None:
            return False

        changed = False

        if weakest == "coherence" and self.difficulty_weights["easy"] < 0.5:
            self.difficulty_weights["easy"] += 0.1
            self.difficulty_weights["hard"] = max(0.1, self.difficulty_weights["hard"] - 0.1)
            changed = True
            self.curriculum_state = CurriculumState.IMPROVING

        elif strongest == "coherence" and self.difficulty_weights["hard"] < 0.5:
            self.difficulty_weights["hard"] += 0.1
            self.difficulty_weights["easy"] = max(0.1, self.difficulty_weights["easy"] - 0.1)
            changed = True

        total = sum(self.difficulty_weights.values())
        for k in self.difficulty_weights:
            self.difficulty_weights[k] /= total

        return changed

    async def run_until_mastered(
        self,
        policy: Policy,
        num_episodes: int = 10,
    ) -> dict[str, Any]:
        """Run improvement loop until curriculum is mastered.

        Args:
            policy: Policy to evaluate.
            num_episodes: Episodes per task per iteration.

        Returns:
            Final results with all iterations.
        """
        iterations = []

        for _i in range(self.max_iterations):
            result = self.run_iteration(policy, num_episodes)
            iterations.append(result)

            if self.curriculum_state == CurriculumState.MASTERED:
                break

        return {
            "total_iterations": len(iterations),
            "final_state": self.curriculum_state,
            "iterations": iterations,
        }
