"""Significant Journey Driver - Real Agent Execution.

Replaces synthetic data generation with actual CompoundExecutor calls,
capturing meaningful agent journeys with semantic context.

Usage:
    uv run python -m scripts.drivers.significant_journey_driver \
        --count 100 \
        --skills JOURNEY_TRACKING_PRIME,FLUME_METHODOLOGY_PRIME \
        --output-dir data/significant_journeys
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class SignificantJourneyConfig:
    """Configuration for significant journey capture."""

    journey_count: int = 100
    max_concurrent: int = 4  # Respect Ollama limits
    skills: list[str] = field(default_factory=lambda: ["JOURNEY_TRACKING_PRIME"])
    output_dir: Path = field(default_factory=lambda: Path("data/significant_journeys"))
    enable_retries: bool = True
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout: float = 30.0


@dataclass
class JourneyStep:
    """Single step in a multi-step journey."""

    step_number: int
    task_description: str
    execution_result: ExecutionResult
    trajectory_12d: list[float]
    phi_score: float
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignificantJourney:
    """Complete significant journey with multiple steps."""

    journey_id: str
    skill_domain: str
    intent: str
    steps: list[JourneyStep]
    start_time: float
    end_time: float
    final_phi: float
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillTaskGenerator:
    """Generate meaningful tasks from PRIME skills."""

    def __init__(self, skills_dir: Path = Path("src/cohezion/skills")):
        self.skills_dir = skills_dir
        self.skill_cache: dict[str, dict] = {}

    def load_skill(self, skill_name: str) -> dict:
        """Load and parse a PRIME skill file."""
        if skill_name in self.skill_cache:
            return self.skill_cache[skill_name]

        skill_path = self.skills_dir / f"{skill_name}.md"
        if not skill_path.exists():
            logger.warning(f"Skill not found: {skill_path}")
            return {}

        content = skill_path.read_text()

        # Extract key sections
        skill_data = {
            "name": skill_name,
            "domain_expertise": self._extract_section(content, "DOMAIN EXPERTISE"),
            "key_concepts": self._extract_section(content, "KEY CONCEPTS"),
            "instructions": self._extract_section(content, "INSTRUCTION"),
        }

        self.skill_cache[skill_name] = skill_data
        return skill_data

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract content from a markdown section."""
        pattern = rf"## {section_name}\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def generate_task(self, skill_name: str, complexity: str = "medium") -> str:
        """Generate a meaningful task from skill context."""
        skill = self.load_skill(skill_name)
        if not skill:
            return f"Explain the concept of {skill_name}"

        expertise = skill.get("domain_expertise", "")
        concepts = skill.get("key_concepts", "")

        # Task templates based on complexity
        templates = {
            "simple": [
                "Explain the key concept of {topic} in simple terms.",
                "What is {topic} and why does it matter?",
                "Define {topic} and give one example.",
            ],
            "medium": [
                "Analyze {topic} and explain its relationship to {related}.",
                "Compare {topic} with alternative approaches. What are the trade-offs?",
                "How does {topic} work? Describe the mechanism and key components.",
                "Apply {topic} to a practical scenario. What would you do?",
            ],
            "complex": [
                "Design a system using {topic} that handles {constraint}. Consider edge cases.",
                "Critique the current implementation of {topic}. What are the failure modes?",
                "Synthesize {topic} with {related} to create a novel approach.",
                "Given conflicting requirements X and Y, how would {topic} resolve this?",
            ],
            "edge": [
                "What happens when {topic} encounters an impossible constraint?",
                "Design {topic} to handle adversarial input while maintaining guarantees.",
                "Given limited resources, how would you approximate {topic}?",
            ],
        }

        template = random.choice(templates.get(complexity, templates["medium"]))

        # Extract topics from expertise/concepts
        topics = self._extract_topics(expertise + " " + concepts)
        topic = random.choice(topics) if topics else skill_name.replace("_PRIME", "").replace("_", " ")

        # Find related concepts
        related = random.choice(topics) if len(topics) > 1 else "existing approaches"

        # Fill template
        return template.format(
            topic=topic,
            related=related,
            constraint=self._generate_constraint(),
        )

    def _extract_topics(self, text: str) -> list[str]:
        """Extract key topics from skill text."""
        # Look for capitalized terms and technical phrases
        patterns = [
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",  # Capitalized phrases
            r"\b[a-z_]+(?:_[a-z]+)+\b",  # Snake_case terms
        ]

        topics = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            topics.update(m for m in matches if len(m) > 3)

        return list(topics)[:20]  # Limit to top 20

    def _generate_constraint(self) -> str:
        """Generate a realistic constraint."""
        constraints = [
            "limited memory",
            "real-time requirements",
            "adversarial inputs",
            "no external dependencies",
            "distributed execution",
            "energy efficiency",
            "maintainability",
            "regulatory compliance",
        ]
        return random.choice(constraints)


