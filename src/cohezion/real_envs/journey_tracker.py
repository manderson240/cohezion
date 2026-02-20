"""Journey tracker integration for real environments.

Connects real environment trajectories to FLUME 12D tracking,
enabling experience-guided learning from actual execution traces.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.real_envs.base import (
    RealEnvironment,
    EnvironmentStep,
    TrajectorySegment,
)


logger = logging.getLogger(__name__)


@dataclass
class RealEnvironmentJourney:
    """A complete journey through one or more real environments."""

    journey_id: str
    task_description: str
    segments: list[TrajectorySegment] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    success: bool = False
    final_reward: float = 0.0

    # FLUME 12D coordinates (aggregated across segments)
    coherence: float = 0.5
    convergence: float = 0.0
    smoothness: float = 0.0

    def compute_phi_score(self) -> float:
        """Compute overall PHI score for this journey."""
        return self.coherence * 0.5 + self.smoothness * 0.3 + self.convergence * 0.2

    def to_dict(self) -> dict[str, Any]:
        return {
            "journey_id": self.journey_id,
            "task_description": self.task_description,
            "start_time": self.start_time,
            "end_time": self.end_time or time.time(),
            "duration_seconds": (self.end_time or time.time()) - self.start_time,
            "segments": [s.to_dict() for s in self.segments],
            "success": self.success,
            "final_reward": self.final_reward,
            "coherence": self.coherence,
            "convergence": self.convergence,
            "smoothness": self.smoothness,
            "phi_score": self.compute_phi_score(),
        }


class RealEnvironmentJourneyTracker:
    """Tracks journeys across multiple real environments.

    Integrates with FLUME 12D manifold tracking to enable:
    - Experience-guided skill selection
    - Trajectory quality analysis
    - Pattern extraction for future runs

    Example:
        ```python
        tracker = RealEnvironmentJourneyTracker()

        # Multi-environment journey
        with tracker.begin_journey("Build and deploy a web app"):
            # Shell: Create project
            shell_env = ShellEnvironment("Create Python project")
            await shell_env.reset_async()
            obs, _, _, _ = await shell_env.step(ShellAction.create_dir("myapp"))
            tracker.record_segment(shell_env.segment)

            # Browser: Test the app
            browser_env = BrowserEnvironment("Test web app")
            await browser_env.reset_async()
            obs, _, _, _ = await browser_env.step(BrowserAction.navigate("http://localhost:8000"))
            tracker.record_segment(browser_env.segment)

        journey = tracker.end_journey(success=True, final_reward=1.0)
        ```
    """

    def __init__(
        self,
        output_dir: str = "data/real_envs/journeys",
        enable_flume_sync: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_flume_sync = enable_flume_sync

        self._current_journey: RealEnvironmentJourney | None = None
        self._journey_stack: list[RealEnvironmentJourney] = []

    def begin_journey(self, task_description: str) -> RealEnvironmentJourney:
        """Begin tracking a new multi-environment journey."""
        journey_id = f"journey_{int(time.time() * 1000)}"
        journey = RealEnvironmentJourney(
            journey_id=journey_id,
            task_description=task_description,
            start_time=time.time(),
        )

        self._journey_stack.append(journey)
        self._current_journey = journey

        logger.info(f"Started journey: {journey_id} - {task_description[:50]}...")
        return journey

    def record_segment(self, segment: TrajectorySegment) -> None:
        """Record a trajectory segment from an environment."""
        if self._current_journey is None:
            raise RuntimeError("No active journey. Call begin_journey() first.")

        self._current_journey.segments.append(segment)

        # Update aggregated metrics
        if self._current_journey.segments:
            coherences = [s.coherence for s in self._current_journey.segments]
            smoothnesses = [s.smoothness for s in self._current_journey.segments]

            self._current_journey.coherence = sum(coherences) / len(coherences)
            self._current_journey.smoothness = sum(smoothnesses) / len(smoothnesses)

            # Convergence improves with more segments
            self._current_journey.convergence = min(
                len(self._current_journey.segments) / 10, 1.0
            )

        logger.debug(
            f"Recorded segment {segment.segment_id} ({segment.environment_type})"
        )

    def end_journey(
        self,
        success: bool,
        final_reward: float,
        metadata: dict[str, Any] | None = None,
    ) -> RealEnvironmentJourney:
        """End current journey and return it."""
        if self._current_journey is None:
            raise RuntimeError("No active journey to end.")

        journey = self._current_journey
        journey.end_time = time.time()
        journey.success = success
        journey.final_reward = final_reward

        if metadata:
            # Add metadata to last segment if exists
            if journey.segments:
                journey.segments[-1].steps[-1].info.update(
                    metadata
                ) if journey.segments[-1].steps else None

        # Sync to FLUME if enabled
        if self.enable_flume_sync:
            self._sync_to_flume(journey)

        # Save to disk
        self._save_journey(journey)

        # Pop from stack
        self._journey_stack.pop()
        self._current_journey = self._journey_stack[-1] if self._journey_stack else None

        logger.info(
            f"Journey complete: {journey.journey_id} - "
            f"success={success}, reward={final_reward:.2f}, phi={journey.compute_phi_score():.2f}"
        )

        return journey

    def _save_journey(self, journey: RealEnvironmentJourney) -> Path:
        """Save journey to disk."""
        filepath = self.output_dir / f"{journey.journey_id}.json"

        with open(filepath, "w") as f:
            json.dump(journey.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved journey to {filepath}")
        return filepath

    def _sync_to_flume(self, journey: RealEnvironmentJourney) -> None:
        """Sync journey to FLUME manifold tracker."""
        try:
            from cohezion.compound.journey_tracker import (
                get_journey_tracker,
                OperationType,
            )

            tracker = get_journey_tracker()

            # Create 12D trajectory point from journey
            tracker.record_execution(
                agent_id="real_env_agent",
                phase="execution",
                position={
                    "x": journey.coherence,
                    "y": journey.smoothness,
                    "z": journey.convergence,
                    "temporal": journey.end_time - journey.start_time
                    if journey.end_time
                    else 0,
                    "physics": journey.success,
                    "biology": len(journey.segments) / 10,  # Complexity
                    "logic": journey.final_reward,
                    "quantum": journey.compute_phi_score(),
                    "field": 0.5,
                    "control": sum(
                        s.compute_metrics()["success_rate"] for s in journey.segments
                    )
                    / max(len(journey.segments), 1),
                    "novelty": 0.5,
                    "precipitation": 1.0 if journey.success else 0.0,
                },
                coherence=journey.coherence,
                operation_type=OperationType.EXECUTE,
                metadata={
                    "journey_id": journey.journey_id,
                    "task_description": journey.task_description,
                    "num_segments": len(journey.segments),
                },
            )

            logger.debug(f"Synced journey {journey.journey_id} to FLUME")

        except Exception as e:
            logger.warning(f"Failed to sync to FLUME: {e}")

    def get_recent_journeys(self, n: int = 10) -> list[RealEnvironmentJourney]:
        """Get recent journeys from disk."""
        journeys = []

        for filepath in sorted(self.output_dir.glob("journey_*.json"), reverse=True)[
            :n
        ]:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    # Convert back to object (simplified)
                    journey = RealEnvironmentJourney(
                        journey_id=data["journey_id"],
                        task_description=data["task_description"],
                        start_time=data["start_time"],
                        end_time=data.get("end_time"),
                        success=data.get("success", False),
                        final_reward=data.get("final_reward", 0.0),
                        coherence=data.get("coherence", 0.5),
                        convergence=data.get("convergence", 0.0),
                        smoothness=data.get("smoothness", 0.0),
                    )
                    journeys.append(journey)
            except Exception as e:
                logger.warning(f"Failed to load journey from {filepath}: {e}")

        return journeys

    def analyze_patterns(self, n_recent: int = 100) -> dict[str, Any]:
        """Analyze patterns in recent journeys."""
        journeys = self.get_recent_journeys(n_recent)

        if not journeys:
            return {"error": "No journeys to analyze"}

        # Success rate by environment type
        success_by_env: dict[str, list[bool]] = {}

        for journey in journeys:
            for segment in journey.segments:
                env_type = segment.environment_type
                if env_type not in success_by_env:
                    success_by_env[env_type] = []
                success_by_env[env_type].append(journey.success)

        # Compute metrics
        analysis = {
            "total_journeys": len(journeys),
            "overall_success_rate": sum(1 for j in journeys if j.success)
            / len(journeys),
            "avg_phi_score": sum(j.compute_phi_score() for j in journeys)
            / len(journeys),
            "avg_reward": sum(j.final_reward for j in journeys) / len(journeys),
            "success_by_environment": {
                env: sum(results) / len(results) if results else 0
                for env, results in success_by_env.items()
            },
            "avg_segments_per_journey": sum(len(j.segments) for j in journeys)
            / len(journeys),
        }

        return analysis
