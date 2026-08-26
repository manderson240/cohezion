#!/usr/bin/env python3
"""
Local NPU Research & Synthesis for THUNLP ProactiveAgent (ICLR 2025)
====================================================================
Uses `qwen3.6-moe-35b-a3b-FLM` on AMD XDNA2 NPU to analyze THUNLP ProactiveAgent
architecture and design Cohezion's native `ProactiveAgent` engine.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path


LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "research"


def main():
    print("=== Researching THUNLP ProactiveAgent via Local NPU MoE (`qwen3.6-moe-35b-a3b-FLM`) ===")

    prompt = (
        "You are Cohezion's Lead AI Architect.\n"
        "Research the THUNLP ProactiveAgent (ICLR 2025) paradigm (shifting agents from reactive responses to active assistance).\n\n"
        "Synthesize 4 core architectural components for Cohezion's `ProactiveAgent` system:\n"
        "1. `ActivitySensingGym`: User activity & environment event tracking.\n"
        "2. `ProactiveGoalPredictor`: Anticipating implicit user intent before explicit prompting.\n"
        "3. `ProactiveTriggerGate`: Threshold evaluation (confidence >= 0.75) for proactive intervention.\n"
        "4. `ProactiveExecutor`: Dispatching zero-cost verified actions via AutoHarness & OOMGuard.\n\n"
        "Provide clear design specifications and Python implementation outlines."
    )

    payload = {
        "model": "qwen3.6-moe-35b-a3b-FLM",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        LEMONADE_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            msg = res["choices"][0]["message"]
            synthesis = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            print(f"  ✓ NPU Research Synthesis completed in {dt}s")

            VAULT_DIR.mkdir(parents=True, exist_ok=True)
            report_file = VAULT_DIR / "THUNLP_PROACTIVE_AGENT_RESEARCH.md"
            report_file.write_text(f"# THUNLP ProactiveAgent Research & Synthesis\n*Date: 2026-08-03*\n*Model: qwen3.6-moe-35b-a3b-FLM (NPU MoE)*\n\n{synthesis}")
            print(f"✅ Research note written to Vault: {report_file}")
    except Exception as e:
        print("! Local research query note:", e)


if __name__ == "__main__":
    main()
