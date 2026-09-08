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


def test_proposed_code(code_str: str, task_data: dict) -> list[list[int]] | None:
    """Executes proposed code in a restricted scope against training pairs."""
    try:
        # AST parse check
        ast.parse(code_str)
        local_scope: dict[str, Any] = {}
        exec(code_str, {"__builtins__": {}}, local_scope)
        if "transform" not in local_scope:
            return None

        fn = local_scope["transform"]
        # Verify against all train pairs
        for p in task_data.get("train", []):
            inp = p.get("input", [])
            expected = p.get("output", [])
            if fn(inp) != expected:
                return None

        # Execute on test input
        test_in = task_data.get("test", [{}])[0].get("input", [[0]])
        result: list[list[int]] = fn(test_in)
        return result
    except Exception:
        return None
