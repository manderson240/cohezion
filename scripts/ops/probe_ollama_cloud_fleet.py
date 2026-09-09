#!/usr/bin/env python3
"""Probe Ollama Cloud Fleet for Kimi-k3, Minimax-m3, GLM-5.3, Nemotron-3, and Kimi-k2.7.

Queries each model with a quick prompt to verify availability, latency, and capabilities.
"""

import asyncio
import time
import httpx

MODELS_TO_PROBE = [
    "kimi-k3:cloud",
    "minimax-m3:cloud",
    "glm-5.3-flash:cloud",
    "kimi-k2.7-code:cloud",
    "nemotron-3-super:cloud",
    "gpt-oss:120b-cloud"
]

PROMPT = "In under 25 words, confirm you are online and describe your frontier capability."

async def probe_model(model_name: str) -> dict:
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": PROMPT,
                    "stream": False,
                    "options": {"num_predict": 60}
                },
                timeout=35.0
            )
            dt = time.perf_counter() - t0
            if resp.status_code == 200:
                out = resp.json().get("response", "").strip()
                return {"model": model_name, "status": "ONLINE", "latency_s": dt, "output": out}
            else:
                return {"model": model_name, "status": f"HTTP_{resp.status_code}", "latency_s": dt, "output": resp.text}
    except Exception as e:
        dt = time.perf_counter() - t0
        return {"model": model_name, "status": "ERROR", "latency_s": dt, "output": str(e)}

async def main():
    print("=" * 80)
    print("🚀 PROBING RECENTLY ACCESSIBLE OLLAMA CLOUD MODELS")
    print("=" * 80)
    tasks = [probe_model(m) for m in MODELS_TO_PROBE]
    results = await asyncio.gather(*tasks)
    
    for r in results:
        status_icon = "🟢" if r["status"] == "ONLINE" else "🔴"
        print(f"\n{status_icon} [{r['model']}] | Status: {r['status']} | Latency: {r['latency_s']:.2f}s")
        print(f"Output: {r['output']}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
