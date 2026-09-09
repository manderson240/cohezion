#!/usr/bin/env python3
"""Verify native Lemonade router policy for Hermes Agent Desktop."""

import json
import time
import urllib.request


url = "http://localhost:13305/api/v1/chat/completions"

# Test 1: Fast conversation -> Routes to NPU waslmedia-qwen3-4b
req_fast = {
    "model": "user.cohezion-hermes-router",
    "messages": [{"role": "user", "content": "Hello Hermes! What is the weather like today?"}],
    "max_tokens": 60,
    "route_trace": True
}

# Test 2: Coding question -> Routes to iGPU Qwen3-Coder-30B
req_code = {
    "model": "user.cohezion-hermes-router",
    "messages": [{"role": "user", "content": "Write a python function to compute fibonacci numbers with memoization."}],
    "max_tokens": 80,
    "route_trace": True
}

def test_route(name: str, payload: dict) -> None:
    print(f"\n--- Testing {name} ---")
    req = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dt = time.perf_counter() - t0
            headers = dict(resp.headers)
            route_hdr = headers.get("x-lemonade-route", "unknown")
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✓ Completed in {dt:.2f}s | Route: {route_hdr}")
            print(f"  Model Used: {data.get('model')}")
            content = data["choices"][0]["message"]["content"]
            reasoning = data["choices"][0]["message"].get("reasoning_content", "")
            print(f"  Snippet: {(content or reasoning)[:120]}...")
    except Exception as e:
        print(f"✗ Failed: {e}")

test_route("Hermes Fast NPU Query", req_fast)
test_route("Hermes Coding iGPU Query", req_code)
