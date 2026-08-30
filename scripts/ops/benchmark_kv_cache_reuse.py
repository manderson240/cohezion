#!/usr/bin/env python3
"""Benchmark KV-Cache & Prompt Cache Reuse on Lemonade port 13305 & Hermes Agent."""

import json
import time
import urllib.request


url = "http://localhost:13305/api/v1/chat/completions"

# 1000-token repeated system prompt / context
SHARED_SYSTEM_PROMPT = "You are Hermes Agent, a sovereign assistant running on AMD Strix Halo. " * 35

def test_turn(turn_num: int, user_msg: str):
    payload = {
        "model": "user.cohezion-hermes-router",
        "messages": [
            {"role": "system", "content": SHARED_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "max_tokens": 40,
        "route_trace": True
    }
    req = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        dt = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        timings = data.get("timings", {})
        prompt_ms = timings.get("prompt_ms", 0.0)
        prompt_n = timings.get("prompt_n", 0)
        prompt_tps = timings.get("prompt_per_second", 0.0)
        print(f"Turn {turn_num} ({user_msg[:25]}...): Total = {dt*1000:.1f}ms | TTFT (Prompt Prefill) = {prompt_ms:.1f}ms | Prefill Speed = {prompt_tps:.1f} tok/s")

print("--- Testing KV-Cache & Prompt Cache Hit Speedup ---")
print("1. Cold Prefill Turn (Loading 1000-token context into KV Cache)...")
test_turn(1, "What is your primary architecture?")

print("\n2. Warm Turn 2 (Re-using cached KV-Cache prefix)...")
test_turn(2, "Confirm your active local port.")

print("\n3. Warm Turn 3 (Re-using cached KV-Cache prefix)...")
test_turn(3, "State today's date.")
