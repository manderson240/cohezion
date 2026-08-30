#!/usr/bin/env python3
"""Verify exact streaming latency when simulating Hermes Desktop turn."""

import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

payload = {
    "model": "user.cohezion-router",
    "messages": [
        {"role": "system", "content": "You are Hermes Desktop Assistant on AMD Strix Halo."},
        {"role": "user", "content": "Tell me a 1-sentence fact about physics."}
    ],
    "max_tokens": 30,
    "stream": True
}

print(f"Connecting to {url}...")
req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()
first_token = None
tokens = 0

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        for line in resp:
            l = line.decode('utf-8').strip()
            if l.startswith("data: ") and l != "data: [DONE]":
                d = json.loads(l[6:])
                delta = d["choices"][0]["delta"]
                tok = delta.get("content") or delta.get("reasoning_content") or ""
                if tok:
                    if first_token is None:
                        first_token = time.perf_counter() - t0
                        print(f"⏱ Time to First Token (TTFT): {first_token:.2f}s")
                    print(tok, end="", flush=True)
                    tokens += 1
    total_t = time.perf_counter() - t0
    tps = tokens / (total_t - (first_token or 0)) if total_t > (first_token or 0) else 0
    print(f"\n✓ Completed: {total_t:.2f}s total | {tokens} tokens | {tps:.1f} tok/s")
except Exception as e:
    print(f"\n✗ Failed: {e}")
