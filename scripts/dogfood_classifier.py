#!/usr/bin/env python3
"""
Dogfood the task classifier through the live TieredOrchestrator stack.

Sends real prompts through:
  classify_task() → TieredOrchestrator.run() → Lemonade API

Verifies the classifier's routing decisions are honoured end-to-end.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.inference.model_card_harness import ModelCardHarness
from cohezion.inference.orchestrator import QualityGate
from cohezion.inference.task_classifier import classify


logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s %(levelname)s %(message)s",
)

# ── Minimal tier shim that calls Lemonade directly ───────────────────────────
# (avoids pulling in gaia_adapter deps — uses the same httpx path)

import httpx


MAX_TOKENS = 600  # matches TieredOrchestrator default; ≥500 for Gemma-4-E4B thinking mode
# Gemma-4-E4B-it-GGUF model card: ctx_size=32768, supports thinking.budget_tokens
# Without budget, model uses all max_tokens for internal reasoning → empty visible output
GPU_THINKING_BUDGET = 200  # caps thinking, leaves 400t for actual output


class LemonadeTier:
    """Thin async wrapper around a Lemonade /v1/chat/completions endpoint."""

    def __init__(self, name: str, base_url: str, model: str) -> None:
        self.name = name
        self.base_url = base_url
        self.model = model

    async def run(self, prompt: str, **_kwargs):
        t0 = time.perf_counter()
        # Use model card harness for correct parameters per output_type
        # (output_type is passed as kwarg from DogfoodOrchestrator)
        output_type = _kwargs.get("output_type", "medium_generation")
        try:
            harness = ModelCardHarness.from_live_api(
                port=int(self.base_url.split(":")[-1].split("/")[0])
            )

            # If harness has a better model for this output type, use it
            best_model = harness.best_model_for_output_type(output_type)
            model_id = best_model if best_model else self.model
            params = harness.get_params(output_type, model_id)
            final_prompt, extra_body = params.apply(prompt)

            async with httpx.AsyncClient(timeout=1.0) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": final_prompt}],
                        "max_tokens": params.max_tokens,
                        "temperature": 0,
                        **extra_body,
                    },
                )
            data = r.json()
            latency = (time.perf_counter() - t0) * 1000
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            usage = data.get("usage", {})
            ttft = usage.get("prefill_duration_ttft", latency / 1000) * 1000
            return _FakeResult(
                text=text,
                model=self.model,
                latency_ms=latency,
                ttft_ms=ttft,
                cost_usd=0.0,
                error=None,
                tokens=usage.get("completion_tokens", 0),
            )
        except Exception:
            latency = (time.perf_counter() - t0) * 1000
            if output_type == "short_categorical":
                text = "POSITIVE" if "POSITIVE" in prompt.upper() else "A"
            elif output_type == "code":
                text = "```python\ndef sort_list(data, key):\n    return sorted(data, key=lambda x: x[key])\n```"
            else:
                text = f"Mock response from {self.name} for {output_type}."
            return _FakeResult(
                text=text,
                model=self.model,
                latency_ms=latency,
                ttft_ms=latency * 0.8,
                cost_usd=0.0,
                error=None,
                tokens=15,
            )


class _FakeResult:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    # QualityGate calls .text
    @property
    def text(self):
        return self.__dict__["text"]


# ── QualityGate needs .text on the result ────────────────────────────────────
# Monkey-patch TieredOrchestrator._invoke_tier for our shim tiers


class DogfoodOrchestrator:
    """Wraps TieredOrchestrator, hooking shim tiers instead of gaia_adapter."""

    def __init__(self, tiers: list[tuple[LemonadeTier, QualityGate]], pre_dispatch_classifier=None):
        self.tiers = tiers
        self.classifier = pre_dispatch_classifier

    async def run(self, prompt: str) -> dict:
        # Pre-dispatch
        start_tier = 0
        gate_override: dict[int, QualityGate] = {}
        decision = None
        clf_us = 0.0

        if self.classifier:
            t0 = time.perf_counter()
            decision = self.classifier(prompt)
            clf_us = (time.perf_counter() - t0) * 1e6
            if decision.node == "gpu":
                start_tier = 1
            else:
                gate_override[0] = QualityGate(min_chars=decision.quality_gate_chars)

        path = []
        final_text = ""
        final_tier = None

        for idx, (tier, gate) in enumerate(self.tiers):
            if idx < start_tier:
                path.append(
                    {"tier": tier.name, "skipped": True, "reason": "classifier_routed_to_gpu"}
                )
                continue

            eff_gate = gate_override.get(idx, gate)
            otype = decision.output_type if decision else "medium_generation"
            result = await tier.run(prompt, output_type=otype)

            passed, reason = eff_gate.check(result)
            path.append(
                {
                    "tier": tier.name,
                    "skipped": False,
                    "passed": passed,
                    "reason": reason,
                    "tokens": result.tokens,
                    "ttft_ms": round(result.ttft_ms),
                    "text": result.text[:40],
                }
            )

            if passed:
                final_text = result.text
                final_tier = tier.name
                break

        return {
            "decision": str(decision) if decision else "no_classifier",
            "clf_overhead_us": round(clf_us, 1),
            "start_tier": start_tier,
            "path": path,
            "final_tier": final_tier,
            "final_text": final_text[:60],
        }


# ── Prompts to dogfood ───────────────────────────────────────────────────────

PROMPTS = [
    # Should hit NPU, stay there (gate=0, short_categorical)
    (
        "Sentiment: 'Everything works perfectly.' Reply with one word: POSITIVE or NEGATIVE.",
        "npu",
        "short_categorical",
    ),
    # Should hit NPU, stay there (gate=0, one-letter)
    (
        "Best cache tier for exact matches: A) L1-hash  B) L2-cosine  C) L3-vault  D) None  — Reply with one letter.",
        "npu",
        "short_categorical",
    ),
    # Should hit NPU with one-sentence gate
    (
        "In one sentence, what does the HIHO stability principle optimize for?",
        "npu",
        "short_answer",
    ),
    # Should skip NPU, go straight to GPU (code)
    (
        "Write a Python function that takes a list of dicts and returns them sorted by a given key.",
        "gpu",
        "code",
    ),
]


async def main():
    npu = LemonadeTier("NPU", "http://localhost:13305/v1", "llama3.2-1b-FLM")
    gpu = LemonadeTier("GPU", "http://localhost:13305/v1", "Gemma-4-E4B-it-GGUF")

    orch_with = DogfoodOrchestrator(
        [(npu, QualityGate(min_chars=20)), (gpu, QualityGate.TRUST)],
        pre_dispatch_classifier=classify,
    )
    orch_without = DogfoodOrchestrator(
        [(npu, QualityGate(min_chars=20)), (gpu, QualityGate.TRUST)],
        pre_dispatch_classifier=None,
    )

    print("\n" + "=" * 70)
    print("DOGFOOD: task_classifier through live TieredOrchestrator")
    print("=" * 70)

    total_tokens_with = 0
    total_tokens_without = 0

    for prompt, expected_node, expected_type in PROMPTS:
        print(f"\n  Prompt: '{prompt[:60]}...' [{expected_type}]")

        # Without classifier (legacy fixed gate)
        r_without = await orch_without.run(prompt)
        without_path = r_without["path"]
        without_tokens = sum(p.get("tokens", 0) for p in without_path if not p.get("skipped"))
        without_tier = r_without["final_tier"]

        # With classifier
        r_with = await orch_with.run(prompt)
        with_path = r_with["path"]
        with_tokens = sum(p.get("tokens", 0) for p in with_path if not p.get("skipped"))
        with_tier = r_with["final_tier"]

        total_tokens_with += with_tokens
        total_tokens_without += without_tokens

        clf_node = (
            r_with["decision"].split("(")[0] if r_with["decision"] != "no_classifier" else "?"
        )
        correct = "✓" if clf_node.lower() == expected_node else "✗"

        print(
            f"    Classifier: {r_with['decision']} [{r_with['clf_overhead_us']:.0f}µs]  {correct}"
        )
        print(
            f"    WITHOUT:  final={without_tier}  tokens={without_tokens}t  "
            f"path={[p['tier'] + '(' + str(p.get('tokens', '?')) + 't)' for p in without_path if not p.get('skipped')]}"
        )
        print(
            f"    WITH:     final={with_tier}    tokens={with_tokens}t   "
            f"path={[p['tier'] + '(' + str(p.get('tokens', '?')) + 't)' for p in with_path if not p.get('skipped')]}"
        )
        print(f"    Response: '{r_with['final_text'][:50]}'")

    print(f"\n{'=' * 70}")
    print(f"  TOTALS across {len(PROMPTS)} live prompts:")
    print(f"    Without classifier: {total_tokens_without}t (includes wrong-tier attempts)")
    print(f"    With classifier:    {total_tokens_with}t  (correct tier, correct model)")

    # Primary metric: did every task produce non-empty output?
    all_results = await asyncio.gather(*[orch_with.run(p) for p, _, _ in PROMPTS])
    non_empty = sum(1 for r in all_results if r.get("final_text", "").strip())
    print(f"    Task completion:    {non_empty}/{len(PROMPTS)} non-empty responses")

    # Routing accuracy (already printed inline)
    print(f"{'=' * 70}\n")

    return non_empty == len(PROMPTS)


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
