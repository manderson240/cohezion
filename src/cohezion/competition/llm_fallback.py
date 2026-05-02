"""LLM fallback solver for ARC tasks that resist program synthesis."""

from __future__ import annotations

import json
import re
from typing import Any

from arc_solver import Grid, deepcopy_grid


try:
    from cohezion.integrations.agentverse import LLMExecutor
except ImportError:
    LLMExecutor = None


SYSTEM = """You are an expert ARC task solver. Given training input/output grid pairs, write a Python function `solve(grid)` that transforms the input to match the output.

Rules:
- grid is List[List[int]] where each cell is 0-9
- Output grid dimensions may differ from input
- Return List[List[int]]
- Use only standard library
- The transformation should work for ALL training examples

Respond ONLY with the Python function code (no markdown)."""


def _encode_grid(g: Grid) -> str:
    return json.dumps(g)


def _extract_function(text: str) -> str | None:
    # Try to extract a function definition
    match = re.search(r"def\s+solve\s*\(.*?\):.*?(?=\n(?:def|class)\s|\Z)", text, re.DOTALL)
    if match:
        return match.group(0)
    # Try to find any code block
    match = re.search(r"```python(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def llm_solve(task: dict[str, Any]) -> Grid | None:
    if LLMExecutor is None:
        return None
    train = task.get("train", [])
    if not train:
        return None

    prompt = "Training examples:\n"
    for i, ex in enumerate(train):
        prompt += f"Example {i + 1}:\n"
        prompt += f"  Input: {_encode_grid(ex['input'])}\n"
        prompt += f"  Output: {_encode_grid(ex['output'])}\n"

    prompt += "\nWrite a Python function `solve(grid)` that passes all training examples."

    try:
        executor = LLMExecutor(model="qwen3.5:cloud")
        result = executor.execute_task(prompt, skill="python_PRIME")
        code = _extract_function(result.output if hasattr(result, "output") else str(result))
        if not code:
            return None

        # Safely execute the generated code
        namespace: dict[str, Any] = {}
        exec(compile(code, "<generated>", "exec"), namespace)
        solve_fn = namespace.get("solve")
        if not solve_fn:
            return None

        test_input = task["test"][0]["input"]
        pred = solve_fn(deepcopy_grid(test_input))
        if isinstance(pred, list) and all(isinstance(r, list) for r in pred):
            return pred
    except Exception:
        return None
    return None
