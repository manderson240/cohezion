#!/usr/bin/env python3
"""Brutally Honest Leaderboard Post-Mortem via Tier 2 Ollama Cloud Fleet.

Queries `deepseek-v4-pro:cloud` to pinpoint why ARC / Kaggle baselines score low
and what Grandmaster techniques actually bridge the gap from 5% to 50%+ on ARC Prize.
"""

import httpx
import json

prompt = """You are a Kaggle Grandmaster and ARC Prize 2024/2026 Winner.
Be BRUTALLY HONEST.
Context:
- Our current ARC solver uses:
  1. Handcrafted geometric transforms (rotations, flips, crops, fills, color remapping).
  2. Neural Cellular Automata (NCA) 3x3 flood fill.
  3. Zero-shot LLM program synthesis (Qwen2.5-Coder / DeepSeek-R1).
  4. 4-depth compositional search.
  
Why does this score low (e.g. ~5-15% on ARC Private Evaluation) compared to the leaders (35% - 72%)?
What are we doing fundamentally WRONG or MISSING?

Specifically analyze:
1. DSL Design: Are our primitive transforms too narrow compared to Michael Hodel's ARC DSL or icecuber's C++ solver?
2. Object Segmentation: Are we treating grids as flat matrices instead of connected component graphs / hierarchical objects?
3. Test-Time Fine-Tuning: Are zero-shot LLM prompts failing without test-time LoRA adaptation on augmented training pairs?
4. Concrete 3-step prescription to jump from <15% to 40%+ on ARC-AGI-2.
Keep it concise, direct, and under 250 words."""

try:
    resp = httpx.post("http://127.0.0.1:11434/api/generate", json={
        "model": "deepseek-v4-pro:cloud",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 600}
    }, timeout=45.0)
    
    if resp.status_code == 200:
        data = resp.json()
        print("💡 BRUTALLY HONEST POST-MORTEM:")
        print("=" * 80)
        print(data.get("response", ""))
        print("=" * 80)
    else:
        print(f"HTTP {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Notice: {e}")
