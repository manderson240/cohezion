#!/usr/bin/env python3
"""Direct Local Silicon Analysis of Liquid AI."""

import asyncio
import httpx
from pathlib import Path

PROMPT = "Summarize how Liquid AI (https://www.liquid.ai/) and Liquid Foundation Models (LFM2.5) continuous dynamical architectures benefit edge AI agent swarms on AMD hardware."

async def run():
    payload = {
        "model": "user.cohezion-hermes-router",
        "messages": [
            {"role": "user", "content": PROMPT}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post("http://localhost:13305/v1/chat/completions", json=payload)
        data = r.json()
        print("Raw response dict keys:", data.keys())
        msg = data["choices"][0]["message"]
        print("Message dict keys:", msg.keys())
        print("Message dict content:", repr(msg.get("content")))
        print("Message reasoning_content:", repr(msg.get("reasoning_content")))
        
        # In case the model puts output in reasoning_content or content
        final_text = msg.get("content") or msg.get("reasoning_content") or ""
        if final_text:
            Path("docs/research/liquid_ai_local_inference_report.md").write_text(
                f"# Liquid AI & Liquid Foundation Models (LFM2.5) Analysis\n\n**Generated via Local Silicon**: `user.cohezion-hermes-router` (:13305)\n\n" + final_text
            )
            print("Successfully written to docs/research/liquid_ai_local_inference_report.md")

if __name__ == "__main__":
    asyncio.run(run())
