#!/usr/bin/env python3
"""NPU Benchmark - FLM XDNA2 Performance Test"""

import subprocess
import time

import requests


# Start FLM server
print("Starting FLM NPU server...")
proc = subprocess.Popen(
    ["/usr/bin/flm", "serve", "gemma3:4b", "--port", "8004", "--pmode", "performance"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

# Wait for server
print("Waiting for server...")
for i in range(10):
    try:
        resp = requests.get("http://localhost:8004/v1/models", timeout=2)
        if resp.status_code == 200:
            print("Server ready!")
            break
    except:
        pass
    time.sleep(1)
else:
    print("Server failed to start")
    proc.terminate()
    exit(1)

# Benchmark
print("Benchmarking NPU...")
start = time.time()
total_tokens = 0

for i in range(4):
    try:
        resp = requests.post(
            "http://localhost:8004/v1/chat/completions",
            json={
                "model": "gemma3:4b",
                "messages": [{"role": "user", "content": f"Write haiku {i}"}],
                "max_tokens": 40
            },
            timeout=30
        )
        data = resp.json()
        tokens = data.get("usage", {}).get("completion_tokens", 0)
        total_tokens += tokens
        print(f"  Request {i+1}: {tokens} tokens")
    except Exception as e:
        print(f"  Request {i+1} failed: {e}")

elapsed_ms = (time.time() - start) * 1000
tps = total_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

print(f"\nTotal: {total_tokens} tokens in {elapsed_ms:.0f}ms")
print(f"NPU TPS: {tps:.1f}")
print(f"\nMETRIC tokens_per_sec={tps:.1f}")

proc.terminate()