class RealExecutionDriver:
    """Driver for capturing significant journeys with real execution."""

    def __init__(self, config: SignificantJourneyConfig | None = None):
        self.config = config or SignificantJourneyConfig()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.task_generator = SkillTaskGenerator()
        self.tracker = JourneyTracker()

        # Will initialize executor in async context
        self.executor: CompoundExecutor | None = None
        self.mcp_client: MCPClient | None = None

        # Statistics
        self.completed_journeys = 0
        self.failed_journeys = 0
        self.total_steps = 0

    async def initialize(self):
        """Initialize async components."""
        self.mcp_client = MCPClient()
        self.executor = CompoundExecutor(
            mcp_client=self.mcp_client,
            enable_guardrails=True,
        )
        logger.info("RealExecutionDriver initialized")

    async def execute_single_journey(
        self,
        skill: str,
        complexity: str,
        journey_id: str,
    ) -> SignificantJourney | None:
        """Execute a single significant journey with real LLM calls."""
        logger.info(f"Starting journey {journey_id} with skill {skill} ({complexity})")

        start_time = time.time()
        steps: list[JourneyStep] = []

        # Generate task from skill
        task = self.task_generator.generate_task(skill, complexity)
        intent = task[:100] + "..." if len(task) > 100 else task

        # Determine number of steps based on complexity
        step_counts = {"simple": 1, "medium": 2, "complex": 3, "edge": 3}
        num_steps = step_counts.get(complexity, 2)

        for step_num in range(num_steps):
            # Generate step-specific task
            if step_num == 0:
                step_task = task
            else:
                step_task = f"Building on previous analysis: {task}\n\nStep {step_num + 1}: Deepen the analysis by considering implementation details."

            try:
                # REAL EXECUTION with timeout
                result = await asyncio.wait_for(
                    self._execute_with_retry(skill, step_task),
                    timeout=self.config.timeout,
                )

                # Track execution as trajectory point
                trajectory = self._compute_trajectory(result, step_task)

                step = JourneyStep(
                    step_number=step_num + 1,
                    task_description=step_task,
                    execution_result=result,
                    trajectory_12d=trajectory,
                    phi_score=self._compute_phi_score(result),
                    timestamp=time.time(),
                    metadata={
                        "skill": skill,
                        "complexity": complexity,
                        "tokens_used": result.token_metrics.get("total_tokens", 0) if result.token_metrics else 0,
                    },
                )
                steps.append(step)
                self.total_steps += 1

                logger.debug(f"  Step {step_num + 1} complete: phi={step.phi_score:.3f}")

            except TimeoutError:
                logger.warning(f"  Step {step_num + 1} timed out")
                steps.append(self._create_error_step(step_num + 1, step_task, "timeout"))

            except Exception as e:
                logger.error(f"  Step {step_num + 1} failed: {e}")
                steps.append(self._create_error_step(step_num + 1, step_task, str(e)))

        end_time = time.time()

        # Compute aggregate metrics
        phi_scores = [s.phi_score for s in steps if s.phi_score > 0]
        final_phi = sum(phi_scores) / len(phi_scores) if phi_scores else 0.0
        success = all(s.execution_result.success for s in steps)

        return SignificantJourney(
            journey_id=journey_id,
            skill_domain=skill,
            intent=intent,
            steps=steps,
            start_time=start_time,
            end_time=end_time,
            final_phi=final_phi,
            success=success,
            metadata={
                "num_steps": len(steps),
                "complexity": complexity,
                "duration_seconds": end_time - start_time,
            },
        )

    async def _execute_with_retry(self, skill: str, task: str) -> ExecutionResult:
        """Execute task with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                if self.executor is None:
                    raise RuntimeError("Executor not initialized")

                return await self.executor.execute_skill(
                    skill_name=skill,
                    prompt=task,
                    operation_type="generate",
                )

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise

        raise RuntimeError("Max retries exceeded")

    def _compute_trajectory(self, result: ExecutionResult, task: str) -> list[float]:
        """Compute 12D trajectory from execution result."""
        # Extract metrics
        coherence = result.metrics.get("coherence", 0.5)
        efficiency = result.token_metrics.get("cache_hit_rate", 0.5) if result.token_metrics else 0.5

        # Generate trajectory using JourneyTracker
        latent = self.tracker.text_to_latent(task)
        projection = self.tracker.holographic_project(latent)

        # Modulation (using analyze as default)
        modulation = self.tracker._modulation_profiles.get("analyze", self.tracker._modulation_profiles["transform"])

        quality_weight = 0.5 * coherence + 0.5 * efficiency
        trajectory = projection * (1.0 - quality_weight) + modulation * quality_weight
        trajectory = np.clip(trajectory, 0.0, 1.0)

        return trajectory.tolist()

    def _compute_phi_score(self, result: ExecutionResult) -> float:
        """Compute journey quality score."""
        coherence = result.metrics.get("coherence", 0.5)
        efficiency = result.token_metrics.get("cache_hit_rate", 0.5) if result.token_metrics else 0.5

        # Phi = coherence * 0.5 + efficiency * 0.3 + convergence * 0.2
        # For single step, convergence is 1.0
        phi = coherence * 0.5 + efficiency * 0.3 + 0.2
        return min(phi, 1.0)

    def _create_error_step(self, step_num: int, task: str, error: str) -> JourneyStep:
        """Create an error step when execution fails."""
        return JourneyStep(
            step_number=step_num,
            task_description=task,
            execution_result=ExecutionResult(
                success=False,
                output="",
                metrics={},
                duration_seconds=0.0,
            ),
            trajectory_12d=[0.0] * 12,  # Null trajectory
            phi_score=0.0,
            timestamp=time.time(),
            metadata={"error": error},
        )

    async def run(self):
        """Main execution loop."""
        await self.initialize()

        logger.info(f"Starting {self.config.journey_count} significant journeys")
        logger.info(f"Skills: {', '.join(self.config.skills)}")
        logger.info(f"Max concurrent: {self.config.max_concurrent}")

        # Create journey specifications
        journeys_to_run = []
        for i in range(self.config.journey_count):
            skill = random.choice(self.config.skills)
            complexity = random.choice(["simple", "medium", "medium", "complex", "edge"])
            journey_id = f"journey_{i:05d}_{int(time.time())}"
            journeys_to_run.append((skill, complexity, journey_id))

        # Execute with semaphore-based concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def execute_with_limit(skill, complexity, journey_id):
            async with semaphore:
                journey = await self.execute_single_journey(skill, complexity, journey_id)
                if journey:
                    await self._persist_journey(journey)
                    if journey.success:
                        self.completed_journeys += 1
                    else:
                        self.failed_journeys += 1
                return journey

        # Run all journeys
        tasks = [execute_with_limit(s, c, j) for s, c, j in journeys_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Finalize
        await self._finalize()

        return results

    async def _persist_journey(self, journey: SignificantJourney):
        """Persist journey to Parquet."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Convert to records (one per step)
        records = []
        for step in journey.steps:
            record = {
                "journey_id": journey.journey_id,
                "skill_domain": journey.skill_domain,
                "intent": journey.intent,
                "step_number": step.step_number,
                "task_description": step.task_description,
                "output": step.execution_result.output,
                "success": step.execution_result.success,
                "phi_score": step.phi_score,
                "duration_seconds": step.execution_result.duration_seconds,
                **{f"dim_{i}": v for i, v in enumerate(step.trajectory_12d)},
            }
            records.append(record)

        # Write to Parquet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.config.output_dir / f"journey_{journey.journey_id}_{timestamp}.parquet"

        table = pa.Table.from_pylist(records)
        pq.write_table(table, filename, compression="zstd")

        logger.debug(f"Persisted journey {journey.journey_id}: {len(records)} steps")

    async def _finalize(self):
        """Finalize and report statistics."""
        logger.info("=" * 60)
        logger.info("SIGNIFICANT JOURNEY CAPTURE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Completed: {self.completed_journeys}")
        logger.info(f"Failed: {self.failed_journeys}")
        logger.info(f"Total Steps: {self.total_steps}")
        logger.info(f"Output: {self.config.output_dir}")

    async def shutdown(self):
        """Clean up resources."""
        if self.executor:
            # Any cleanup needed
            pass


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Significant Journey Capture Driver")
    parser.add_argument("--count", type=int, default=100, help="Number of journeys")
    parser.add_argument("--skills", type=str, default="JOURNEY_TRACKING_PRIME", help="Comma-separated skill names")
    parser.add_argument("--output-dir", type=Path, default=Path("data/significant_journeys"))
    parser.add_argument("--max-concurrent", type=int, default=4, help="Max concurrent executions")
    parser.add_argument("--timeout", type=float, default=30.0, help="Execution timeout")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    skills = [s.strip() for s in args.skills.split(",")]

    config = SignificantJourneyConfig(
        journey_count=args.count,
        skills=skills,
        output_dir=args.output_dir,
        max_concurrent=args.max_concurrent,
        timeout=args.timeout,
    )

    driver = RealExecutionDriver(config)
    try:
        asyncio.run(driver.run())
    finally:
        asyncio.run(driver.shutdown())


if __name__ == "__main__":
    main()
