"""EvalPipeline and RalphLoop for long-running evaluation patterns.

Architecture:
    - EvalPipeline: Orchestrates episode collection with RalphLoop
    - RalphLoop: FOR loop with DONE incantation and escalation

Ralph Loop Pattern:
    RalphLoop("Continue until success criteria met with DONE", max_iterations=20)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cohezion.rl.task_generator import TaskSpec
    from cohezion.sandbox.isolation import IsolationManager


class EpisodeStatus(StrEnum):
    """Status of a single episode."""

    SUCCESS = "success"
    FAILURE = "failure"
    ESCALATED = "escalated"
    RUNNING = "running"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class EpisodeResult:
    """Result of a single episode."""

    episode_id: str
    status: EpisodeStatus
    task_spec: TaskSpec
    duration_seconds: float
    iterations: int
    final_state: dict | None = None
    error: str | None = None
    escalation_level: int = 0


@dataclass
class RalphLoopConfig:
    """Configuration for RalphLoop behavior."""

    max_iterations: int = 20
    escalation_threshold: int = 3
    escalation_factor: float = 1.5
    done_keyword: str = "DONE"
    initial_difficulty: int = 1


@dataclass
class PipelineProgress:
    """Tracks overall pipeline progress."""

    total_episodes: int = 0
    successful_episodes: int = 0
    failed_episodes: int = 0
    escalated_episodes: int = 0
    current_difficulty: int = 1
    consecutive_failures: int = 0
    total_iterations: int = 0
    successful_task_specs: list[str] = field(default_factory=list)
    failed_approaches: list[dict] = field(default_factory=list)
    milestones: list[dict] = field(default_factory=list)


class RalphLoop:
    """Ralph loop pattern: FOR iteration with DONE incantation and escalation.

    Implements the "Continue until success criteria met with DONE" pattern where:
    1. Each iteration checks for DONE keyword in agent output
    2. After escalation_threshold failures, difficulty increases
    3. Max iterations prevents infinite loops
    """

    def __init__(
        self,
        done_keyword: str = "DONE",
        max_iterations: int = 20,
        escalation_threshold: int = 3,
        escalation_factor: float = 1.5,
    ) -> None:
        """Initialize RalphLoop.

        Args:
            done_keyword: Keyword that signals successful completion
            max_iterations: Maximum iterations before giving up
            escalation_threshold: Failures before escalating difficulty
            escalation_factor: Multiplier for difficulty on escalation
        """
        self.done_keyword = done_keyword
        self.max_iterations = max_iterations
        self.escalation_threshold = escalation_threshold
        self.escalation_factor = escalation_factor
        self.consecutive_failures = 0
        self.current_difficulty = 1

    def check_done(self, agent_output: str) -> bool:
        """Check if agent output contains DONE keyword.

        Args:
            agent_output: String output from agent

        Returns:
            True if DONE found, False otherwise
        """
        if not agent_output:
            return False
        return self.done_keyword.upper() in agent_output.upper()

    def record_failure(self) -> None:
        """Record a failed iteration, potentially triggering escalation."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.escalation_threshold:
            self.escalate()

    def record_success(self) -> None:
        """Record a successful iteration, resetting failure counter."""
        self.consecutive_failures = 0

    def escalate(self) -> int:
        """Increase difficulty level.

        Returns:
            New difficulty level
        """
        old_difficulty = self.current_difficulty
        self.current_difficulty = min(
            int(self.current_difficulty * self.escalation_factor),
            10,
        )
        self.consecutive_failures = 0
        logger.info(f"Escalating from difficulty {old_difficulty} to {self.current_difficulty}")
        return self.current_difficulty

    def should_continue(self, iteration: int) -> bool:
        """Check if loop should continue.

        Args:
            iteration: Current iteration number

        Returns:
            True if should continue, False if max iterations reached
        """
        return iteration < self.max_iterations

    def get_config(self) -> RalphLoopConfig:
        """Get current configuration.

        Returns:
            RalphLoopConfig with current settings
        """
        return RalphLoopConfig(
            max_iterations=self.max_iterations,
            escalation_threshold=self.escalation_threshold,
            escalation_factor=self.escalation_factor,
            done_keyword=self.done_keyword,
            initial_difficulty=self.current_difficulty,
        )


