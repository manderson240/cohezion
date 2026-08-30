#!/usr/bin/env python3
"""Consult Model Fleet on Optimal Next Action.

Queries `deepseek-v4-flash:cloud` / `deepseek-v4-pro:cloud` to determine the highest-leverage
next technical milestone for Cohezion.
"""

import httpx
import json

prompt = """You are an elite autonomous AGI & Systems Architect.
Current System State:
1. Competition Submissions: All 5 Kaggle tracks (ARC-AGI-2, ARC-AGI-3, Pokémon TCG, RSNA Knee, Biohub Cell) have deployed kernels running with hardened schemas, AWQ INT4 dual-T4 GPUs, and CPU inference engines.
2. Metadata & ML Modules: Built, tested, and aligned with all 4 platform blueprints (ARC shape/color invariants, Pokémon legality action masks, RSNA DICOM FiLM modulation, Biohub OME-Zarr Riemannian distance metric).
3. Background Daemons: Master Daemon Strategic Roadmap registry active; DiskGuardrail managing NVMe storage and log rotation.

What are the 3 highest-leverage NEXT steps we should execute right now to accelerate emergence, leaderboard progression, and sovereign capabilities?
Keep it actionable, highly technical, and under 150 words."""

try:
    resp = httpx.post("http://127.0.0.1:11434/api/generate", json={
        "model": "deepseek-v4-flash:cloud",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 400}
    }, timeout=30.0)
    
    if resp.status_code == 200:
        res = resp.json().get("response", "").strip()
        print("💡 MODEL STRATEGIC RECOMMENDATION:")
        print("=" * 70)
        print(res)
        print("=" * 70)
    else:
        print(f"HTTP {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Notice: {e}")
