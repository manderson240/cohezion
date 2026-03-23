import re
from dataclasses import dataclass

import numpy as np


@dataclass
class MathProblemState:
    """
    12D State Vector for Mathematical Problems.
    Refined for High-Fidelity Perception.
    """

    # 3 Spatial: Problem 'Geometry' (Structural complexity)
    structural_depth: float = 0.0  # Max nesting of LaTeX braces
    token_density: float = 0.0  # Ratio of math tokens to text
    constraint_density: float = 0.0  # Constraints per variable

    # 1 Time: Temporal 'Flow' (Expected reasoning steps)
    reasoning_complexity: float = 0.0

    # 8 Brane: Domain and Character
    algebra: float = 0.0
    number_theory: float = 0.0
    geometry: float = 0.0
    combinatorics: float = 0.0
    calculus: float = 0.0
    logic_type: float = 0.0  # 0: Calculation, 1: Optimization, 2: Proof
    abstraction_level: float = 0.0  # Presence of abstract structures (groups, rings, etc.)
    stability_heuristic: float = 0.0  # Expected consistency across runs

    def to_vector(self) -> np.ndarray:
        return np.array(
            [
                self.structural_depth,
                self.token_density,
                self.constraint_density,
                self.reasoning_complexity,
                self.algebra,
                self.number_theory,
                self.geometry,
                self.combinatorics,
                self.calculus,
                self.logic_type,
                self.abstraction_level,
                self.stability_heuristic,
            ]
        )


class MathParser:
    """
    High-fidelity LaTeX Math Parser for AIMO.
    Extracts structured data and generates manifold state vectors.
    """

    def __init__(self):
        self.domains = {
            "algebra": [
                r"\b(solve|equation|function|polynomial|root|coefficient|quadratic|cubic|inequality)\b",
                r"[xyzabc]",
            ],
            "number_theory": [
                r"\b(integer|divisor|prime|modular|congruent|gcd|lcm|divides|mod|remainder|coprime)\b",
                r"n =",
            ],
            "geometry": [
                r"\b(triangle|circle|area|angle|perpendicular|parallel|radius|tangent|chord|vertex|polygon)\b"
            ],
            "combinatorics": [
                r"\b(number of ways|how many|permutation|combination|probability|subset|distinct|arrangement|die|dice|coin)\b"
            ],
            "calculus": [
                r"\b(limit|integral|derivative|sum|sequence|series|convergence|continuity|differentiable)\b"
            ],
        }

    def clean_latex(self, text: str) -> str:
        """Removes unnecessary LaTeX formatting while preserving math context."""
        text = text.replace(r"\\", " ")
        text = re.sub(r"\\(text|textbf|textit)\{([^}]*)\}", r"\2", text)
        return text

    def extract_equations(self, text: str) -> list[str]:
        """Identifies potential equations for symbolic processing."""
        # Look for content between $...$ or within \begin{equation}...
        matches = re.findall(r"\$([^$]+)\$", text)
        equations = [m for m in matches if "=" in m or "<" in m or ">" in m]
        return equations

    def extract_variables(self, text: str) -> set[str]:
        """Identifies unique mathematical variables."""
        # Simple heuristic: single letters in math mode that aren't common commands
        math_content = " ".join(re.findall(r"\$([^$]+)\$", text))
        vars = set(re.findall(r"\b([a-zA-Z])\b", math_content))
        # Exclude common LaTeX letters used as commands if any
        vars -= {"d", "e", "i"}  # Often used for dx, exp, imaginary unit
        return vars

    def get_max_nesting(self, text: str) -> int:
        """Calculates maximum depth of nested braces in LaTeX."""
        max_depth = 0
        current_depth = 0
        for char in text:
            if char == "{":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == "}":
                current_depth -= 1
        return max_depth

    def parse(self, problem_text: str) -> MathProblemState:
        state = MathProblemState()
        clean_text = self.clean_latex(problem_text)

        # 1. Structural Metrics
        state.structural_depth = min(1.0, self.get_max_nesting(problem_text) / 5.0)
        math_tokens = len(re.findall(r"(\$|\\|\{|\^|_|=)", problem_text))
        state.token_density = min(1.0, math_tokens / (len(problem_text.split()) + 1))

        equations = self.extract_equations(problem_text)
        variables = self.extract_variables(problem_text)
        state.constraint_density = min(1.0, len(equations) / (len(variables) + 1))

        # 2. Domain Probabilities
        domain_matches = {}
        for domain, patterns in self.domains.items():
            matches = 0
            for pattern in patterns:
                matches += len(re.findall(pattern, clean_text, re.IGNORECASE))
            domain_matches[domain] = matches
            setattr(state, domain, min(1.0, matches / 4.0))

        # 3. Logic and Abstraction
        if re.search(r"\b(maximum|minimum|optimum|largest|smallest)\b", clean_text, re.IGNORECASE):
            state.logic_type = 0.5  # Optimization
        elif re.search(r"\b(prove|show that|determine if)\b", clean_text, re.IGNORECASE):
            state.logic_type = 1.0  # Proof

        if re.search(
            r"\b(ring|field|group|space|manifold|isomorphic)\b", clean_text, re.IGNORECASE
        ):
            state.abstraction_level = 1.0

        # 4. Temporal/Complexity Flow
        state.reasoning_complexity = (
            state.structural_depth + state.token_density + state.constraint_density
        ) / 3.0

        # 5. Stability (Inverse of complexity/ambiguity)
        state.stability_heuristic = 1.0 - (state.reasoning_complexity * 0.5)

        return state


if __name__ == "__main__":
    parser = MathParser()
    sample = "Let $n = 3^3 \\cdot 11^3$. Find the number of distinct positive divisors of $n$."
    state = parser.parse(sample)
    print(f"Problem: {sample}")
    print(f"State Vector: {state.to_vector()}")
    print(f"Variables: {parser.extract_variables(sample)}")
    print(f"Equations: {parser.extract_equations(sample)}")