class EvalPipeline:
    """Evaluation pipeline for collecting episodes via RalphLoop.

    Orchestrates:
    1. RalphLoop iteration with DONE incantation
    2. Sandbox execution via IsolationManager
    3. Git commits every 10 successful episodes
    4. EVAL_PROGRESS.md lab notes tracking
    """

    COMMIT_THRESHOLD = 10

    def __init__(
        self,
        isolation_manager: IsolationManager | None = None,
        progress_path: Path | None = None,
        git_auto_commit: bool = True,
    ) -> None:
        """Initialize EvalPipeline.

        Args:
            isolation_manager: Sandbox isolation manager (uses default if None)
            progress_path: Path to EVAL_PROGRESS.md (default: data/eval/EVAL_PROGRESS.md)
            git_auto_commit: Whether to auto-commit after successful episodes
        """
        if isolation_manager is None:
            from cohezion.sandbox.isolation import get_isolation_manager

            isolation_manager = get_isolation_manager()
        self.isolation_manager = isolation_manager
        self.progress_path = progress_path or Path("data/eval/EVAL_PROGRESS.md")
        self.git_auto_commit = git_auto_commit
        self.progress = PipelineProgress()
        self._successful_since_commit = 0

    def run(
        self,
        task_spec: TaskSpec,
        n_episodes: int = 1,
        use_swarm_advisor: bool = False,
    ) -> list[EpisodeResult]:
        """Run evaluation episodes for a task spec.

        Args:
            task_spec: Task specification to evaluate
            n_episodes: Number of episodes to run
            use_swarm_advisor: Whether to use swarm advisor for guidance

        Returns:
            List of EpisodeResult for each episode
        """
        results: list[EpisodeResult] = []
        ralph = RalphLoop()

        for episode_idx in range(n_episodes):
            logger.info(
                f"Running episode {episode_idx + 1}/{n_episodes} for task {task_spec.archetype}"
            )

            result = self._run_single_episode(
                task_spec=task_spec,
                ralph=ralph,
                episode_idx=episode_idx,
                use_swarm_advisor=use_swarm_advisor,
            )
            results.append(result)
            self._update_progress(result, task_spec)

            if result.status == EpisodeStatus.SUCCESS:
                self._handle_success(task_spec)

        return results

    def _run_single_episode(
        self,
        task_spec: TaskSpec,
        ralph: RalphLoop,
        episode_idx: int,
        use_swarm_advisor: bool,
    ) -> EpisodeResult:
        """Run a single episode within RalphLoop.

        Args:
            task_spec: Task specification
            ralph: RalphLoop instance for iteration control
            episode_idx: Episode index
            use_swarm_advisor: Whether to use swarm advisor

        Returns:
            EpisodeResult for this episode
        """
        episode_id = f"{task_spec.archetype}_{episode_idx}_{int(time.time())}"
        start_time = time.time()
        iteration = 0
        last_output = ""

        while ralph.should_continue(iteration):
            iteration += 1

            try:
                last_output = self._execute_iteration(
                    task_spec=task_spec,
                    iteration=iteration,
                    use_swarm_advisor=use_swarm_advisor,
                )
            except Exception as e:
                logger.error(f"Iteration {iteration} failed with error: {e}")
                ralph.record_failure()
                return EpisodeResult(
                    episode_id=episode_id,
                    status=EpisodeStatus.FAILURE,
                    task_spec=task_spec,
                    duration_seconds=time.time() - start_time,
                    iterations=iteration,
                    error=str(e),
                )

            if ralph.check_done(last_output):
                ralph.record_success()
                return EpisodeResult(
                    episode_id=episode_id,
                    status=EpisodeStatus.SUCCESS,
                    task_spec=task_spec,
                    duration_seconds=time.time() - start_time,
                    iterations=iteration,
                    final_state={"output": last_output},
                )

            ralph.record_failure()

        if iteration >= ralph.max_iterations:
            return EpisodeResult(
                episode_id=episode_id,
                status=EpisodeStatus.MAX_ITERATIONS,
                task_spec=task_spec,
                duration_seconds=time.time() - start_time,
                iterations=iteration,
                final_state={"last_output": last_output},
            )

        return EpisodeResult(
            episode_id=episode_id,
            status=EpisodeStatus.ESCALATED,
            task_spec=task_spec,
            duration_seconds=time.time() - start_time,
            iterations=iteration,
            escalation_level=ralph.current_difficulty,
        )

    def _execute_iteration(
        self,
        task_spec: TaskSpec,
        iteration: int,
        use_swarm_advisor: bool,
    ) -> str:
        """Execute a single RalphLoop iteration.

        Args:
            task_spec: Task specification
            iteration: Iteration number
            use_swarm_advisor: Whether to use swarm advisor

        Returns:
            Agent output string (may contain DONE)
        """
        from cohezion.rl.environment import FlumeNavEnv

        env = FlumeNavEnv()
        obs, info = env.reset(task_spec=task_spec)

        for _step in range(task_spec.horizon):
            action = self._get_action(obs, info, iteration, use_swarm_advisor)
            obs, reward, terminated, truncated, info = env.step(action)

            if terminated or truncated:
                break

        final_obs = obs
        output = self._format_output(final_obs, info, reward)

        return output

    def _get_action(
        self,
        obs: dict,
        info: dict,
        iteration: int,
        use_swarm_advisor: bool,
    ) -> int:
        """Get action for current observation.

        Args:
            obs: Current observation
            info: Environment info
            iteration: Current iteration
            use_swarm_advisor: Whether to use swarm advisor

        Returns:
            Action integer
        """
        if use_swarm_advisor:
            return self._get_swarm_action(obs, info, iteration)
        return self._get_default_action(obs, info, iteration)

    def _get_swarm_action(
        self,
        obs: dict,
        info: dict,
        iteration: int,
    ) -> int:
        """Get action using swarm advisor.

        Args:
            obs: Current observation
            info: Environment info
            iteration: Current iteration

        Returns:
            Action from swarm advisor
        """
        return 0

    def _get_default_action(
        self,
        obs: dict,
        info: dict,
        iteration: int,
    ) -> int:
        """Get default action based on EVO state.

        Args:
            obs: Current observation
            info: Environment info
            iteration: Current iteration

        Returns:
            Action integer
        """
        evo_state = obs.get("evo_state", {})
        coherence = evo_state.get("coherence", 0.5)

        if coherence > 0.8:
            return 2
        elif coherence > 0.5:
            return 1
        else:
            return 0

    def _format_output(
        self,
        obs: dict,
        info: dict,
        reward: float,
    ) -> str:
        """Format observation into output string.

        Args:
            obs: Final observation
            info: Environment info
            reward: Final reward

        Returns:
            Formatted output string
        """
        if reward > 0.9:
            return f"DONE: Task completed with reward {reward:.3f}"
        elif reward > 0.5:
            return f"PARTIAL: Task partially completed with reward {reward:.3f}"
        else:
            evo_state = obs.get("evo_state", {})
            coherence = evo_state.get("coherence", 0.0)
            return f"INCOMPLETE: coherence={coherence:.3f}, reward={reward:.3f}"

    def _update_progress(
        self,
        result: EpisodeResult,
        task_spec: TaskSpec,
    ) -> None:
        """Update progress tracking after episode.

        Args:
            result: Episode result
            task_spec: Task specification
        """
        self.progress.total_episodes += 1
        self.progress.total_iterations += result.iterations

        if result.status == EpisodeStatus.SUCCESS:
            self.progress.successful_episodes += 1
            self.progress.successful_task_specs.append(task_spec.archetype)
        elif result.status == EpisodeStatus.ESCALATED:
            self.progress.escalated_episodes += 1
            self.progress.failed_approaches.append(
                {
                    "archetype": task_spec.archetype,
                    "difficulty": task_spec.difficulty,
                    "iterations": result.iterations,
                }
            )
        else:
            self.progress.failed_episodes += 1

        self._write_progress()

    def _handle_success(self, task_spec: TaskSpec) -> None:
        """Handle successful episode.

        Args:
            task_spec: Task specification that succeeded
        """
        self._successful_since_commit += 1

        if self.git_auto_commit and self._successful_since_commit >= self.COMMIT_THRESHOLD:
            self._git_commit()
            self._successful_since_commit = 0

    def _git_commit(self) -> None:
        """Create git commit for progress."""
        import shutil
        import subprocess

        git_path = shutil.which("git")
        if not git_path:
            logger.warning("git not found in PATH, skipping commit")
            return

        try:
            subprocess.run(  # noqa: S603
                [git_path, "add", str(self.progress_path)],
                check=True,
                capture_output=True,
            )
            commit_msg = (
                f"eval: record progress - {self.progress.successful_episodes} successful episodes"
            )
            subprocess.run(  # noqa: S603
                [git_path, "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
            )
            logger.info(f"Git commit created: {commit_msg}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e}")

    def _write_progress(self) -> None:
        """Write EVAL_PROGRESS.md lab notes."""
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()
        lines = [
            "# EVAL_PROGRESS.md - Lab Notes",
            "",
            f"**Updated**: {timestamp}",
            "",
            "## Summary",
            "",
            f"- **Total Episodes**: {self.progress.total_episodes}",
            f"- **Successful**: {self.progress.successful_episodes}",
            f"- **Failed**: {self.progress.failed_episodes}",
            f"- **Escalated**: {self.progress.escalated_episodes}",
            f"- **Success Rate**: {self._success_rate():.1%}",
            "",
            "## Milestones",
            "",
        ]

        for milestone in self.progress.milestones:
            lines.append(f"- {milestone.get('description', 'Unknown milestone')}")

        lines.extend(["", "## Failed Approaches", ""])

        for failed in self.progress.failed_approaches:
            lines.append(
                f"- {failed.get('archetype', 'unknown')} "
                f"(difficulty={failed.get('difficulty', 0)}): "
                f"{failed.get('iterations', 0)} iterations"
            )

        lines.extend(["", "## EVO Physics Tables", "", "### Coherence Dynamics", ""])
        lines.append("| Episode | Coherence | Phase | Amplitude |")
        lines.append("|---------|-----------|-------|-----------|")

        lines.extend(["", "### TRIUNE Balance", "", "| Episode | Doer | Thinker | Knower |"])
        lines.append("|---------|------|---------|--------|")

        content = "\n".join(lines) + "\n"
        self.progress_path.write_text(content)

    def _success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate as float
        """
        if self.progress.total_episodes == 0:
            return 0.0
        return self.progress.successful_episodes / self.progress.total_episodes

    def get_progress(self) -> PipelineProgress:
        """Get current pipeline progress.

        Returns:
            PipelineProgress object
        """
        return self.progress
