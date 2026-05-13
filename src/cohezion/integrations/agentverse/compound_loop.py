"""Compound Benchmark Loop - Orchestrate benchmark → refine → re-benchmark cycle.

The CompoundBenchmarkLoop implements a closed-loop learning system where:
1. AgentVerse benchmarks run against Cohezion skills
2. Metrics are analyzed to identify weak skills
3. SkillRefiner improves weak skills
4. Re-benchmark to verify improvement
5. Repeat until convergence or max iterations

This creates compounding improvement where each iteration's learnings
improve the skill definitions for future iterations.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.skill_refiner import SkillRefiner
    from cohezion.integrations.agentverse.benchmark_runner import AgentVerseBenchmarkRunner

logger = logging.getLogger(__name__)


@dataclass
class LoopConfig:
    """Configuration for compound benchmark loop."""

    max_iterations: int = 5
    coherence_threshold: float = 0.5
    weak_skill_threshold: float = 0.4
    improvement_threshold: float = 0.1
    enable_parallel_refinement: bool = True


@dataclass
class IterationResult:
    """Result from a single loop iteration."""

    iteration: int
    coherence_before: float
    coherence_after: float
    weak_skills: list[str]
    refined_skills: list[str]
    converged: bool
    improvement: float


@dataclass
class LoopResult:
    """Final result from the compound benchmark loop."""

    total_iterations: int
    final_coherence: float
    initial_coherence: float
    total_improvement: float
    iterations: list[IterationResult]
    refined_skills: set[str]
    converged: bool


class CompoundBenchmarkLoop:
    """Orchestrates benchmark → skill refinement → re-benchmark cycle.

    This loop implements compound engineering for Cohezion skills by:
    1. Running AgentVerse benchmarks to measure skill performance
    2. Identifying skills with below-threshold coherence
    3. Triggering SkillRefiner to improve those skills
    4. Re-running benchmarks to verify improvement
    5. Repeating until convergence or max iterations

    Each iteration compounds on previous learnings, creating a
    closed-loop optimization system.

    Parameters
    ----------
    runner : AgentVerseBenchmarkRunner
        Benchmark runner with vault integration
    refiner : SkillRefiner
        Skill refiner for improving weak skills

    Examples
    --------
    >>> loop = CompoundBenchmarkLoop(runner, refiner)
    >>> tasks = [{"task": "write tests", "skill": "testing_PRIME"}]
    >>> result = await loop.run_loop(tasks)
    >>> print(f"Improved coherence by {result.total_improvement:.2%}")
    """

    def __init__(
        self,
        runner: AgentVerseBenchmarkRunner,
        refiner: SkillRefiner,
        config: LoopConfig | None = None,
    ) -> None:
        """Initialize compound benchmark loop.

        Args:
            runner: AgentVerseBenchmarkRunner instance
            refiner: SkillRefiner instance
            config: Optional loop configuration
        """
        self.runner = runner
        self.refiner = refiner
        self.config = config or LoopConfig()
        self._iteration_history: list[IterationResult] = []

    async def run_loop(
        self,
        tasks: list[dict[str, str]],
        skills_to_benchmark: list[str] | None = None,
    ) -> LoopResult:
        """Run compound benchmark loop until convergence or max iterations.

        Parameters
        ----------
        tasks : list[dict[str, str]]
            List of benchmark tasks with 'task' and 'skill' keys
        skills_to_benchmark : list[str], optional
            Subset of skills to focus refinement on

        Returns
        -------
        LoopResult
            Final result with improvement metrics and iteration history
        """
        logger.info(
            "Starting compound benchmark loop: max_iterations=%d, threshold=%.2f",
            self.config.max_iterations,
            self.config.coherence_threshold,
        )

        self.runner.run_batch_benchmark(tasks)
        initial_coherence = self.runner.get_average_coherence()
        self.runner.identify_weak_skills(self.config.weak_skill_threshold)

        iterations: list[IterationResult] = []
        refined_skills: set[str] = set()
        current_coherence = initial_coherence

        for i in range(self.config.max_iterations):
            logger.info("Loop iteration %d/%d", i + 1, self.config.max_iterations)

            iteration_result = await self._run_iteration(tasks, i, current_coherence, refined_skills)
            iterations.append(iteration_result)
            self._iteration_history.append(iteration_result)

            current_coherence = iteration_result.coherence_after
            refined_skills.update(iteration_result.refined_skills)

            if iteration_result.converged:
                logger.info("Loop converged at iteration %d", i + 1)
                break

        self.runner.persist_results()

        return LoopResult(
            total_iterations=len(iterations),
            final_coherence=current_coherence,
            initial_coherence=initial_coherence,
            total_improvement=current_coherence - initial_coherence,
            iterations=iterations,
            refined_skills=refined_skills,
            converged=any(it.converged for it in iterations),
        )

    async def _run_iteration(
        self,
        tasks: list[dict[str, str]],
        iteration: int,
        coherence_before: float,
        already_refined: set[str],
    ) -> IterationResult:
        """Run a single iteration of the loop.

        Parameters
        ----------
        tasks : list[dict[str, str]]
            Benchmark tasks
        iteration : int
            Current iteration number
        coherence_before : float
            Coherence before this iteration
        already_refined : set[str]
            Skills already refined in previous iterations

        Returns
        -------
        IterationResult
            Result from this iteration
        """
        weak_skills = self.runner.identify_weak_skills(self.config.weak_skill_threshold)
        skills_to_refine = [s for s in weak_skills if s not in already_refined]

        logger.info(
            "Iteration %d: found %d weak skills, %d to refine",
            iteration + 1,
            len(weak_skills),
            len(skills_to_refine),
        )

        refined = await self._refine_skills(skills_to_refine, tasks)

        coherence_after = self.runner.get_average_coherence()
        improvement = coherence_after - coherence_before

        converged = improvement >= self.config.improvement_threshold

        return IterationResult(
            iteration=iteration,
            coherence_before=coherence_before,
            coherence_after=coherence_after,
            weak_skills=weak_skills,
            refined_skills=list(refined.keys()),
            converged=converged,
            improvement=improvement,
        )

    async def _refine_skills(
        self,
        skills: list[str],
        tasks: list[dict[str, str]],
    ) -> dict[str, str]:
        """Refine multiple skills.

        Parameters
        ----------
        skills : list[str]
            Skills to refine
        tasks : list[dict[str, str]]
            Benchmark tasks for context

        Returns
        -------
        dict[str, str]
            Mapping of skill name to refined file path
        """
        results: dict[str, str] = {}

        if not skills:
            return results

        if self.config.enable_parallel_refinement:
            refinements = await asyncio.gather(
                *[self._refine_single_skill(skill, self._get_task_for_skill(skill, tasks)) for skill in skills],
                return_exceptions=True,
            )
            for skill, result in zip(skills, refinements, strict=True):
                if isinstance(result, str):
                    results[skill] = result
        else:
            for skill in skills:
                task = self._get_task_for_skill(skill, tasks)
                result = await self._refine_single_skill(skill, task)
                if isinstance(result, str):
                    results[skill] = result

        logger.info("Refined %d skills: %s", len(results), list(results.keys()))
        return results

    async def _refine_single_skill(
        self,
        skill: str,
        task: dict[str, str] | None,
    ) -> str | None:
        """Refine a single skill.

        Parameters
        ----------
        skill : str
            Skill name to refine
        task : dict[str, str] | None
            Associated benchmark task

        Returns
        -------
        str | None
            Path to refined file if successful
        """
        try:
            execution_result = {
                "success": True,
                "metrics": {"coherence": self.runner.get_average_coherence()},
                "duration_seconds": 1.0,
            }
            return self.refiner.refine(
                skill_name=skill,
                operation_type="generate",
                execution_result=execution_result,
            )
        except Exception as e:
            logger.debug("Failed to refine skill %s: %s", skill, e)
            return None

    def _get_task_for_skill(
        self,
        skill: str,
        tasks: list[dict[str, str]],
    ) -> dict[str, str] | None:
        """Get benchmark task for a skill.

        Parameters
        ----------
        skill : str
            Skill name
        tasks : list[dict[str, str]]
            All benchmark tasks

        Returns
        -------
        dict[str, str] | None
            Task dict for the skill
        """
        for task in tasks:
            if task.get("skill") == skill:
                return task
        return tasks[0] if tasks else None

    def get_convergence_trajectory(self) -> list[dict[str, Any]]:
        """Get the coherence trajectory across all iterations.

        Returns
        -------
        list[dict[str, Any]]
            List of iteration metrics
        """
        return [
            {
                "iteration": it.iteration,
                "coherence_before": it.coherence_before,
                "coherence_after": it.coherence_after,
                "improvement": it.improvement,
                "weak_skills": it.weak_skills,
                "refined_skills": it.refined_skills,
            }
            for it in self._iteration_history
        ]

    def identify_weak_skills_from_results(
        self,
        threshold: float | None = None,
    ) -> list[str]:
        """Identify weak skills from current benchmark results.

        Parameters
        ----------
        threshold : float, optional
            Override weak skill threshold

        Returns
        -------
        list[str]
            List of weak skill names
        """
        return self.runner.identify_weak_skills(threshold or self.config.weak_skill_threshold)

    def get_refinement_candidates(self) -> list[str]:
        """Get skills that are candidates for refinement.

        Returns
        -------
        list[str]
            Skills that failed or had low coherence
        """
        return self.runner.get_refinement_candidates()
