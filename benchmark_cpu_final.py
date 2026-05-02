#!/usr/bin/env python3
"""CPU Dedicated Benchmark - Using llama-server directly on CPU backend"""

import os
import subprocess
import time

import requests


def main():
    model_path = "/var/lib/lemonade/.cache/huggingface/hub/models--unsloth--Qwen3-0.6B-GGUF/snapshots/50968a4468ef4233ed78cd7c3de230dd1d61a56b/Qwen3-0.6B-Q4_0.gguf"

    print("Starting CPU-only llama-server on port 8008...")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = "/var/lib/lemonade/.cache/lemonade/bin/llamacpp/cpu"

    proc = subprocess.Popen(
        [
            "/var/lib/lemonade/.cache/lemonade/bin/llamacpp/cpu/llama-server",
            "-m",
            model_path,
            "--port",
            "8008",
            "-ngl",
            "0",
            "-t",
            "16",
            "--ctx-size",
            "2048",
            "-fa",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Wait for ready
    print("Waiting for server...")
    ready = False
    for _ in range(15):
        try:
            resp = requests.get("http://localhost:8008/v1/models", timeout=1)
            if resp.status_code == 200:
                print("Server ready!")
                ready = True
                break
        except:
            pass
        time.sleep(1)

    if not ready:
        print("Server failed to start")
        proc.terminate()
        return

    # Benchmark
    print("\nBenchmarking CPU (Qwen3-0.6B, 16 threads)...")
    start = time.time()
    total_tokens = 0

    for i in range(4):
        try:
            resp = requests.post(
                "http://localhost:8008/v1/chat/completions",
                json={
                    "model": "Qwen3-0.6B-Q4_0",
                    "messages": [{"role": "user", "content": f"Write haiku {i}"}],
                    "max_tokens": 40,
                },
                timeout=30,
            )
            data = resp.json()
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            total_tokens += tokens
            print(f"  Request {i + 1}: {tokens} tokens")
        except Exception as e:
            print(f"  Error on request {i + 1}: {e}")

    elapsed_ms = (time.time() - start) * 1000
    tps = total_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

    print("\nCPU Results:")
    print(f"  Total: {total_tokens} tokens in {elapsed_ms:.0f}ms")
    print(f"  CPU TPS: {tps:.1f}")
    print(f"\nMETRIC tokens_per_sec={tps:.1f}")

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()


if __name__ == "__main__":
    main()
