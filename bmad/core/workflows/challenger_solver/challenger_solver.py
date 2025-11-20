"""
Challenger/Solver Pattern Implementation
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Critique:
    score: float  # 0.0 to 1.0
    feedback: str
    issues: list[str]
    suggestions: list[str]

@dataclass
class ChallengerSolverResult:
    final_solution: str
    iterations: int
    critiques: list[Critique]
    success: bool

def challenger_solver_loop(
    problem: str,
    solver_fn: Callable[[str, Critique | None], str],
    challenger_fn: Callable[[str], Critique],
    max_iterations: int = 3,
    consensus_threshold: float = 0.8
) -> ChallengerSolverResult:
    """
    Execute the Challenger/Solver pattern.
    
    Args:
        problem: The problem statement
        solver_fn: Function that generates/refines solutions
        challenger_fn: Function that critiques solutions
        max_iterations: Maximum critique-fix cycles
        consensus_threshold: Minimum score to accept solution
        
    Returns:
        ChallengerSolverResult with final solution and metadata
    """
    critiques = []
    solution = solver_fn(problem, None)

    for iteration in range(max_iterations):
        critique = challenger_fn(solution)
        critiques.append(critique)

        if critique.score >= consensus_threshold:
            return ChallengerSolverResult(
                final_solution=solution,
                iterations=iteration + 1,
                critiques=critiques,
                success=True
            )

        # Fix based on critique
        solution = solver_fn(problem, critique)

    # Max iterations reached without consensus
    return ChallengerSolverResult(
        final_solution=solution,
        iterations=max_iterations,
        critiques=critiques,
        success=False
    )
