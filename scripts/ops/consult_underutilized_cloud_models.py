#!/usr/bin/env python3
"""Multi-Perspective Ensemble using Underutilized Cloud Models:
1. `gemma4:31b-cloud` (Only 3 requests this week)
2. `nemotron-3-ultra:cloud` (Only 5 requests this week)
3. `kimi-k2.6:cloud` (Only 3 requests this week)
4. `gpt-oss:120b-cloud` (Only 13 requests this week)

Dispatches targeted architectural reasoning tasks to each underutilized model.
"""

import asyncio
import time
import httpx

TASKS = [
    {
        "model": "gemma4:31b-cloud",
        "role": "Multimodal Vision & Geometric Invariant Specialist",
        "prompt": "You are a Vision & Geometry Lead. In 50 words, explain how multi-scale discrete Fourier transforms and topological persistence diagrams detect repeating grid motifs in ARC-AGI-2."
    },
    {
        "model": "nemotron-3-ultra:cloud",
        "role": "Systems Engineering & Quantum Optimization Lead",
        "prompt": "You are a Systems Optimization Lead. In 50 words, explain how compiling quantum kernel lookups into static contiguous FP16 memory blocks achieves sub-0.01ms inference inside Kaggle code competitions."
    },
    {
        "model": "kimi-k2.6:cloud",
        "role": "Long-Horizon Planning & Combinatorial Game Strategist",
        "prompt": "You are a Strategic Game Theory Lead. In 50 words, explain how public belief state tracking and virtual loss parallelization scale ISMCTS rollouts for Pokémon TCG AI."
    },
    {
        "model": "gpt-oss:120b-cloud",
        "role": "Formal Verification & Rigorous Proof Lead",
        "prompt": "You are a Formal Methods Lead. In 50 words, explain why Mercer-compliant Positive Semi-Definite (PSD) quantum kernels prevent matrix inversion singularity in Ridge Regression."
    }
]

async def query_model(task: dict) -> dict:
    model = task["model"]
    role = task["role"]
    prompt = task["prompt"]
    t0 = time.perf_counter()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 200}
                },
                timeout=45.0
            )
            dt = time.perf_counter() - t0
            out = resp.json().get("response", "").strip() if resp.status_code == 200 else f"HTTP {resp.status_code}"
            return {"model": model, "role": role, "latency_s": dt, "output": out, "status": "SUCCESS"}
        except Exception as e:
            dt = time.perf_counter() - t0
            return {"model": model, "role": role, "latency_s": dt, "output": str(e), "status": "ERROR"}

async def main():
    print("=" * 90)
    print("🚀 DISPATCHING TASKS TO UNDERUTILIZED OLLAMA CLOUD MODELS")
    print("=" * 90)
    tasks = [query_model(t) for t in TASKS]
    results = await asyncio.gather(*tasks)

    for r in results:
        print(f"\n--- 🤖 [{r['model']}] ({r['role']}) | Latency: {r['latency_s']:.2f}s ---")
        print(f"Output:\n{r['output']}\n")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(main())
