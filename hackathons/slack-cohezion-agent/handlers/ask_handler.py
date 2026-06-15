"""Q&A handler — routes questions through Cohezion compound loop.

Tier routing:
  NPU  (llama3.2-1b-FLM, 42 TPS)  → short/categorical answers
  iGPU (deepseek-r1-8b, ~200ms)   → generation/explanation
  CPU  (Gemma-4-31B, ~800ms)      → reasoning/analysis
  Cloud (claude-haiku-4-5)        → fallback when local silicon offline
"""

from __future__ import annotations

import os
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cohezion_bridge import CohezionBridge, LemonadeClient


_bridge = CohezionBridge()

_SYSTEM_PROMPT = """\
You are Cohezion Intelligence, an expert AI assistant for software engineering teams.
Answer concisely and accurately. For code questions, include working examples.
When local AMD silicon is available, you run at $0/query with zero cloud cost.
"""

_TIER_TO_MODEL = {
    "npu": "llama3.2-1b-FLM",
    "igpu": "deepseek-r1-0528-8b-FLM",
    "cpu": "Gemma-4-31B-it-GGUF",
}


def handle_ask(question: str, tier: str = "auto", user_id: str = "") -> dict:
    """Route a question through Cohezion compound loop and return an answer.

    Args:
        question: The question to answer.
        tier: Inference tier — "auto" lets the classifier decide.
        user_id: Slack user ID (for context, not used in inference).

    Returns:
        {
            "answer": str,
            "tier_used": str,
            "latency_ms": int,
            "cost_usd": float,
            "model": str,
            "local_silicon": bool,
        }
    """
    start = time.time()

    # ── Tier selection ────────────────────────────────────────────────
    chosen_tier = tier
    if tier == "auto":
        classification = _bridge.classify_task(question)
        if classification:
            chosen_tier = classification.get("node", "igpu")
        else:
            # Default: iGPU for generation
            chosen_tier = "igpu"

    # ── Local AMD silicon attempt ─────────────────────────────────────
    if _bridge.lemonade_available(chosen_tier):
        lemonade = LemonadeClient(chosen_tier)
        full_prompt = f"{_SYSTEM_PROMPT}\n\nUser: {question}\n\nAssistant:"
        answer = lemonade.complete(full_prompt, max_tokens=800, temperature=0.1)
        if answer:
            return {
                "answer": answer,
                "tier_used": chosen_tier,
                "latency_ms": int((time.time() - start) * 1000),
                "cost_usd": 0.0,
                "model": _TIER_TO_MODEL.get(chosen_tier, "unknown"),
                "local_silicon": True,
            }

    # ── Cloud fallback (Anthropic) ────────────────────────────────────
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=800,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        answer = response.content[0].text if response.content else "No response generated."
        # Approximate cost: claude-haiku-4-5 ~$0.025/1K tokens input, $0.125/1K output
        approx_cost = round(
            (response.usage.input_tokens / 1000 * 0.025)
            + (response.usage.output_tokens / 1000 * 0.125),
            4,
        )
        return {
            "answer": answer,
            "tier_used": "cloud",
            "latency_ms": int((time.time() - start) * 1000),
            "cost_usd": approx_cost,
            "model": "claude-haiku-4-5",
            "local_silicon": False,
        }
    except Exception:
        pass

    return {
        "answer": "Cohezion is offline — no local silicon or API key configured. Please set ANTHROPIC_API_KEY.",
        "tier_used": "none",
        "latency_ms": int((time.time() - start) * 1000),
        "cost_usd": 0.0,
        "model": "none",
        "local_silicon": False,
    }
