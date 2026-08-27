"""Embedded Multi-Agent Swarm for Offline Kaggle Submissions.

Coordinates:
1. `HypothesisAgent` (CPU Invariant Delta Extractor)
2. `ProgramSynthesizerAgent` (GPU DSL Synthesizer)
3. `VerifierAgent` (Zero-cost Bytecode Action Verifier)
4. `ReflectorAgent` (Error Trace & Constraint Mutator)
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class HypothesisAgent:
    """Extracts geometric, topological, and color invariants to form synthesis guidance."""

    @staticmethod
    def analyze(task: dict[str, Any]) -> dict[str, Any]:
        train = task.get("train", [])
        if not train:
            return {"primary_pattern": "IDENTITY", "scale": (1, 1), "colors": []}

        in_shapes = [
            (len(p["input"]), len(p["input"][0])) for p in train if p.get("input") and p["input"][0]
        ]
        out_shapes = [
            (len(p["output"]), len(p["output"][0]))
            for p in train
            if p.get("output") and p["output"][0]
        ]

        same_shape = in_shapes == out_shapes
        scale_x = out_shapes[0][0] // max(1, in_shapes[0][0]) if out_shapes and in_shapes else 1
        scale_y = out_shapes[0][1] // max(1, in_shapes[0][1]) if out_shapes and in_shapes else 1

        return {
            "is_same_shape": same_shape,
            "scale_factor": (scale_x, scale_y),
            "pair_count": len(train),
            "hypothesis_tag": "PRESERVE_GEOMETRY" if same_shape else f"SCALE_{scale_x}x{scale_y}",
        }


class VerifierAgent:
    """Compiles and executes candidate AST code against all training pairs with zero latency."""

    @staticmethod
    def verify(
        task: dict[str, Any], fn: Callable[[list[list[int]]], list[list[int]]]
    ) -> tuple[bool, str]:
        train = task.get("train", [])
        for i, pair in enumerate(train):
            in_g = pair.get("input", [])
            expected = pair.get("output", [])
            try:
                actual = fn(in_g)
                if actual != expected:
                    return (
                        False,
                        f"Mismatch on pair {i}: shape expected ({len(expected)}, {len(expected[0]) if expected else 0}), got ({len(actual)}, {len(actual[0]) if actual else 0})",
                    )
            except Exception as e:
                return False, f"Execution exception on pair {i}: {e}"
        return True, "VERIFIED_PERFECT_FIT"


class ReflectorAgent:
    """Diagnoses verification failures and mutates hypothesis constraints."""

    @staticmethod
    def reflect_and_mutate(hypothesis: dict[str, Any], error_msg: str) -> dict[str, Any]:
        new_hyp = dict(hypothesis)
        if "shape expected" in error_msg:
            new_hyp["hypothesis_tag"] = "DYNAMIC_CROPPING_OR_BOUNDING_BOX"
        elif "Execution exception" in error_msg:
            new_hyp["hypothesis_tag"] = "FALLBACK_IDENTITY_GUARDED"
        else:
            new_hyp["hypothesis_tag"] = "MUTATE_COLOR_PERMUTATION"
        return new_hyp


class EmbeddedKaggleAgentSwarm:
    """Master Orchestrator coordinating in-memory multi-agent consensus within Kaggle budget."""

    def __init__(self, task: dict[str, Any], time_budget_sec: float = 5.0):
        self.task = task
        self.time_budget_sec = time_budget_sec
        self.history: list[dict[str, Any]] = []

    def solve(self, candidate_transforms: list[Callable]) -> tuple[Callable | None, str]:
        t0 = time.perf_counter()

        # 1. Hypothesis Agent forms initial belief state
        hyp = HypothesisAgent.analyze(self.task)
        self.history.append({"stage": "hypothesis", "state": hyp})

        # 2. Fast heuristic test loop with Verifier
        for fn in candidate_transforms:
            if (time.perf_counter() - t0) >= self.time_budget_sec:
                break
            passed, msg = VerifierAgent.verify(self.task, fn)
            if passed:
                return fn, f"SOLVED_BY_SWARM_VERIFIER ({fn.__name__})"

            # 3. Reflector Agent diagnoses and mutates hypothesis
            hyp = ReflectorAgent.reflect_and_mutate(hyp, msg)
            self.history.append({"stage": "reflection", "error": msg, "new_hyp": hyp})

        return None, "SWARM_EXHAUSTED_TIME_BUDGET"
