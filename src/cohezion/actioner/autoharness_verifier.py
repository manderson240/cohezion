"""AutoHarness AST Bytecode Policy Verifier & Semantic Guardian
================================================================
Hardened against adversarial bypasses identified in the local multi-perspective review:
1. Indirect builtins & inheritance traversal (`__builtins__`, `__subclasses__`, `__dict__`).
2. Memory exhaustion generator explosions (unbounded list/generator multiplication).
3. Dynamic import evasion (`__import__`, `eval`, `exec`).
"""

from __future__ import annotations

import ast
import logging
import time

from cohezion.contracts import CodeAsAction, VerificationResult, Verifier


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("autoharness_verifier")

FORBIDDEN_ATTRIBUTES: set[str] = {
    "__builtins__",
    "__subclasses__",
    "__dict__",
    "__globals__",
    "__class__",
    "__base__",
    "__bases__",
}

FORBIDDEN_CALLS: set[str] = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "os.system",
    "subprocess.Popen",
    "shutil.rmtree",
}


class AutoHarnessASTSecurityValidator(ast.NodeVisitor):
    """Deep AST Semantic Validator preventing code injection and sandbox escapes."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.startswith("os.system") or alias.name in {"subprocess", "shutil", "sys"}:
                self.violations.append(f"Disallowed import: '{alias.name}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and (node.module.startswith("os") or node.module in {"subprocess", "shutil", "sys"}):
            self.violations.append(f"Disallowed import: '{node.module}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(
                f"Forbidden attribute access: '{node.attr}' at line {node.lineno}"
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                func_name = f"{node.func.value.id}.{node.func.attr}"
            else:
                func_name = node.func.attr

        if func_name in FORBIDDEN_CALLS:
            self.violations.append(f"Forbidden call: '{func_name}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        # Check for memory exhaustion attacks: [0] * (10**6), [0] * 10000000, etc.
        if isinstance(node.op, ast.Mult):
            # Check constant right multiplier
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
                if node.right.value > 100_000:
                    self.violations.append(
                        f"Potential memory exhaustion multiplier ({node.right.value}) at line {node.lineno}"
                    )
            # Check power expression right multiplier: (10**7)
            elif isinstance(node.right, ast.BinOp) and isinstance(node.right.op, ast.Pow):
                self.violations.append(
                    f"Potential memory exhaustion exponent multiplier at line {node.lineno}"
                )
        self.generic_visit(node)


def verify_ast_action_safety(code: str) -> bool:
    """Validate a code snippet with zero-cost static AST inspection before execution."""
    try:
        tree = ast.parse(code)
        validator = AutoHarnessASTSecurityValidator()
        validator.visit(tree)
        if validator.violations:
            logger.warning("AutoHarness AST Action Security Violations: %s", validator.violations)
            return False
        return True
    except Exception as e:
        logger.error("AST Parse failure during security validation: %s", e)
        return False


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
