"""AutoHarness static AST lint for code-as-action snippets.

Checks AST size, cyclomatic complexity, and a small blocklist of import/call
spellings, returning a :class:`~cohezion.contracts.VerificationResult`.

RESTORED 2026-08-12 from commit 66f5186d5. WHY: this module is absent from this
branch while ``agi/flume_vae.py`` imports it, leaving the FLUME VAE surface
unimportable (``ModuleNotFoundError: No module named
'cohezion.actioner.autoharness_verifier'``). Stdlib-only (``ast``, ``time``,
``typing``) plus ``cohezion.contracts``, so restoring it is additive.

THIS IS NOT A SECURITY BOUNDARY. Do not use it to decide whether untrusted code
is safe to execute. Measured 2026-08-12 against the restored implementation:

    from os import system        -> BLOCKED   (the one spelling in the blocklist)
    import os; os.system(...)    -> ACCEPTED
    __import__('os').system(...) -> ACCEPTED
    import subprocess; run(...)  -> ACCEPTED
    getattr(os, 'sys'+'tem')     -> ACCEPTED

The blocklist matches literal dotted import *names*, so the idiomatic
``import os`` form -- alias ``os``, which is not the string ``os.system`` --
passes untouched. Four of five bypasses require no cleverness at all. Those
limits are pinned by ``tests/actioner/test_autoharness_verifier.py`` so that a
future reader cannot mistake this for a sandbox; if you need one, it must be
out-of-process (bubblewrap/nsjail), not an AST walk.

Read it as what it soundly is: a complexity and hygiene lint whose signal is the
node count and cyclomatic complexity in ``metadata``.
"""

from __future__ import annotations

import ast
import time

from cohezion.contracts import CodeAsAction, VerificationResult, Verifier


class AutoHarnessVerifier(Verifier):
    """Static AST-based lint implementing zero-cost action inspection."""

    def __init__(
        self,
        max_ast_nodes: int = 500,
        max_cyclomatic_complexity: int = 30,
        disallowed_imports: set[str] | None = None,
    ) -> None:
        self.max_ast_nodes = max_ast_nodes
        self.max_cyclomatic_complexity = max_cyclomatic_complexity
        self.disallowed_imports = disallowed_imports or {
            "os.system",
            "subprocess.Popen",
            "shutil.rmtree",
            "ctypes",
        }

    def verify_code(self, source_code: str) -> VerificationResult:
        """Statically inspect source code AST for size/complexity invariants."""
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
        #    NOTE: literal-name matching only -- see the module docstring for the
        #    bypasses this does NOT catch. Not a safety boundary.
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
            if isinstance(
                node,
                (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert, ast.Try),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        if complexity > self.max_cyclomatic_complexity:
            errors.append(
                f"Cyclomatic complexity exceeds limit ({complexity} > {self.max_cyclomatic_complexity})"
            )

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
    """Concrete wrapper for lint-checked code-as-action snippets."""

    def __init__(
        self, name: str, source_code: str, verifier: AutoHarnessVerifier | None = None
    ) -> None:
        self._name = name
        self.source_code = source_code
        self.verifier = verifier or AutoHarnessVerifier()

    @property
    def name(self) -> str:
        return self._name

    def verify(self) -> VerificationResult:
        return self.verifier.verify_code(self.source_code)


__all__: list[str] = ["AutoHarnessVerifier", "ExecutableAction"]
