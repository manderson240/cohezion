"""Self-Evolving Refiner - Implementation of the Read-Write Reflective Learning loop.

This module implements the self-evolution mechanism inspired by Memento-Skills,
where failures are treated as training signals to rewrite skill specifications.

The loop follows the paradigm:
  Read (Skill Selection) -> Execute (Tool Use) -> Reflect (Failure Attribution) -> Write (Skill Mutation)

In Cohezion, this is augmented by the Mereon System:
  - E7 Sector (Core): Refinements focus on technical precision and logic.
  - E8 Sector (Boundary): Refinements focus on conceptual alignment and abstraction.
  - Focusing Sphere: Refinements bridge the gap between abstract theory and concrete execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cohezion.physics.mereon_projector import MereonProjector


logger = logging.getLogger(__name__)


@dataclass
class FailureAnalysis:
    """Analysis of why a skill execution failed."""

    skill_name: str
    error_trace: str
    attribution: str  # e.g., "prompt_ambiguity", "logic_error", "missing_tool"
    suggested_fix: str
    confidence: float


class SelfEvolvingRefiner:
    """
    Advanced refiner that mutates skill specifications based on a
    Read-Execute-Reflect-Write loop.
    """

    def __init__(self, projector: MereonProjector | None = None):
        self.projector = projector or MereonProjector()
        self.skills_dir = Path(__file__).parent.parent / "skills"

    async def reflect_and_mutate(
        self, skill_name: str, execution_trace: str, outcome: str, context: np.ndarray
    ) -> bool:
        """
        The 'Write' phase of the reflective loop.

        1. Reflect: Analyze the trace to attribute the failure.
        2. Mutate: Rewrite the skill's instructions or prompt.
        3. Validate: Ensure the mutation doesn't break existing coherence.
        """
        # 1. Determine the topological regime for the reflection strategy
        # We lift the current context to S3 to see where the failure happened
        lift = self.projector.lift(context)
        regime = lift.vertex_type  # 'A', 'B', 'C', or 'Inner'

        # 2. Perform failure attribution (Reflect)
        analysis = await self._analyze_failure(skill_name, execution_trace, outcome)
        if not analysis:
            return False

        # 3. Apply mutation based on regime (Write)
        success = await self._apply_mutation(skill_name, analysis, regime)

        if success:
            logger.info(f"Skill {skill_name} evolved in {regime} regime: {analysis.attribution}")

        return success

    async def _analyze_failure(
        self, skill_name: str, trace: str, outcome: str
    ) -> FailureAnalysis | None:
        """
        Simulates the LLM-based failure attribution selector.
        In a full implementation, this would call an LLM to analyze the trace.
        """
        # Logic to identify if it's a prompt issue or a code issue
        if "Timeout" in trace or "Max depth" in trace:
            attribution = "execution_inefficiency"
            fix = "Optimize the multi-step reasoning path to reduce token depth."
        elif "Unexpected token" in trace:
            attribution = "syntax_error"
            fix = "Add a guardrail to validate output format before finalization."
        else:
            attribution = "conceptual_misalignment"
            fix = "Refine the skill's conceptual boundary to better match the user's intent."

        return FailureAnalysis(
            skill_name=skill_name,
            error_trace=trace,
            attribution=attribution,
            suggested_fix=fix,
            confidence=0.85,
        )

    async def _apply_mutation(
        self, skill_name: str, analysis: FailureAnalysis, regime: str
    ) -> bool:
        """
        Rewrites the skill specification based on the regime.
        - E7 (A-type): Focus on technical constraints.
        - E8 (C-type): Focus on conceptual definitions.
        - Focusing Sphere (Inner): Focus on the bridge between a and b.
        """
        prime_file = self.skills_dir / f"{skill_name.upper()}_PRIME.md"
        if not prime_file.exists():
            return False

        # Offload blocking I/O to thread pool
        def _mutate_file():
            content = prime_file.read_text()

            # Strategy based on Mereon Regime
            mutation_prefix = ""
            if regime == "A":  # Core/Technical
                mutation_prefix = "TECHNICAL REFINEMENT: "
            elif regime == "C":  # Boundary/Abstract
                mutation_prefix = "CONCEPTUAL ALIGNMENT: "
            elif regime == "Inner":  # Focusing Sphere
                mutation_prefix = "BRIDGE OPTIMIZATION: "
            else:
                mutation_prefix = "GENERAL IMPROVEMENT: "

            refinement = f"\\n\\n### Evolutionary Mutation ({mutation_prefix})\\n- **Attribution**: {analysis.attribution}\\n- **Fix**: {analysis.suggested_fix}\\n"

            # We prepend the mutation to the top of the skill's 'Instructions' section
            # to ensure the LLM sees the most recent evolution first.
            if "## Instructions" in content:
                new_content = content.replace("## Instructions", f"## Instructions\\n{refinement}")
            else:
                new_content = content + refinement

            prime_file.write_text(new_content)
            return True

        try:
            import asyncio
            return await asyncio.to_thread(_mutate_file)
        except Exception as e:
            logger.debug(f"Mutation I/O failed: {e}")
            return False

    async def generate_new_skill(self, task_goal: str, context: np.ndarray) -> str:
        """
        Implements 'Skill Discovery' when no existing skill is suitable.
        Creates a new PRIME skill definition from scratch.
        """
        # Calculate the 4D seed based on the task context
        lift = self.projector.lift(context)

        # Use the lifted w-coordinate to determine the initial "complexity" of the skill
        # Higher w (poles) -> More atomic, Lower w (equator) -> More complex/integrated
        complexity = "Atomic" if abs(lift.w) > 0.5 else "Compound"

        skill_name = f"EVOLVED_{hash(task_goal) % 10000}"
        prime_path = self.skills_dir / f"{skill_name}_PRIME.md"

        content = f"""# {skill_name}
## Description: {task_goal}
## Type: {complexity}
## Instructions:
Initial generation based on context {lift.w:.4f}.
"""
        # Offload blocking I/O to thread pool
        def _write_skill():
            prime_path.write_text(content)
            return True
            
        try:
            import asyncio
            await asyncio.to_thread(_write_skill)
        except Exception as e:
            logger.error(f"Skill discovery writing failed: {e}")

        return skill_name
