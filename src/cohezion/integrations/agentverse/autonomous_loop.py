"""Autonomous Compound Benchmark Loop.

Self-improving benchmark system that:
1. Auto-discovers skills from skills/ directory
2. Executes tasks via LLM (Ollama cloud)
3. Evaluates coherence with real LLM judgments
4. Refines weak skills automatically
5. Persists all results to vault
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from cohezion.core.mcp_client import MCPClient
    from cohezion.integrations.agentverse.llm_executor import LLMExecutor


logger = logging.getLogger(__name__)


@dataclass
class SkillBenchmark:
    """A skill benchmark task."""

    skill_name: str
    skill_path: Path
    task: str
    coherence: float = 0.0
    refined: bool = False
    refinement_count: int = 0


@dataclass
class RefinementResult:
    """Result from refining a skill."""

    skill_name: str
    original_path: Path
    refined_path: Path
    success: bool
    coherence_before: float
    coherence_after: float
    error: str | None = None


class AutonomousCompoundLoop:
    """Autonomous compound benchmark loop.

    Discovers skills, benchmarks them via LLM, and refines
    weak skills automatically.

    Parameters
    ----------
    skills_dir : Path
        Directory containing PRIME skill files
    mcp_client : MCPClient
        Vault MCP client for persistence
    llm_executor : LLMExecutor
        LLM executor for task execution
    weak_threshold : float
        Coherence threshold below which skills are refined
    improvement_threshold : float
        Required improvement to consider refinement successful
    max_refinements : int
        Maximum refinements per skill

    Examples
    --------
    >>> loop = AutonomousCompoundLoop(
    ...     skills_dir=Path("skills/"),
    ...     mcp_client=mcp_client,
    ...     llm_executor=LLMExecutor(model="qwen3.5:cloud"),
    ... )
    >>> results = await loop.run()
    >>> print(f"Benchmarked {len(results)} skills")
    """

    def __init__(
        self,
        skills_dir: Path,
        mcp_client: MCPClient,
        llm_executor: LLMExecutor,
        weak_threshold: float = 0.4,
        improvement_threshold: float = 0.1,
        max_refinements: int = 2,
    ) -> None:
        """Initialize autonomous compound loop."""
        self.skills_dir = skills_dir
        self.mcp_client = mcp_client
        self.llm_executor = llm_executor
        self.weak_threshold = weak_threshold
        self.improvement_threshold = improvement_threshold
        self.max_refinements = max_refinements
        self._results: list[SkillBenchmark] = []
        self._refinements: list[RefinementResult] = []

    def discover_skills(self) -> list[SkillBenchmark]:
        """Discover and catalog skills from skills directory.

        Returns
        -------
        list[SkillBenchmark]
            List of discovered skills with tasks
        """
        logger.info("Discovering skills in %s", self.skills_dir)

        if not self.skills_dir.exists():
            logger.warning("Skills directory does not exist: %s", self.skills_dir)
            return []

        skills: list[SkillBenchmark] = []

        for skill_file in self.skills_dir.glob("*PRIME.md"):
            skill_name = skill_file.stem

            try:
                content = skill_file.read_text()
                self._extract_skill_description(content)
                task = f"Apply {skill_name} to solve a real-world problem"
            except Exception as e:
                logger.warning("Failed to read skill %s: %s", skill_name, e)
                continue

            skills.append(
                SkillBenchmark(
                    skill_name=skill_name,
                    skill_path=skill_file,
                    task=task,
                )
            )

        logger.info("Discovered %d skills", len(skills))
        return skills

    def _extract_skill_description(self, content: str) -> str:
        """Extract skill description from markdown content.

        Parameters
        ----------
        content : str
            Skill file content

        Returns
        -------
        str
            Extracted description
        """
        lines = content.split("\n")
        description_lines: list[str] = []

        in_description = False
        for line in lines:
            if line.startswith("**Purpose**"):
                in_description = True
                continue
            elif line.startswith("**") and in_description:
                break
            elif in_description and line.strip():
                description_lines.append(line.strip())

        return " ".join(description_lines[:3]) if description_lines else "General skill"

    async def benchmark_skill(self, benchmark: SkillBenchmark) -> SkillBenchmark:
        """Benchmark a single skill.

        Parameters
        ----------
        benchmark : SkillBenchmark
            Skill to benchmark

        Returns
        -------
        SkillBenchmark
            Updated benchmark with coherence score
        """
        logger.debug("Benchmarking %s", benchmark.skill_name)

        result = await self.llm_executor.execute_task(
            task=benchmark.task,
            skill=benchmark.skill_name,
        )

        benchmark.coherence = result.coherence
        logger.info(
            "Skill %s coherence: %.3f (latency: %.0fms)",
            benchmark.skill_name,
            result.coherence,
            result.latency_ms,
        )

        return benchmark

    async def benchmark_all(self) -> list[SkillBenchmark]:
        """Benchmark all discovered skills.

        Returns
        -------
        list[SkillBenchmark]
            Skills with coherence scores
        """
        skills = self.discover_skills()

        logger.info("Benchmarking %d skills...", len(skills))

        for skill in skills:
            await self.benchmark_skill(skill)
            self._results.append(skill)

        return skills

    async def refine_weak_skills(
        self,
        skills: list[SkillBenchmark],
    ) -> list[RefinementResult]:
        """Refine skills with low coherence.

        Parameters
        ----------
        skills : list[SkillBenchmark]
            Skills to evaluate for refinement

        Returns
        -------
        list[RefinementResult]
            Results of refinement attempts
        """
        weak_skills = [s for s in skills if s.coherence < self.weak_threshold]

        logger.info("Found %d weak skills to refine", len(weak_skills))

        for skill in weak_skills:
            if skill.refinement_count >= self.max_refinements:
                logger.info("Skill %s already refined max times, skipping", skill.skill_name)
                continue

            result = await self._refine_skill(skill)
            self._refinements.append(result)

        return self._refinements

    async def _refine_skill(self, skill: SkillBenchmark) -> RefinementResult:
        """Refine a single skill.

        Parameters
        ----------
        skill : SkillBenchmark
            Skill to refine

        Returns
        -------
        RefinementResult
            Result of refinement
        """
        coherence_before = skill.coherence
        logger.info(
            "Refining %s (coherence: %.3f)",
            skill.skill_name,
            coherence_before,
        )

        refined_path = self.skills_dir / "refined" / f"{skill.skill_name}.md"

        try:
            original_content = skill.skill_path.read_text()

            refinement_prompt = (
                f"Improve the following skill definition to address these weaknesses:\n"
                f"- Current coherence: {coherence_before:.2f}/1.0\n"
                f"- Skill: {skill.skill_name}\n\n"
                f"Original content:\n{original_content[:1000]}\n\n"
                f"Provide an improved version that better demonstrates "
                f"the skill's principles."
            )

            result = await self.llm_executor.execute_task(
                task=refinement_prompt,
                skill=skill.skill_name,
            )

            refined_path.parent.mkdir(parents=True, exist_ok=True)
            refined_path.write_text(result.output)

            skill.refined = True
            skill.refinement_count += 1

            new_benchmark = await self.benchmark_skill(skill)

            return RefinementResult(
                skill_name=skill.skill_name,
                original_path=skill.skill_path,
                refined_path=refined_path,
                success=True,
                coherence_before=coherence_before,
                coherence_after=new_benchmark.coherence,
            )

        except Exception as e:
            logger.error("Failed to refine %s: %s", skill.skill_name, e)
            return RefinementResult(
                skill_name=skill.skill_name,
                original_path=skill.skill_path,
                refined_path=refined_path,
                success=False,
                coherence_before=coherence_before,
                coherence_after=coherence_before,
                error=str(e),
            )

    async def persist_results(self) -> str:
        """Persist benchmark results to vault.

        Returns
        -------
        str
            Vault path where results were stored
        """
        data = {
            "timestamp": time.time(),
            "n_skills": len(self._results),
            "n_refinements": len(self._refinements),
            "skills": [
                {
                    "skill": s.skill_name,
                    "coherence": s.coherence,
                    "refined": s.refined,
                    "refinement_count": s.refinement_count,
                }
                for s in self._results
            ],
            "refinements": [
                {
                    "skill": r.skill_name,
                    "success": r.success,
                    "coherence_before": r.coherence_before,
                    "coherence_after": r.coherence_after,
                    "error": r.error,
                }
                for r in self._refinements
            ],
        }

        unique_id = uuid.uuid4().hex[:8]
        vault_path = f"/vault/benchmarks/autonomous_{unique_id}.json"

        try:
            self.mcp_client.vault_write(vault_path, json.dumps(data, indent=2))
            logger.info("Persisted results to %s", vault_path)
        except Exception as e:
            logger.error("Failed to persist results: %s", e)

        return vault_path

    async def run(self) -> list[SkillBenchmark]:
        """Run the autonomous benchmark loop.

        Returns
        -------
        list[SkillBenchmark]
            Final benchmark results
        """
        logger.info("Starting autonomous compound loop")

        skills = await self.benchmark_all()

        weak_skills = [s for s in skills if s.coherence < self.weak_threshold]
        if weak_skills:
            await self.refine_weak_skills(weak_skills)

        await self.persist_results()

        logger.info(
            "Autonomous loop complete: %d skills, %d weak, %d refined",
            len(skills),
            len(weak_skills),
            sum(1 for s in skills if s.refined),
        )

        return skills
