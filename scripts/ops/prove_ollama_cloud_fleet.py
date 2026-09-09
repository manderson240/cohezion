#!/usr/bin/env python3
"""Live Verification & Multi-Model Proof Harness for the 13-Model Ollama Cloud Fleet.

Queries each of the 13 registered Ollama Cloud models through the local Ollama API
daemon (http://localhost:11434/api/chat) on specialized domain prompts to prove
live end-to-end routing, response generation, latency, and capability mapping.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CLOUD_PROOF] %(message)s")
logger = logging.getLogger("cloud_proof")

OLLAMA_BASE = "http://localhost:11434"

TEST_FLEET = [
    ("deepseek-v4-pro:cloud", "1.6T Reasoning", "State the core invariant of Sheaf Cohomology restriction maps in 1 sentence."),
    ("kimi-k3:cloud", "Deep Planning", "Outline a 3-step autonomous recovery plan for an OOM-faulted agent loop in 1 sentence."),
    ("qwen3.5:397b-cloud", "397B Coding", "Write a Python lambda that checks if a 12D state vector norm is < 1.0 in 1 line."),
    ("kimi-k2.7-code:cloud", "Code Tools", "Define the AST node type for a Python function call in 1 sentence."),
    ("glm-5.2:cloud", "Frontier Multimodal", "Explain how Poincaré ball distance scales near the unit boundary in 1 sentence."),
    ("nemotron-3-ultra:cloud", "Enterprise Research", "State the primary benefit of SurrealDB v2 RELATE graph schema in 1 sentence."),
    ("nemotron-3-super:cloud", "Frontier Physics", "Explain how Bennett pinch equilibrium stabilizes Ken Shoulders EVOs in 1 sentence."),
    ("deepseek-v4-flash:cloud", "Fast QA", "What is the capital of France? Answer in 1 word."),
    ("deepseek-v4-flash:0731-cloud", "Ultra-Fast Draft", "Summarize why AutoHarness executes in 0ms in 1 sentence."),
    ("kimi-k2.6:cloud", "2M Long Context", "Explain why 2M context windows enable complete codebase RAG in 1 sentence."),
    ("minimax-m3:cloud", "Creative Synthesis", "Synthesize a metaphor comparing AI agent swarms to biological ant colonies in 1 sentence."),
    ("gemma4:31b-cloud", "Dense Embeddings", "Define semantic vector cosine similarity in 1 sentence."),
    ("gpt-oss:120b-cloud", "120B General", "Confirm your operating status on the cloud inference fleet in 1 sentence.")
]

@dataclass
class ProofResult:
    model: str
    role: str
    prompt: str
    response: str
    duration_sec: float
    status: str

async def verify_cloud_model(client: httpx.AsyncClient, model: str, role: str, prompt: str) -> ProofResult:
    t0 = time.perf_counter()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a specialized frontier AI model. Respond directly, concisely, and accurately."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 128
        }
    }

    try:
        r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=40.0)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            text = data.get("message", {}).get("content", "").strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
            return ProofResult(
                model=model,
                role=role,
                prompt=prompt,
                response=text.replace("\n", " "),
                duration_sec=dt,
                status="✅ PASS"
            )
        else:
            return ProofResult(
                model=model,
                role=role,
                prompt=prompt,
                response=f"HTTP {r.status_code}: {r.text[:80]}",
                duration_sec=dt,
                status="❌ FAIL"
            )
    except Exception as e:
        dt = round(time.perf_counter() - t0, 2)
        return ProofResult(
            model=model,
            role=role,
            prompt=prompt,
            response=f"Error: {str(e)[:80]}",
            duration_sec=dt,
            status="❌ TIMEOUT/ERR"
        )

async def run_fleet_proof():
    print("\n" + "=" * 115)
    print("☁️ LIVE PROOF HARNESS: OLLAMA CLOUD 13-MODEL FRONTIER FLEET")
    print(f"• Target Endpoint : {OLLAMA_BASE}/api/chat")
    print(f"• Total Models    : {len(TEST_FLEET)}")
    print("=" * 115)

    results: list[ProofResult] = []
    async with httpx.AsyncClient(timeout=45.0) as client:
        for idx, (model, role, prompt) in enumerate(TEST_FLEET, 1):
            print(f"\n[{idx:02d}/{len(TEST_FLEET):02d}] Probing `{model}` ({role})...")
            res = await verify_cloud_model(client, model, role, prompt)
            results.append(res)
            print(f"  └─ Status: {res.status} ({res.duration_sec}s)")
            print(f"  └─ Reply : {res.response[:110]}...")

    print("\n" + "=" * 115)
    print("📋 OLLAMA CLOUD 13-MODEL LIVE INFERENCE SCORECARD")
    print("=" * 115)
    passed = sum(1 for r in results if r.status == "✅ PASS")
    print(f"• Success Rate: {passed} / {len(results)} ({passed/len(results)*100:.1f}%)")
    print("-" * 115)
    for r in results:
        print(f"{r.status} | {r.model:<32} | {r.duration_sec:>5.2f}s | {r.response[:60]}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_fleet_proof())
