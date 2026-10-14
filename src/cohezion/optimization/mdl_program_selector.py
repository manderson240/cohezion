"""Minimum Description Length (MDL) Program Selector for ARC-AGI Program Synthesis.

First-Principles Objective:
In accordance with Algorithmic Information Theory (Solomonoff, Kolmogorov, Chaitin),
the true generative rule explaining a small set of demonstration examples is the program
that minimizes the two-part Minimum Description Length (MDL):

    MDL(P, D) = L(P) + L(D | P)

Where:
- L(P) is the Kolmogorov complexity (code length, AST node complexity, syntactic entropy).
- L(D | P) is the empirical error (0 if all training pairs match, infinity otherwise).

When multiple programs pass the demonstration examples, the program with minimal L(P)
is mathematically most likely to generalize to unseen test inputs without overfitting
to accidental public sample quirks.
"""

from __future__ import annotations

import ast
import math
from typing import Any


class ASTComplexityVisitor(ast.NodeVisitor):
    """Measures syntactic complexity, node counts, and nesting depth of Python AST."""

    def __init__(self) -> None:
        self.node_count: int = 0
        self.branch_count: int = 0
        self.loop_count: int = 0
        self.constant_count: int = 0
        self.max_depth: int = 0
        self._current_depth: int = 0

    def generic_visit(self, node: ast.AST) -> None:
        self.node_count += 1
        self._current_depth += 1
        if self._current_depth > self.max_depth:
            self.max_depth = self._current_depth

        if isinstance(node, (ast.If, ast.IfExp)):
            self.branch_count += 1
        elif isinstance(node, (ast.For, ast.While, ast.ListComp, ast.DictComp)):
            self.loop_count += 1
        elif isinstance(node, ast.Constant):
            self.constant_count += 1

        super().generic_visit(node)
        self._current_depth -= 1


class MDLProgramSelector:
    """Evaluates and ranks program synthesis candidates based on Kolmogorov/MDL complexity."""

    def __init__(
        self,
        weight_nodes: float = 1.0,
        weight_depth: float = 2.5,
        weight_branches: float = 3.0,
        weight_constants: float = 0.5,
    ) -> None:
        self.weight_nodes = weight_nodes
        self.weight_depth = weight_depth
        self.weight_branches = weight_branches
        self.weight_constants = weight_constants

    def compute_complexity(self, code: str) -> dict[str, float]:
        """Compute the Kolmogorov/MDL description length score for a Python code snippet."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"mdl_score": float("inf"), "is_valid": False, "error": "SyntaxError"}

        visitor = ASTComplexityVisitor()
        visitor.visit(tree)

        # Calculate MDL description length
        # Penalizes deep nesting and excessive branching (heuristics/lookup tables)
        mdl_score = (
            self.weight_nodes * visitor.node_count
            + self.weight_depth * math.pow(visitor.max_depth, 1.2)
            + self.weight_branches * math.pow(visitor.branch_count + 1, 1.5)
            + self.weight_constants * visitor.constant_count
        )

        return {
            "mdl_score": round(mdl_score, 2),
            "is_valid": True,
            "node_count": visitor.node_count,
            "max_depth": visitor.max_depth,
            "branch_count": visitor.branch_count,
            "loop_count": visitor.loop_count,
            "constant_count": visitor.constant_count,
        }

    def rank_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank candidate solutions by verified correctness, then by minimal MDL score.

        Each candidate dict must contain:
        - 'code': str
        - 'all_train_passed': bool
        """
        evaluated = []
        for cand in candidates:
            code = cand.get("code", "")
            metrics = self.compute_complexity(code)
            all_passed = cand.get("all_train_passed", False)

            # Combined Pareto score: correctness is mandatory, then minimal MDL
            score = metrics["mdl_score"] if all_passed and metrics["is_valid"] else float("inf")
            evaluated.append({
                **cand,
                **metrics,
                "pareto_score": score,
            })

        evaluated.sort(key=lambda x: x["pareto_score"])
        return evaluated
