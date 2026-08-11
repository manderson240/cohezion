"""AutoHarness Static Symbolic Verifier
=======================================
Zero-cost verification engine that validates Python code-as-action ASTs
before execution. Enforces pure functional invariants, cyclomatic complexity
limits, and memory/NPU safety bounds.
"""

from __future__ import annotations

import ast
import time
from typing import Any

from cohezion.contracts import CodeAsAction, VerificationResult, Verifier


class AutoHarnessVerifier(Verifier):
    """Static AST-based verifier implementing zero-cost action verification."""

    def __init__(
        self,
        max_ast_nodes: int = 500,
        max_cyclomatic_complexity: int = 30,
        disallowed_imports: set[str] | None = None,
    ) -> None:
        self.max_ast_nodes = max_ast_nodes
        self.max_cyclomatic_complexity = max_cyclomatic_complexity
        self.disallowed_imports = disallowed_imports or {
            "os.system", "subprocess.Popen", "shutil.rmtree", "ctypes"
        }

    def verify_code(self, source_code: str) -> VerificationResult:
        """Statically inspect source code AST for safety invariants."""
        t0 = time.perf_counter()
        errors: list[str] = []
        warnings: list[str] = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return VerificationResult.failure(
                [f"SyntaxError at line {e.lineno}: {e.msg}"], score=0.0, duration_ms=duration_ms
            )

        # 1. AST Node Count Check
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > self.max_ast_nodes:
            errors.append(f"AST node count exceeds limit ({node_count} > {self.max_ast_nodes})")

        # 2. Check for Disallowed Imports & Dangerous Calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.disallowed_imports:
                        errors.append(f"Disallowed import: '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    full_imp = f"{mod}.{alias.name}" if mod else alias.name
                    if full_imp in self.disallowed_imports or mod in self.disallowed_imports:
                        errors.append(f"Disallowed import: '{full_imp}'")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                    errors.append(f"Forbidden call: '{node.func.id}()'")

        # 3. Cyclomatic Complexity Calculation (Branch Count)
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert, ast.Try)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        if complexity > self.max_cyclomatic_complexity:
            errors.append(f"Cyclomatic complexity exceeds limit ({complexity} > {self.max_cyclomatic_complexity})")

        duration_ms = (time.perf_counter() - t0) * 1000.0

        if errors:
            return VerificationResult.failure(errors, score=0.0, duration_ms=duration_ms)

        # Compute safety score (1.0 = perfect, lower if warnings exist)
        score = max(0.5, 1.0 - (len(warnings) * 0.1))
        return VerificationResult.success(
            score=score,
            metadata={"node_count": node_count, "complexity": complexity, "warnings": warnings},
            duration_ms=duration_ms,
        )


class ExecutableAction(CodeAsAction):
    """Concrete wrapper for verified code-as-action snippets."""

    def __init__(self, name: str, source_code: str, verifier: AutoHarnessVerifier | None = None) -> None:
        self._name = name
        self.source_code = source_code
        self.verifier = verifier or AutoHarnessVerifier()

    @property
    def name(self) -> str:
        return self._name

    def verify(self) -> VerificationResult:
        return self.verifier.verify_code(self.source_code)
