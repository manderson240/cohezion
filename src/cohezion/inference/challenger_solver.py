"""
ChallengerSolverVerifier — TreeQuest ABMCTS across NPU / iGPU / CPU Lemonade tiers.

All three tiers run concurrently via treequest.ABMCTSM(max_process_workers=3).
Calls Lemonade OmniRouter :13305 synchronously (requests.post) — no asyncio needed
because TreeQuest requires sync generate functions.

Tier roles
----------
solver:     Gemma-4-E4B-it-GGUF    (iGPU vulkan, ~54 TPS) — proposes initial answers
challenger: deepseek-r1-0528-8b-FLM (NPU FLM,   ~10 TPS) — refutes via chain-of-thought
cpu:        Gemma-4-31B-it-GGUF    (CPU llamacpp, heavy)  — deep verification / synthesis

AB-MCTS (Adaptive Budget MCTS) automatically allocates more search steps to tiers with
higher demonstrated scores — the best-performing tier on this task class gets more calls.
"""

import re
import requests
from dataclasses import dataclass

import treequest as tq  # type: ignore[import-untyped]

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
_TIMEOUT = 120  # seconds — CPU tier can be slow on large models
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)

_TIER_MODELS: dict[str, str] = {
    "solver":     "Gemma-4-E4B-it-GGUF",
    "challenger": "deepseek-r1-0528-8b-FLM",
    "cpu":        "Gemma-4-31B-it-GGUF",
}
_JUDGE_MODEL = "llama3.2-1b-FLM"  # 42 TPS — fast independent judge


@dataclass
class SolverState:
    task: str
    response: str
    tier: str


def _chat(messages: list[dict], model: str, max_tokens: int = 1024) -> str:
    resp = requests.post(
        LEMONADE_URL,
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    # Strip <think> blocks from reasoning models before returning
    if "<think>" in content:
        stripped = _THINK_RE.sub("", content).strip()
        return stripped if stripped else content
    return content


def _judge(task: str, response: str) -> float:
    """Fast llama3.2-1b-FLM judge score [0.0, 1.0]. Falls back to 0.5 on error."""
    if not response or len(response.strip()) < 20:
        return 0.0
    try:
        text = _chat(
            [{"role": "user", "content": f"Rate this answer 0-10 (number only).\nQ: {task[:80]}\nA: {response[:400]}"}],
            model=_JUDGE_MODEL,
            max_tokens=4,
        )
        return min(1.0, max(0.0, float(text.strip()) / 10))
    except Exception:
        return 0.5


def _make_generate(tier: str, task: str):
    model = _TIER_MODELS[tier]

    def generate(parent: SolverState | None) -> tuple[SolverState, float]:
        if parent is None:
            # Root node: each tier directly attempts the task
            prompt = f"Answer concisely and accurately: {task}"
        elif tier == "challenger":
            prompt = (
                f"Critically challenge this answer — find errors, gaps, or edge cases. "
                f"If it is correct, confirm it explicitly. If wrong, give the correct answer.\n\n"
                f"Question: {task}\nProposed answer: {parent.response}"
            )
        else:
            prompt = (
                f"Deeply analyse and improve this answer:\n\n"
                f"Question: {task}\nCurrent answer: {parent.response}"
            )

        response = _chat([{"role": "user", "content": prompt}], model=model)
        score = _judge(task, response)
        return SolverState(task=task, response=response, tier=tier), score

    return generate


def run(task: str, steps: int = 9) -> SolverState:
    """
    Run TreeQuest ABMCTS across all 3 Lemonade tiers concurrently.

    steps=9 gives ~3 expansions per tier on average; raise for harder tasks.
    Wall-clock time ≈ slowest single tier (CPU), not sum of all tiers.

    Returns the highest-scored SolverState.
    """
    algo = tq.ABMCTSM(max_process_workers=3)
    tree = algo.init_tree()
    generate_fns = {tier: _make_generate(tier, task) for tier in _TIER_MODELS}

    for _ in range(steps):
        tree = algo.step(tree, generate_fns)

    best_state, _ = tq.top_k(tree, algo, k=1)[0]
    return best_state
