#!/usr/bin/env python3
"""Inference Triad — local inference across NPU, iGPU, and CPU via Lemonade (:13305).

Probes the full compute stack simultaneously:
  NPU   → AMD XDNA2 FLM models  (gemma3, llama3.2, qwen3.5)
  iGPU  → GGUF via Vulkan       (small Qwen3 models)
  CPU   → GGUF fallback         (anything, but slow)

Usage:
    uv run scripts/inference_triad.py [prompt]

Exit codes:
    0  All tiers responsive
    1  One or more tiers failed
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx


_LEMONADE_BASE = os.environ.get("LEMONADE_BASE", "http://localhost:13305")
_PROMPT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "Explain the relationship between quantized neural networks and local inference speed in one paragraph."
)

# Representative models per backend — discovered from /v1/models
# We run ONE per tier to avoid serialising on single-device backends.
_REPRESENTATIVE_MODELS = {
    "npu": "gemma3-4b-FLM",
    "igpu": "Qwen3-0.6B-GGUF",
    "cpu": "Qwen3-0.6B-GGUF",
}

MAX_TOKENS = 128
TIMEOUT = 90.0


async def probe_registry(client: httpx.AsyncClient) -> list[dict]:
    resp = await client.get(f"{_LEMONADE_BASE}/v1/models", timeout=10.0)
    resp.raise_for_status()
    return resp.json().get("data", [])


async def benchmark_one(
    client: httpx.AsyncClient,
    model: str,
    backend: str,
    prompt: str,
) -> dict:
    """Run a single benchmark via Lemonade chat/completions."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }
    # If backend hint is supported, add it; Lemonade may ignore unsupported keys
    # but some builds accept preferred_backend in extra_body or headers.
    headers = {}
    if backend != "auto":
        headers["X-Preferred-Backend"] = backend

    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{_LEMONADE_BASE}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return {
                "model": model,
                "backend": backend,
                "ok": False,
                "error": f"HTTP {resp.status_code}",
            }
        data = resp.json()
        t1 = time.perf_counter()

        content = data["choices"][0]["message"]["content"]
        # Approximate token count (4 chars/token is a coarse heuristic)
        tokens_out = max(1, len(content) // 4)
        elapsed = t1 - t0
        ttft_s = elapsed  # non-streaming: TTFT ≈ full latency

        return {
            "model": model,
            "backend": backend,
            "ok": True,
            "content_preview": content[:120].replace("\n", " ") + "…",
            "tokens_out": tokens_out,
            "latency_s": round(elapsed, 3),
            "ttft_ms": round(ttft_s * 1000, 1),
            "tps": round(tokens_out / elapsed, 2),
        }
    except Exception as exc:
        return {
            "model": model,
            "backend": backend,
            "ok": False,
            "error": str(exc),
        }


async def run_tier(
    client: httpx.AsyncClient,
    tier: str,
    candidate: str,
    registry_models: set[str],
    prompt: str,
) -> dict:
    """Run one representative model for a tier."""
    if candidate not in registry_models:
        return {"tier": tier, "ok": False, "error": f"{candidate} not in registry"}
    return await benchmark_one(client, candidate, tier, prompt)


def print_results(results: dict[str, dict]) -> None:
    print("\n" + "=" * 70)
    print(f" Inference Triad Report — {datetime.now().isoformat()}")
    print("=" * 70)
    grand_total = 0.0
    any_failed = False

    for tier in ("npu", "igpu", "cpu"):
        print(f"\n[{tier.upper()}]")
        r = results.get(tier, {})
        if not r:
            print("  No results")
            continue

        if not r.get("ok"):
            print(f"  ✗ {r.get('model', tier)}: {r.get('error', 'unknown')}")
            any_failed = True
            continue

        print(
            f"  ✓ {r['model']:30s}  "
            f"{r['tps']:7.2f} TPS | "
            f"{r['ttft_ms']:8.1f} ms TTFT | "
            f"{r['tokens_out']:3d} tok | "
            f"latency {r['latency_s']:.2f}s"
        )
        grand_total += r["tps"]

    print("\n" + "-" * 70)
    print(f"Combined throughput across responsive tiers: {grand_total:.2f} TPS")

    if any_failed:
        print("\n⚠️  One or more benchmarks failed. (see errors above)")
    else:
        print("\n✅ All tiers responsive.")
    print("=" * 70)


async def main() -> int:
    print("Inference Triad — probing NPU / iGPU / CPU via Lemonade")
    print(f"Prompt: {_PROMPT[:80]}…")
    print(f"Endpoint: {_LEMONADE_BASE}\n")

    async with httpx.AsyncClient() as client:
        # 1. Discover registry
        try:
            registry = await probe_registry(client)
        except Exception as exc:
            print(f"FATAL: Cannot reach lemonade at {_LEMONADE_BASE}: {exc}")
            return 1

        registry_ids = {m["id"] for m in registry}
        print(f"Registry: {len(registry)} models loaded")

        # 2. Run all tiers concurrently (one model each to avoid queue contention)
        results = await asyncio.gather(
            run_tier(client, "npu", _REPRESENTATIVE_MODELS["npu"], registry_ids, _PROMPT),
            run_tier(client, "igpu", _REPRESENTATIVE_MODELS["igpu"], registry_ids, _PROMPT),
            run_tier(client, "cpu", _REPRESENTATIVE_MODELS["cpu"], registry_ids, _PROMPT),
        )

        all_ok = {}
        for tier_name, tier_res in zip(("npu", "igpu", "cpu"), results):
            all_ok[tier_name] = tier_res

        # 3. Print
        print_results(all_ok)

        # 4. Write machine-readable report next to the script
        report = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": _LEMONADE_BASE,
            "prompt": _PROMPT,
            "results": all_ok,
        }
        out_path = Path(__file__).with_name("inference_triad_report.json")
        out_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nReport written: {out_path}")

    return 0 if all(all_ok[t].get("ok") for t in ("npu", "igpu", "cpu")) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
