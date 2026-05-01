#!/usr/bin/env python3
"""Dedicated CPU Backend Benchmark

Starts llama-server directly on CPU backend for pure CPU testing.
"""

import os
import subprocess
import time

import requests


def main():
    MODEL_PATH = "/var/lib/lemonade/.cache/huggingface/hub/models--unsloth--Qwen3-0.6B-GGUF/snapshots/*/Qwen3-0.6B-Q4_0.gguf"

    # Find model file
    import glob
    model_files = glob.glob(MODEL_PATH)
    if not model_files:
        print("Model not found, using any available small model...")
        # Fallback to find any small GGUF
        all_models = glob.glob("/var/lib/lemonade/.cache/huggingface/hub/**/Qwen*.gguf", recursive=True)
        if all_models:
            model_path = all_models[0]
        else:
            print("No models found")
            return
    else:
        model_path = model_files[0]

    print(f"Using model: {model_path}")

    # Start CPU llama-server
    print("\nStarting CPU llama-server on port 8005...")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = "/var/lib/lemonade/.cache/lemonade/bin/llamacpp/cpu"

    proc = subprocess.Popen(
        [
            "/var/lib/lemonade/.cache/lemonade/bin/llamacpp/cpu/llama-server",
            "-m", model_path,
            "--port", "8005",
            "-t", "16",  # 16 threads
            "-ngl", "0",  # No GPU layers (CPU only)
            "--ctx-size", "4096",
            "-fa",  # Flash attention
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )

    # Wait for server
    print("Waiting for server...")
    for i in range(20):
        try:
            resp = requests.get("http://localhost:8005/v1/models", timeout=1)
            if resp.status_code == 200:
                print("Server ready!")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("Server failed to start")
        proc.terminate()
        return

    # Benchmark
    print("\nBenchmarking CPU...")
    start = time.time()
    total_tokens = 0

    for i in range(4):
        try:
            resp = requests.post(
                "http://localhost:8005/v1/chat/completions",
                json={
                    "model": "Qwen3-0.6B",
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
            print(f"  Error: {e}")

    elapsed = (time.time() - start) * 1000
    tps = total_tokens / (elapsed / 1000) if elapsed > 0 else 0

    print("\nResults:")
    print(f"  Total: {total_tokens} tokens in {elapsed:.0f}ms")
    print(f"  CPU TPS: {tps:.1f}")
    print(f"\nMETRIC tokens_per_sec={tps:.1f}")

    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()
