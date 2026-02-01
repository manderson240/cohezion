"""
Cohezion Crystal Protocol (EBMS Core)
=====================================
Implements the Kona-style Energy-Based Model System for deterministic, verified reasoning.
The 'Crystal' represents a state of 0-Energy (Maximum Coherence/Stability).

Logic:
1. Define Energy Functions E(x) where x is a solution/thought.
2. Minimize E(x) via iterative descent (Critique -> Refine).
3. E > 0 implies imperfect logic, syntax errors, or semantic drift.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

try:
    import numpy as np
except ImportError:
    np = None

# Placeholder for Ollama Client - will be replaced by actual client later
# or imported from a common util if it exists.
# For now, we assume a local ollama interface.

logger = logging.getLogger(__name__)


@dataclass
class EnergyProfile:
    """The Energy State of a Solution."""

    total_energy: float
    components: dict[str, float]
    critique: str  # The 'Gradient' - why is energy high?
    is_stable: bool  # True if total_energy < threshold


class EnergyFunction(Protocol):
    """Protocol for any module that wants to contribute to the System Energy."""

    name: str
    weight: float

    async def calculate_energy(
        self, solution: str, context: dict[str, Any]
    ) -> tuple[float, str]:
        """
        Calculate E(x) for the solution.
        Returns:
            energy (float): 0.0 to 1.0 (normalized).
            reason (str): Explanation for the energy level (the gradient).
        """
        ...


class SyntaxEnergy:
    """Checks for Python syntax errors. High Energy = Invalid Code."""

    name = "E_syntax"
    weight = 10.0  # Hard constraint

    async def calculate_energy(
        self, solution: str, context: dict[str, Any]
    ) -> tuple[float, str]:
        if not solution.strip():
            return 1.0, "Empty solution."

        # Basic check: Try to parse
        try:
            import ast

            ast.parse(solution)
            return 0.0, "Valid Syntax"
        except SyntaxError as e:
            return 1.0, f"Syntax Error: {str(e)}"
        except Exception as e:
            return 0.5, f"Parsing Error: {str(e)}"


class CohezionCrystal:
    """
    The Orchestrator of the Crystal Protocol.
    Manages the Descent Loop (Optimization) to reach a low-energy state.
    """

    def __init__(self, model_client: Any, energy_functions: list[EnergyFunction]):
        self.client = model_client  # e.g. OllamaWrapper
        self.energy_functions = energy_functions
        self.max_iterations = 5
        self.stability_threshold = 0.05

    async def minimize(
        self,
        initial_prompt: str,
        context: dict[str, Any] = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Run the Energy Descent loop.

        Args:
            initial_prompt: The user's request.
            context: Additional context (files, memory).
            temperature: Sampling temp for drafting.

        Returns:
            Best solution found and its trajectory.
        """
        context = context or {}
        trajectory = []

        # Step 0: Draft (x_0)
        # Using Qwen for speed/code
        current_solution = await self.client.generate(
            model="qwen3-coder:32b", prompt=initial_prompt, temperature=temperature
        )

        best_solution = current_solution
        min_energy = float("inf")

        for t in range(self.max_iterations):
            # Step 1: Calculate Energy E(x_t)
            profile = await self._compute_total_energy(current_solution, context)
            trajectory.append(
                {"t": t, "energy": profile.total_energy, "critique": profile.critique}
            )

            logger.info(f"Crystal Iteration {t}: Energy={profile.total_energy:.4f}")

            # Update Best
            if profile.total_energy < min_energy:
                min_energy = profile.total_energy
                best_solution = current_solution

            # Check Convergence
            if profile.is_stable:
                logger.info("Crystal Stabilized (Zero Energy State).")
                break

            # Step 2: Generate Gradient (Critique -> Refine)
            # Use DeepSeek for deep reasoning on the critique if energy is high
            gradient_prompt = f"""
            ORIGINAL TASK: {initial_prompt}

            CURRENT SOLUTION:
            {current_solution}

            CRITIQUE (Energy Profile):
            {profile.critique}

            TASK: Refine the solution to minimize the Energy. Fix the specific issues identified in the critique.
            Output ONLY the refined code/text.
            """

            current_solution = await self.client.generate(
                model="qwen3-coder:32b",  # Refine with coder
                prompt=gradient_prompt,
                temperature=0.2,  # Low temp for precision fixes
            )

        return {
            "solution": best_solution,
            "energy": min_energy,
            "trajectory": trajectory,
            "converged": min_energy < self.stability_threshold,
        }

    async def _compute_total_energy(
        self, solution: str, context: dict[str, Any]
    ) -> EnergyProfile:
        """Sum specific energies to get Total Hamiltonian."""
        total = 0.0
        components = {}
        critiques = []

        for e_func in self.energy_functions:
            score, reason = await e_func.calculate_energy(solution, context)
            weighted_score = score * e_func.weight
            total += weighted_score

            components[e_func.name] = weighted_score
            if score > 0:
                critiques.append(f"[{e_func.name}]: {reason}")

        is_stable = total < self.stability_threshold
        critique_text = "\n".join(critiques) if critiques else "Solution is stable."

        return EnergyProfile(
            total_energy=total,
            components=components,
            critique=critique_text,
            is_stable=is_stable,
        )


# Mock Client for initial implementation if needed,
# or we can pull the real Swarm one later.
class MockOllamaClient:
    async def generate(self, model, prompt, temperature=0.7):
        return "# Mock Solution\ndef foo(): pass"


if __name__ == "__main__":
    # Simple test
    async def main():
        logging.basicConfig(level=logging.INFO)
        crystal = CohezionCrystal(MockOllamaClient(), [SyntaxEnergy()])
        result = await crystal.minimize("Write a python function provided via Mock.")
        print("Result Energy:", result["energy"])

    asyncio.run(main())
