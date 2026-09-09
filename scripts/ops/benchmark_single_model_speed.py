#!/usr/bin/env python3
"""Benchmark individual Lemonade models to identify the exact fastest chat and coding candidates."""

import json
import time
import urllib.request


candidates = [
    "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "Qwen3.6-35B-A3B-MTP-GGUF",
    "qwen3.6-moe-35b-a3b-FLM"
]

prompt = "Write 1 paragraph explaining how an AGI swarm uses semantic routing."

for model in candidates:
    print(f"\n--- Testing {model} ---")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "stream": True
    }
    req = urllib.request.Request("http://127.0.0.1:13305/v1/chat/completions", headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
    t0 = time.perf_counter()
    ttft = None
    tokens = 0
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                l = line.decode('utf-8').strip()
                if l.startswith("data: ") and l != "data: [DONE]":
                    try:
                        d = json.loads(l[6:])
                        c = d["choices"][0]["delta"].get("content", "")
                        if c:
                            if ttft is None:
                                ttft = time.perf_counter() - t0
                            tokens += 1
                    except Exception:
                        pass
        total_t = time.perf_counter() - t0
        tps = tokens / (total_t - (ttft or 0)) if total_t > (ttft or 0) else 0
        print(f"✓ TTFT: {ttft:.2f}s | Total: {total_t:.2f}s | Tokens: {tokens} | Decode: {tps:.1f} tok/s")
    except Exception as e:
        print(f"✗ Failed: {e}")
