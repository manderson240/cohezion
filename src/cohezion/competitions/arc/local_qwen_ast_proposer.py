"""Local LLM-in-the-Loop Program Proposer via Qwen3-Coder-30B on AMD iGPU (Port 13305).

Synthesizes task-specific Python functions for ARC challenges that fail standard DSL search.
Executes generated code in an isolated AST sandbox with 0ms AutoHarness verification.
"""

import ast
import logging
from typing import Any

import httpx


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [LLM_PROPOSER] %(message)s"
)
logger = logging.getLogger("llm_proposer")

LEMONADE_BASE = "http://localhost:13305"

PROMPT_TEMPLATE = """You are an ARC-AGI Python Code Synthesizer.
Given the input/output training examples, write a single standalone Python function `transform(grid: list[list[int]]) -> list[list[int]]` that exactly transforms the input grid to the output grid.

Training Examples:
{train_pairs}

Return ONLY the executable Python code block:
```python
def transform(grid):
    # Your logic
    return new_grid
```
"""


async def propose_python_solution(client: httpx.AsyncClient, task_data: dict) -> str | None:
    train_pairs_text = ""
    for idx, p in enumerate(task_data.get("train", [])):
        train_pairs_text += (
            f"\nExample {idx + 1}:\nInput: {p.get('input')}\nOutput: {p.get('output')}\n"
        )

    prompt = PROMPT_TEMPLATE.format(train_pairs=train_pairs_text)
    payload = {
        "model": "Qwen3-Coder-30B",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 16384,
    }

    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload, timeout=900.0)
        if r.status_code == 200:
            content: str = r.json()["choices"][0]["message"]["content"]
            if "```python" in content:
                code = content.split("```python")[1].split("```")[0].strip()
                return code
            elif "def transform" in content:
                return content.strip()
    except Exception as e:
        logger.warning("LLM proposal call failed: %s", e)
    return None


# Appended to the proposal and run INSIDE the sandbox child: verifies every train pair and, only
# if all match, returns the test-input grid. One process round-trip per proposal instead of one
# per pair. The name is underscore-prefixed so a legitimate proposal never collides with it.
_RUNNER = """

def _cz_run(task):
    for p in task.get("train", []):
        if transform(p.get("input", [])) != p.get("output", []):
            return None
    return transform(task.get("test", [{}])[0].get("input", [[0]]))
"""


def _is_grid(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(r, list) and all(type(v) is int for v in r) for r in value
    )


def test_proposed_code(code_str: str, task_data: dict) -> list[list[int]] | None:
    """Runs proposed code OUT OF PROCESS against the training pairs; returns the test grid or None.

    H5: the previous in-process ``exec`` under ``safe_exec_globals`` was an availability gate, not a
    boundary (the ``__subclasses__``/``collections._sys`` reach was available with not even the rlimit
    floor). ``run_untrusted`` applies kernel rlimits (+bwrap when available) and fails closed. The
    result is post-exec UNTRUSTED data (the child can forge it), so only a grid of ints is accepted —
    which is all a proposal can legitimately produce, and all its consumers compare or submit.
    """
    try:
        ast.parse(code_str)
    except SyntaxError:
        return None
    from cohezion.compound.sandboxed_exec import run_untrusted

    r = run_untrusted(
        code_str + _RUNNER, call="_cz_run", args=[task_data], bindings={"np": "numpy"}
    )
    if not r.ok or not _is_grid(r.value):
        return None
    return r.value
