#!/usr/bin/env python3
"""Rigorous End-to-End Non-Rushed Verification of Hermes Local Inference Pipeline."""

import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"
model = "Qwen3-Coder-30B-A3B-Instruct-GGUF"

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "You are Hermes Agent on AMD Strix Halo."},
        {"role": "user", "content": "Confirm that you are operational in exactly 3 words."}
    ],
    "max_tokens": 30,
    "stream": True
}

print(f"1. Testing SSE Stream against {url}...")
req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())

t0 = time.perf_counter()
first_token_time = None
collected_text = ""

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            l = line.decode('utf-8').strip()
            if l.startswith("data: ") and l != "data: [DONE]":
                data = json.loads(l[6:])
                delta = data["choices"][0]["delta"]
                token = delta.get("content") or delta.get("reasoning_content") or ""
                if token:
                    if first_token_time is None:
                        first_token_time = time.perf_counter() - t0
                    collected_text += token
    total_time = time.perf_counter() - t0
    print("✓ Status: SUCCESS")
    print(f"⏱ TTFT: {first_token_time:.2f}s | Total: {total_time:.2f}s")
    print(f"📝 Response: '{collected_text.strip()}'")
except Exception as e:
    print(f"✗ Status: FAILED with error: {e}")
