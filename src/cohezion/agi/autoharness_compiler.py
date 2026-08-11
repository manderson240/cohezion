r"""AutoHarness Policy Bytecode Compiler (arXiv:2603.03329v1)
============================================================
Compiles Python AST invariant rules into zero-overhead bytecode functions
executing in < 50 microseconds to enforce deterministic action policies.
"""

from __future__ import annotations

import ast
import time
from typing import Any, Callable

from cohezion.agi.autoharness_policy import ActionPolicyResult


class AutoHarnessCompiler:
    """Compiles string AST invariant expressions into compiled bytecode evaluators."""

    @classmethod
    def compile_rule(cls, rule_name: str, expression_str: str) -> Callable[[dict[str, Any]], bool]:
        """Compile a Python string expression into a safe, fast evaluation function."""
        tree = ast.parse(expression_str, mode="eval")
        compiled_code = compile(tree, filename=f"<autoharness_{rule_name}>", mode="eval")

        def compiled_evaluator(state: dict[str, Any]) -> bool:
            # Provide safe builtins only
            safe_globals = {"__builtins__": {"abs": abs, "min": min, "max": max, "len": len, "sum": sum}}
            try:
                return bool(eval(compiled_code, safe_globals, state))
            except Exception:
                return False

        return compiled_evaluator

    @classmethod
    def benchmark_rule_latency(cls, evaluator_fn: Callable[[dict[str, Any]], bool], sample_state: dict[str, Any], runs: int = 1000) -> float:
        """Measure average latency per policy evaluation run in microseconds."""
        t0 = time.perf_counter()
        for _ in range(runs):
            evaluator_fn(sample_state)
        dt = (time.perf_counter() - t0) / runs
        return dt * 1_000_000.0  # Return microseconds (us)
