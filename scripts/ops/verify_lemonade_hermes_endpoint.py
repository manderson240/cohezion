#!/usr/bin/env python3
"""Test Lemonade OpenAI API compatibility for Hermes Desktop client."""

import json
import time
import urllib.request


url = "http://localhost:13305/v1/chat/completions"
payload = {
    "model": "omnirouter",  # or custom cohezion router
    "messages": [
        {"role": "system", "content": "You are Hermes assistant."},
        {"role": "user", "content": "Hello Hermes! Check system status and tell me what model you are routing through."}
    ],
    "temperature": 0.3,
    "max_tokens": 200
}

req = urllib.request.Request(
    url,
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

print(f"Sending test chat completion to Lemonade ({url})...")
t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        dt = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        print(f"✓ Response in {dt:.2f}s:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"✗ Request failed: {e}")
