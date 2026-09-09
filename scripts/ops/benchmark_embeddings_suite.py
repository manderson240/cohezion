#!/usr/bin/env python3
"""Benchmark and verify Local Embedding Models on Lemonade port 13305 (NPU vs iGPU vs CPU)."""

from __future__ import annotations

import json
import time
import urllib.request

import numpy as np


URL = "http://localhost:13305/v1/embeddings"

EMBED_MODELS = [
    {
        "id": "embed-gemma-300m-FLM",
        "silicon": "AMD XDNA2 NPU (recipe: flm)",
        "desc": "Ultra-lightweight on-chip NPU embeddings"
    },
    {
        "id": "Qwen3-Embedding-0.6B-GGUF",
        "silicon": "Radeon 8060S iGPU (Vulkan 8k ctx)",
        "desc": "High-density MTEB leader on iGPU"
    },
    {
        "id": "lfm25-embed-350m",
        "silicon": "CPU / iGPU (128k context)",
        "desc": "Long-context Liquid AI embedding model"
    },
    {
        "id": "nomic-embed-text-v2-moe-GGUF",
        "silicon": "CPU / iGPU MoE",
        "desc": "Nomic MoE sparse embedding model"
    }
]

TEST_TEXTS = [
    "Kenneth Shoulders discovered Exotic Vacuum Objects (EVOs) traveling along dielectric guide rails.",
    "Dr. Takaaki Matsumoto observed 42-satellite itonic decay rings on nuclear emulsions.",
    "The AMD Strix Halo architecture features an XDNA2 NPU and RDNA 3.5 iGPU on a unified memory bus."
]


def test_embedding(model_info: dict) -> None:
    print(f"\n--- Testing: {model_info['id']} ({model_info['silicon']}) ---")
    payload = {
        "model": model_info["id"],
        "input": TEST_TEXTS
    }
    req = urllib.request.Request(
        URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dt = time.perf_counter() - t0
            data = json.loads(resp.read().decode("utf-8"))
            vectors = [item["embedding"] for item in data.get("data", [])]
            dim = len(vectors[0]) if vectors else 0

            # Compute cosine similarity between text 0 (Shoulders) and text 1 (Matsumoto)
            v0 = np.array(vectors[0])
            v1 = np.array(vectors[1])
            v2 = np.array(vectors[2])

            sim_01 = np.dot(v0, v1) / (np.linalg.norm(v0) * np.linalg.norm(v1))
            sim_02 = np.dot(v0, v2) / (np.linalg.norm(v0) * np.linalg.norm(v2))

            print(f"✓ Latency: {dt*1000:.1f}ms for 3 texts ({len(vectors)} vectors)")
            print(f"  Vector Dimension: {dim}D")
            print(f"  Physics Similarity (Shoulders <-> Matsumoto): {sim_01:.4f}")
            print(f"  Cross-Domain Similarity (Shoulders <-> AMD Hardware): {sim_02:.4f}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def main() -> None:
    print("=" * 85)
    print("  📊 BENCHMARKING LOCAL EMBEDDING SUITE ON LEMONADE (PORT 13305)")
    print("=" * 85)

    for m in EMBED_MODELS:
        test_embedding(m)

    print("\n" + "=" * 85)
    print("🎉 EMBEDDING BENCHMARK COMPLETE!")
    print("=" * 85)


if __name__ == "__main__":
    main()
