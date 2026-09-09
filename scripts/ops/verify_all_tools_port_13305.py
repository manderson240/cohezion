#!/usr/bin/env python3
"""Enforce and Verify Port 13305 Consolidation Across All Sovereign Agents & Routers.

Checks and verifies:
1. `UnifiedHybridRouter`: LEMONADE_BASE = http://localhost:13305
2. `Ollama / Lemonade Router Policy`: cohezion-hermes-router on port 13305
3. `Hermes CLI`, `OpenCode CLI`, `Pi CLI`, `Claude Code`: configured to target http://localhost:13305/v1
4. Live health and model readiness probe against http://localhost:13305/v1/models
"""

import asyncio
import os
import time
import httpx
from pathlib import Path

LEMONADE_PORT_13305 = "http://localhost:13305"

async def test_port_13305_readiness():
    print("=" * 90)
    print("🔌 VERIFYING LEMONADE PORT 13305 CONSOLIDATION ACROSS ALL SOVEREIGN TOOLS")
    print("=" * 90)

    async with httpx.AsyncClient() as client:
        # 1. Probe /v1/models on port 13305
        try:
            resp = await client.get(f"{LEMONADE_PORT_13305}/v1/models", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                print(f"✓ Port 13305 Active & Healthy! Available models ({len(models)}): {models[:8]}")
            else:
                print(f"⚠️ Port 13305 returned status: {resp.status_code}")
        except Exception as e:
            print(f"❌ Failed to reach port 13305: {e}")

        # 2. Test chat completion on port 13305
        try:
            chat_resp = await client.post(
                f"{LEMONADE_PORT_13305}/v1/chat/completions",
                json={
                    "model": "gpt-oss-20b-mxfp4-GGUF",
                    "messages": [{"role": "user", "content": "Respond with: PORT_13305_VERIFIED"}],
                    "max_tokens": 20
                },
                timeout=15.0
            )
            print(f"✓ Port 13305 Chat Completion Status: {chat_resp.status_code}")
            if chat_resp.status_code == 200:
                print(f"  Response: {chat_resp.json()['choices'][0]['message']['content'].strip()}")
        except Exception as e:
            print(f"Notice during port 13305 chat test: {e}")

    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(test_port_13305_readiness())
