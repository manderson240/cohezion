#!/usr/bin/env python3
"""Diagnose why Hermes Desktop experiences latency or empty SSE stream stalls."""

import json
import time
import urllib.request


url_chat = "http://127.0.0.1:13305/api/v1/chat/completions"

# Test 1: Direct stream test to see where the latency is spending time
print("=== 1. Testing Streaming Response Latency on Port 13305 ===")
payload = {
    "model": "user.cohezion-hermes-router",
    "messages": [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Explain what you are doing in 2 short bullet points."}
    ],
    "max_tokens": 80,
    "stream": True
}

req = urllib.request.Request(url_chat, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()
first_token_t = None
token_count = 0

with urllib.request.urlopen(req, timeout=30) as resp:
    for line in resp:
        line = line.decode('utf-8').strip()
        if line.startswith("data: "):
            if line == "data: [DONE]":
                break
            try:
                data = json.loads(line[6:])
                delta = data["choices"][0]["delta"].get("content", "")
                if delta:
                    if first_token_t is None:
                        first_token_t = time.perf_counter() - t0
                        print(f"⏱ Time to First Token (TTFT): {first_token_t:.2f}s")
                    token_count += 1
            except Exception:
                pass

total_t = time.perf_counter() - t0
tps = token_count / (total_t - (first_token_t or 0)) if total_t > (first_token_t or 0) else 0
print(f"⏱ Total Time: {total_t:.2f}s | Tokens: {token_count} | Decode Speed: {tps:.1f} tok/s")
