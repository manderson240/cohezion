"""
FLIER Verifier (Structural Energy)
==================================
Implements Fluid Latent Entanglement Routing (FLIER) verification logic.
Checks code structure, dependencies, and 'Entanglement' (Complexity/Coupling).

E_flier = E_circular + E_dangerous + E_coupling
"""

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FlierEnergy:
    """
    Calculates E_flier (Structural Integrity).
    """

    name = "E_flier"
    weight = 8.0

    def __init__(self):
        self.dangerous_modules = {"os", "sys", "subprocess", "shutil"}

    async def calculate_energy(
        self, solution: str, context: dict[str, Any]
    ) -> tuple[float, str]:
        """
        Analyze AST for structural issues.
        """
        try:
            tree = ast.parse(solution)
        except SyntaxError:
            return 0.0, "Syntax handled by E_syntax"

        energy = 0.0
        issues = []

        # 1. Check Imports
        imports = self._get_imports(tree)

        # Dangerous Imports Check
        # In Cohezion, we want to be careful with shell commands outside of specific utils
        dangerous_found = imports.intersection(self.dangerous_modules)
        if dangerous_found:
            # Soft constraint: warn but don't explode unless strict mode
            energy += 0.3
            issues.append(
                f"High-Risk Imports detected: {dangerous_found}. Ensure properly guardrailed."
            )

        # 2. Complexity Check (Cyclomatic - simplified as node count for now)
        # Assuming huge functions are 'High Energy' (Hard to maintain)
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > 500:  # Arbitrary threshold for a single snippet
            energy += 0.2
            issues.append(
                f"High Complexity (Nodes: {node_count}). Consider refactoring."
            )

        # 3. Class/Function Ratio (Encapsulation Check)
        # We prefer Classes/Functions over top-level script code
        has_class_or_def = any(
            isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in tree.body
        )
        if not has_class_or_def and node_count > 20:
            energy += 0.4
            issues.append(
                "Script-like structure detected. Wrap logic in Functions/Classes."
            )

        if energy == 0:
            return 0.0, "Structurally Sound."

        return min(1.0, energy), "; ".join(issues)

    def _get_imports(self, tree: ast.AST) -> set[str]:
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        return imports
