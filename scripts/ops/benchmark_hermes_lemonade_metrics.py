#!/usr/bin/env python3
"""Benchmark Latency, Throughput (tok/s), Time-To-First-Token (TTFT), and Quality across Lemonade Router tiers."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any


URL = "http://localhost:13305/api/v1/chat/completions"
MODEL = "user.cohezion-hermes-router"

BENCHMARK_SUITE = [
    {
        "tier": "Tier 1 (NPU Fast Chat)",
        "name": "Fast Q&A / Trivial Ack",
        "prompt": "State the speed of light in vacuum in m/s in one concise sentence.",
        "expected_route": "hermes-fast-chat",
        "max_tokens": 60
    },
    {
        "tier": "Tier 1 (iGPU Coding/Tools)",
        "name": "Algorithmic Code Generation",
        "prompt": "Write a python function `levenshtein_distance(s1: str, s2: str) -> int` with dynamic programming.",
        "expected_route": "hermes-coding-skills",
        "max_tokens": 200
    },
    {
        "tier": "Tier 1 (NPU/iGPU Reasoning)",
        "name": "Diagnostic Causal Reasoning",
        "prompt": "Explain step by step why a relativistic Bennett pinch magnetic field B_theta prevents Coulomb explosion in a 10^11 electron cluster.",
        "expected_route": "hermes-deep-reasoning",
        "max_tokens": 250
    },
    {
        "tier": "Tier 1 (Agentic Tool Dispatch)",
        "name": "Structured Tool Calling",
        "prompt": "Execute the tool to query the system kernel temperature sensor.",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "query_sensor",
                    "description": "Query hardware thermal sensors",
                    "parameters": {
                        "type": "object",
                        "properties": {"sensor_id": {"type": "string", "enum": ["cpu", "npu", "igpu"]}},
                        "required": ["sensor_id"]
                    }
                }
            }
        ],
        "expected_route": "hermes-agent-tools",
        "max_tokens": 120
    }
]


def run_benchmark_turn(test: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are Hermes Agent powered by AMD Strix Halo local silicon."},
            {"role": "user", "content": test["prompt"]}
        ],
        "max_tokens": test.get("max_tokens", 100),
        "route_trace": True
    }
    if "tools" in test:
        payload["tools"] = test["tools"]

    req = urllib.request.Request(
        URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_dt = time.perf_counter() - t0
            headers = dict(resp.headers)
            route = headers.get("x-lemonade-route", "unknown")
            raw_body = resp.read().decode("utf-8")
            data = json.loads(raw_body)

            # Extract timings
            timings = data.get("timings", {})
            prompt_ms = timings.get("prompt_ms", 0.0)
            prompt_n = timings.get("prompt_n", 0)
            prompt_tps = timings.get("prompt_per_second", (prompt_n / (prompt_ms / 1000.0)) if prompt_ms > 0 else 0.0)

            pred_ms = timings.get("predicted_ms", 0.0)
            pred_n = timings.get("predicted_n", len(data["choices"][0]["message"].get("content", "").split()))
            pred_tps = timings.get("predicted_per_second", (pred_n / (pred_ms / 1000.0)) if pred_ms > 0 else (pred_n / total_dt))

            # Extract content / tools
            msg = data["choices"][0]["message"]
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            reasoning = msg.get("reasoning_content", "")

            # Quality Evaluation heuristic
            quality_score = 1.0
            if "tools" in test and not tool_calls:
                quality_score -= 0.5
            if not content and not tool_calls and not reasoning:
                quality_score = 0.0

            return {
                "name": test["name"],
                "tier": test["tier"],
                "route": route,
                "model": data.get("model", "unknown"),
                "total_time_s": total_dt,
                "ttft_ms": prompt_ms,
                "prefill_tps": prompt_tps,
                "decode_tps": pred_tps,
                "tokens_generated": pred_n,
                "quality_score": quality_score,
                "tool_calls_count": len(tool_calls),
                "snippet": (content or reasoning or str(tool_calls))[:90].replace("\n", " ")
            }
    except Exception as e:
        return {
            "name": test["name"],
            "tier": test["tier"],
            "route": "ERROR",
            "model": "error",
            "total_time_s": time.perf_counter() - t0,
            "ttft_ms": 0.0,
            "prefill_tps": 0.0,
            "decode_tps": 0.0,
            "tokens_generated": 0,
            "quality_score": 0.0,
            "tool_calls_count": 0,
            "snippet": f"Error: {e}"
        }


def main() -> None:
    print("=" * 95)
    print("  📊 HERMES AGENT ↔ LEMONADE ROUTER: LATENCY, THROUGHPUT & QUALITY BENCHMARK")
    print("=" * 95)

    results = []
    for test in BENCHMARK_SUITE:
        print(f"\nEvaluating: {test['name']} ({test['tier']})...")
        res = run_benchmark_turn(test)
        results.append(res)
        print(f"  ✓ Route: {res['route']} -> Model: {res['model']}")
        print(f"  ⏱ Total Latency: {res['total_time_s']:.2f}s | TTFT (Prefill): {res['ttft_ms']:.1f}ms")
        print(f"  ⚡ Prefill: {res['prefill_tps']:.1f} tok/s | Decode: {res['decode_tps']:.1f} tok/s ({res['tokens_generated']} tokens)")
        print(f"  🎯 Quality Score: {res['quality_score']*100:.0f}% | Snippet: {res['snippet']}...")

    # Write Markdown summary table
    out_md = "/home/mike-anderson/dev/cohezion/docs/research/hermes_lemonade_benchmark_report.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Hermes Desktop ↔ Lemonade Custom Router Benchmark Report\n\n")
        f.write("**Hardware**: AMD Framework Desktop 16 (AMD Ryzen AI MAX+ 395, 128GB Unified RAM, Radeon 8060S iGPU)\n")
        f.write("**Endpoint**: `http://localhost:13305/api/v1`\n")
        f.write("**Router Policy**: `user.cohezion-hermes-router`\n\n")
        f.write("| Workload / Tier | Matched Route | Dispatched Model | Total Time | TTFT (ms) | Prefill (t/s) | Decode (t/s) | Quality |\n")
        f.write("|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|\n")
        for r in results:
            f.write(f"| **{r['name']}**<br>*{r['tier']}* | `{r['route']}` | `{r['model'].replace('user.', '')}` | **{r['total_time_s']:.2f}s** | {r['ttft_ms']:.1f}ms | {r['prefill_tps']:.1f} | **{r['decode_tps']:.1f}** | **{r['quality_score']*100:.0f}%** |\n")

    print("\n" + "=" * 95)
    print(f"🎉 Benchmark complete! Report saved to: {out_md}")
    print("=" * 95)


if __name__ == "__main__":
    main()
