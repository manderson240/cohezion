#!/usr/bin/env python3
"""Execute Deep Reasoning Evaluation on kimi-k3:cloud & minimax-m3:cloud.

Tasks:
1. ARC-AGI-2 Topological & Morphogenetic invariant reasoning.
2. Long-horizon planning strategy for Pokémon TCG MCTS.
"""

import asyncio
import time
import httpx

TEST_PROMPTS = [
    {
        "model": "kimi-k3:cloud",
        "task": "ARC-AGI Invariant Synthesis",
        "prompt": "You are a Kaggle Grandmaster. In 50 words, explain why combining Michael Levin's bioelectric voltage diffusion with Yann LeCun's JEPA latent energy minimization creates a superior solver for ARC-AGI-2 compared to pure autoregressive LLM prompting."
    },
    {
        "model": "minimax-m3:cloud",
        "task": "Hierarchical MCTS Planning",
        "prompt": "You are a Game Theory Grandmaster. In 50 words, explain how hierarchical goal-conditioned planning prevents value estimation collapse in imperfect-information games like Pokémon TCG."
    },
    {
        "model": "nemotron-3-super:cloud",
        "task": "AMD Strix Halo Roofline Saturation",
        "prompt": "You are a Hardware Systems Architect. In 50 words, explain how UMA contiguous KV paging and FP4 quantization maximize memory bandwidth saturation on AMD Strix Halo."
    }
]

async def run_reasoning_test(item: dict) -> dict:
    model = item["model"]
    task = item["task"]
    prompt = item["prompt"]
    t0 = time.perf_counter()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 250}
                },
                timeout=45.0
            )
            dt = time.perf_counter() - t0
            if resp.status_code == 200:
                out = resp.json().get("response", "").strip()
                return {"model": model, "task": task, "latency_s": dt, "output": out, "status": "SUCCESS"}
            else:
                return {"model": model, "task": task, "latency_s": dt, "output": f"HTTP {resp.status_code}", "status": "FAIL"}
        except Exception as e:
            dt = time.perf_counter() - t0
            return {"model": model, "task": task, "latency_s": dt, "output": str(e), "status": "ERROR"}

async def main():
    print("=" * 80)
    print("🧠 RUNNING DEEP REASONING ON RECENT OLLAMA CLOUD MODELS")
    print("=" * 80)
    tasks = [run_reasoning_test(t) for t in TEST_PROMPTS]
    results = await asyncio.gather(*tasks)

    for r in results:
        print(f"\n--- 🤖 [{r['model']}] ({r['task']}) | Latency: {r['latency_s']:.2f}s ---")
        print(f"Output:\n{r['output']}\n")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
