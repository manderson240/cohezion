"""Compound engineering integration for FLUME journey benchmarks.

Provides:
1. BenchmarkSessionManager — EvalPipeline wrapped in CompoundSessionManager
   for warm-start cache + checkpoint persistence
2. SelfImprovingBenchmarkLoop — Closed-loop feedback: scorecard weak axis
   → task curriculum oversampling → refined benchmark runs

Integration 1: EvalPipeline ↔ CompoundSessionManager
    Wraps RalphLoop iterations inside CompoundSessionManager lifecycle.
    On start: warm cache, restore PPOTrainer checkpoint, restore metrics.
    On end: persist cache, save PPOTrainer checkpoint, persist metrics.

Integration 2: EVO Biography → Vault MCP
    After each episode, JourneyTracker records EVO physics trajectory.
    MCP tools (vault_write) persist biographies to SurrealDB.

Integration 3: Weak-Axis Curriculum
    CapabilityScorecard identifies weakest axis.
    SkillRefiner oversamples TaskSpecs targeting that axis.
    TaskGenerator filters to relevant archetype/difficulty.

Example:
    # Integration 1: Session-wrapped benchmark
    mgr = BenchmarkSessionManager()
    summary = mgr.start_session()
    scorecard = mgr.run_benchmark(policy, n_episodes=100)
    mgr.end_session()

    # Integration 3: Self-improving loop
    loop = SelfImprovingBenchmarkLoop()
    for iteration in loop.iterate(policy):
        scorecard = iteration.run()
        iteration.record(scorecard)
        if iteration.converged():
            break
        iteration.update_curriculum()
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSessionSummary:
    """Summary of a benchmark session."""

    session_id: str
    episodes_completed: int
    total_duration_seconds: float
    cache_entries_loaded: int
    cache_entries_saved: int
    metrics_restored: bool
    metrics_saved: bool
    scorecard_snapshot: dict[str, Any]


class BenchmarkSessionManager:
    """CompoundSessionManager extended for RL benchmark workloads.

    Adds:
    - PPOTrainer checkpoint persistence across sessions
    - Benchmark metrics collection (distinct from compound metrics)
    - EvalPipeline integration with warm-start/clean-shutdown

    Example:
        mgr = BenchmarkSessionManager()
        summary = mgr.start_session()
        scorecard = mgr.run_benchmark(trainer, n_episodes=100)
        summary = mgr.end_session()
        print(f"Ran {summary.episodes_completed} episodes in {summary.total_duration_seconds:.1f}s")
    """

    _sessions: dict[str, BenchmarkSessionManager] = {}

    def __init__(self) -> None:
        self._session_id: str = ""
        self._start_time: float = 0.0
        self._cache_loaded: int = 0
        self._cache_saved: int = 0
        self._metrics_restored: bool = False
        self._metrics_saved: bool = False
        self._latest_scorecard: dict[str, Any] | None = None
        self._trainer_checkpoint_path: Path | None = None

    def start_session(
        self,
        max_cache_entries: int = 256,
        trainer_checkpoint_path: Path | str | None = None,
    ) -> BenchmarkSessionSummary:
        """Start benchmark session: warm cache + restore trainer checkpoint.

        Args:
            max_cache_entries: Maximum cache entries to restore.
            trainer_checkpoint_path: Optional path to PPOTrainer checkpoint
                for warm-start training.

        Returns:
            BenchmarkSessionSummary with warm-start state.
        """
        self._session_id = f"bench_{uuid.uuid4().hex[:8]}"
        self._start_time = time.time()

        if trainer_checkpoint_path is not None:
            self._trainer_checkpoint_path = Path(trainer_checkpoint_path)

        self._warm_cache(max_cache_entries)
        self._restore_metrics()
        self._restore_trainer_checkpoint()

        BenchmarkSessionManager._sessions[self._session_id] = self

        return BenchmarkSessionSummary(
            session_id=self._session_id,
            episodes_completed=0,
            total_duration_seconds=0.0,
            cache_entries_loaded=self._cache_loaded,
            cache_entries_saved=0,
            metrics_restored=self._metrics_restored,
            metrics_saved=False,
            scorecard_snapshot={},
        )

    def _warm_cache(self, max_entries: int) -> None:
        """Warm the L1/L2/L3 semantic cache from persistence."""
        try:
            from cohezion.compound.cache_persistence import WarmCacheLoader

            try:
                from cohezion.swarm.compound_client import get_compound_client

                client = get_compound_client()
                loader = WarmCacheLoader()
                self._cache_loaded = loader.warm_client(client, max_entries)
                logger.info(f"Cache warmed: {self._cache_loaded} entries")
            except Exception:
                logger.debug("Compound client unavailable for cache warm")
                self._cache_loaded = 0
        except ImportError:
            self._cache_loaded = 0

    def _restore_metrics(self) -> None:
        """Restore compound metrics from persistence."""
        try:
            from cohezion.compound.metrics_persistence import MetricsPersistence

            try:
                from cohezion.compound.metrics import get_collector

                collector = get_collector()
                mp = MetricsPersistence()
                snapshot = mp.load_latest_snapshot()
                if snapshot:
                    collector.load_from_snapshot(snapshot)
                    self._metrics_restored = True
                    logger.info("Metrics restored from snapshot")
            except Exception:
                logger.debug("Metrics restore failed (non-critical)")
                self._metrics_restored = False
        except ImportError:
            self._metrics_restored = False

    def _restore_trainer_checkpoint(self) -> None:
        """Restore PPOTrainer from checkpoint if available."""
        if self._trainer_checkpoint_path is None:
            return
        if not self._trainer_checkpoint_path.exists():
            return

        try:
            from cohezion.rl.ppo_trainer import PPOTrainer

            trainer = PPOTrainer.get_singleton()
            trainer.load(self._trainer_checkpoint_path)
            logger.info(f"Trainer checkpoint restored: {self._trainer_checkpoint_path}")
        except Exception as e:
            logger.warning(f"Trainer checkpoint restore failed: {e}")

    def run_benchmark(
        self,
        policy: Any,
        n_episodes: int = 100,
        task_spec: Any | None = None,
        output_path: Path | str | None = None,
        seed: int | None = None,
        verbose: bool = True,
    ) -> Any:
        """Run benchmark evaluation wrapped in the session.

        Args:
            policy: Policy with get_action(state) -> (action, log_prob, value).
            n_episodes: Number of episodes.
            task_spec: Optional TaskSpec to use for all episodes.
            output_path: Optional path to write results.
            seed: Random seed.
            verbose: Print progress.

        Returns:
            CapabilityScorecard with evaluation results.
        """
        from cohezion.eval.pipeline import EvalPipeline

        pipeline = EvalPipeline(verbose=verbose)

        scorecard = pipeline.run(
            policy=policy,
            n_episodes=n_episodes,
            task_spec=task_spec,
            output_path=output_path,
            seed=seed,
        )

        self._latest_scorecard = scorecard.generate_report()
        return scorecard

    def save_trainer_checkpoint(self, path: Path | str) -> None:
        """Save PPOTrainer checkpoint after session.

        Args:
            path: Path to save checkpoint.
        """
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer

            trainer = PPOTrainer.get_singleton()
            trainer.checkpoint(path)
            logger.info(f"Trainer checkpoint saved: {path}")
        except Exception as e:
            logger.warning(f"Trainer checkpoint save failed: {e}")

    def end_session(self) -> BenchmarkSessionSummary:
        """End benchmark session: persist cache, save metrics, save checkpoint.

        Returns:
            BenchmarkSessionSummary with final state.
        """
        duration = time.time() - self._start_time

        self._persist_cache()
        self._persist_metrics()

        if self._trainer_checkpoint_path is not None:
            self.save_trainer_checkpoint(self._trainer_checkpoint_path)

        summary = BenchmarkSessionSummary(
            session_id=self._session_id,
            episodes_completed=self._latest_scorecard.get("latest", {}).get("n_episodes", 0)
            if self._latest_scorecard
            else 0,
            total_duration_seconds=duration,
            cache_entries_loaded=self._cache_loaded,
            cache_entries_saved=self._cache_saved,
            metrics_restored=self._metrics_restored,
            metrics_saved=self._metrics_saved,
            scorecard_snapshot=self._latest_scorecard or {},
        )

        if self._session_id in BenchmarkSessionManager._sessions:
            del BenchmarkSessionManager._sessions[self._session_id]

        return summary

    def _persist_cache(self) -> None:
        """Persist cache to persistence layer."""
        try:
            from cohezion.compound.cache_persistence import CachePersistence

            try:
                from cohezion.swarm.compound_client import get_compound_client

                client = get_compound_client()
                cp = CachePersistence()
                self._cache_saved = cp.save_cache(client._cache)
                logger.info(f"Cache persisted: {self._cache_saved} entries")
            except Exception:
                logger.debug("Compound client unavailable for cache persist")
                self._cache_saved = 0
        except ImportError:
            self._cache_saved = 0

    def _persist_metrics(self) -> None:
        """Persist compound metrics to persistence layer."""
        try:
            from cohezion.compound.metrics_persistence import MetricsPersistence

            try:
                from cohezion.compound.metrics import get_collector

                collector = get_collector()
                mp = MetricsPersistence()
                mp.save_snapshot(collector)
                self._metrics_saved = True
                logger.info("Metrics persisted")
            except Exception:
                logger.debug("Metrics persist failed (non-critical)")
                self._metrics_saved = False
        except ImportError:
            self._metrics_saved = False

    def get_session_id(self) -> str:
        """Return current session ID."""
        return self._session_id

    @classmethod
    def get_session(cls, session_id: str) -> BenchmarkSessionManager | None:
        """Get an active session by ID."""
        return cls._sessions.get(session_id)


@dataclass
class CurriculumState:
    """Tracks curriculum state for self-improving benchmark loop."""

    iteration: int = 0
    weakest_axis: str | None = None
    strongest_axis: str | None = None
    oversample_archetype: str | None = None
    total_episodes: int = 0
    convergence_reached: bool = False


class SelfImprovingBenchmarkLoop:
    """Closed-loop self-improving benchmark: scorecard → curriculum → benchmark.

    Each iteration:
    1. Run benchmark with current curriculum
    2. Record scorecard
    3. Identify weakest axis
    4. Update curriculum to oversample weak axis
    5. Repeat until convergence or max iterations

    Axis → Archetype mapping:
        HIHO Coherence     → HIHO_BASIN
        TRIUNE Balance     → TRIUNE_BALANCE
        Stability          → HIHO_BASIN (stability ≈ HIHO proximity)
        Exotic Charge      → EXOTIC_CHARGE
        Kordylewski Orbit  → KORDYLEWSKI_ORBIT
        SPIN Phase         → HIHO_BASIN (phase = energy proxy)

    Example:
        loop = SelfImprovingBenchmarkLoop(max_iterations=10)
        for iteration in loop.iterate(policy):
            scorecard = iteration.run()
            iteration.record(scorecard)
            if iteration.converged():
                break
            iteration.update_curriculum()
    """

    AXIS_TO_ARCHETYPE = {
        "HIHO Coherence": "HIHO_BASIN",
        "TRIUNE Balance": "TRIUNE_BALANCE",
        "Stability": "HIHO_BASIN",
        "Exotic Charge": "EXOTIC_CHARGE",
        "Kordylewski Orbit": "KORDYLEWSKI_ORBIT",
        "SPIN Phase": "HIHO_BASIN",
    }

    def __init__(
        self,
        max_iterations: int = 10,
        episodes_per_iteration: int = 50,
        convergence_threshold: float = 0.05,
    ) -> None:
        self.max_iterations = max_iterations
        self.episodes_per_iteration = episodes_per_iteration
        self.convergence_threshold = convergence_threshold
        self._state = CurriculumState()
        self._scorecards: list[Any] = []
        self._curriculum_task_specs: list[Any] = []
        self._task_generator: Any | None = None

    def iterate(self, policy: Any) -> SelfImprovingBenchmarkLoop:
        """Generator yielding self for each iteration.

        Yields:
            Self (for fluent chaining).
        """
        self._state.iteration = 0
        self._scorecards = []
        self._init_task_generator()

        for i in range(self.max_iterations):
            self._state.iteration = i + 1
            yield self

            if self._state.convergence_reached:
                break

    def _init_task_generator(self) -> None:
        """Initialize task generator."""
        try:
            from cohezion.rl.task_generator import TaskGenerator

            self._task_generator = TaskGenerator()
        except ImportError:
            logger.warning("TaskGenerator not available")
            self._task_generator = None

    def run(self, policy: Any) -> Any:
        """Run one benchmark iteration with current curriculum.

        Args:
            policy: Policy with get_action(state).

        Returns:
            CapabilityScorecard with results.
        """
        from cohezion.eval.pipeline import EvalPipeline

        pipeline = EvalPipeline(verbose=True)

        if self._curriculum_task_specs:
            import random

            spec = random.choice(self._curriculum_task_specs)
        else:
            spec = None

        scorecard = pipeline.run(
            policy=policy,
            n_episodes=self.episodes_per_iteration,
            task_spec=spec,
        )

        self._scorecards.append(scorecard)
        self._state.total_episodes += self.episodes_per_iteration

        return scorecard

    def record(self, scorecard: Any) -> None:
        """Record a scorecard and update axis tracking.

        Args:
            scorecard: CapabilityScorecard from run().
        """
        scorecard.generate_report()

        tracker = scorecard._longitudinal_tracker
        weakest = tracker.get_weakest_axis()
        strongest = tracker.get_strongest_axis()

        self._state.weakest_axis = weakest
        self._state.strongest_axis = strongest

        logger.info(
            f"Iteration {self._state.iteration}: "
            f"weakest={weakest}, strongest={strongest}, "
            f"total_eps={self._state.total_episodes}"
        )

    def converged(self) -> bool:
        """Check if convergence has been reached.

        Convergence: weakest axis score within convergence_threshold
        of strongest axis score (normalized), OR max iterations reached.

        Returns:
            True if converged.
        """
        if self._state.iteration >= self.max_iterations:
            return True

        if len(self._scorecards) < 2:
            return False

        report = self._scorecards[-1].generate_report()
        scores = report.get("current_capabilities", {})

        if not scores:
            return False

        values = list(scores.values())
        if not values or all(v == 0 for v in values):
            return False

        min_score = min(v for v in values if v > 0)
        max_score = max(values)
        if max_score == 0:
            return False

        normalized_gap = (max_score - min_score) / max_score

        if normalized_gap < self.convergence_threshold:
            self._state.convergence_reached = True
            logger.info(f"Convergence reached: gap={normalized_gap:.3f} < threshold={self.convergence_threshold}")

        return self._state.convergence_reached

    def update_curriculum(self) -> None:
        """Update task curriculum to oversample weakest axis archetype.

        After identifying the weakest axis, this method oversamples
        TaskSpecs targeting that archetype by adding them to the
        curriculum pool with higher probability.
        """
        if self._state.weakest_axis is None:
            return

        if self._task_generator is None:
            return

        archetype = self.AXIS_TO_ARCHETYPE.get(self._state.weakest_axis)
        if archetype is None:
            return

        self._state.oversample_archetype = archetype

        oversample_specs = []
        for difficulty in ["easy", "medium", "hard"]:
            try:
                spec = self._task_generator.sample(
                    difficulty=difficulty,
                    archetype=archetype,
                )
                oversample_specs.append(spec)
                oversample_specs.append(spec)
                oversample_specs.append(spec)
            except Exception:
                pass

        if oversample_specs:
            self._curriculum_task_specs = oversample_specs
            logger.info(f"Curriculum updated: oversampling {archetype} ({len(oversample_specs)} specs in pool)")

    def get_state(self) -> CurriculumState:
        """Return current curriculum state."""
        return self._state

    def get_scorecards(self) -> list[Any]:
        """Return all recorded scorecards."""
        return self._scorecards

    def generate_final_report(self) -> dict[str, Any]:
        """Generate final report after loop completes.

        Returns:
            Dictionary with full loop summary.
        """
        if not self._scorecards:
            return {"error": "No scorecards recorded"}

        final_scorecard = self._scorecards[-1]
        final_report = final_scorecard.generate_report()

        return {
            "iterations": self._state.iteration,
            "total_episodes": self._state.total_episodes,
            "convergence_reached": self._state.convergence_reached,
            "weakest_axis": self._state.weakest_axis,
            "strongest_axis": self._state.strongest_axis,
            "oversample_archetype": self._state.oversample_archetype,
            "final_scorecard": final_report,
            "improvement_trends": final_scorecard.get("longitudinal", {}),
        }
