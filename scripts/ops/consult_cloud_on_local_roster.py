#!/usr/bin/env python3
"""Consult Underutilized Ollama Cloud Models to Critique and Recommend the Optimal Local Silicon Model Roster.

Queries:
1. `kimi-k2.6:cloud` - Strategic evaluation of resident local models on AMD Strix Halo (128GB UMA).
2. `gpt-oss:120b-cloud` - Technical evaluation of NPU FLM vs iGPU GGUF vs CPU offload candidates.
"""

import httpx
import json

DOWNLOADED_LOCAL_MODELS = [
    "DeepSeek-Qwen3-8B-GGUF",
    "Gemma-4-26B-A4B-it-GGUF (Active in slot)",
    "Gemma-4-E2B-it-GGUF",
    "Gemma-4-E4B-it-GGUF (Active in slot)",
    "Qwen3-0.6B-GGUF",
    "Qwen3-8B-GGUF",
    "Qwen3.6-35B-A3B-GGUF",
    "Qwen3.6-35B-A3B-MTP-GGUF",
    "deepseek-r1-0528-8b-FLM",
    "embed-gemma-300m-FLM",
    "gemma3-1b-FLM",
    "gpt-oss-20b-mxfp4-GGUF",
    "kokoro-v1 (TTS)",
    "lfm2.5-it-1.2b-FLM",
    "llama3.2-1b-FLM (Active in slot)",
    "llama3.2-3b-FLM",
    "nomic-embed-text-v2-moe-GGUF (Active in slot)",
    "qwen3-4b-FLM",
    "qwen3vl-it-4b-FLM"
]

prompt = f"""You are a Principal AI Hardware Systems Architect evaluating local model residency on AMD Strix Halo (128GB Unified Memory, XDNA2 NPU, Radeon 8060S iGPU).

Currently resident models in active Lemonade slots:
1. GPU Slot 1: Gemma-4-26B-A4B-it-GGUF (262k ctx)
2. GPU Slot 2: Gemma-4-E4B-it-GGUF (131k ctx)
3. NPU Slot 1: llama3.2-1b-FLM (131k ctx)
4. GPU Slot 3: nomic-embed-text-v2-moe-GGUF (512 ctx)

Other available downloaded local models ready to load:
{json.dumps(DOWNLOADED_LOCAL_MODELS, indent=2)}

Critique this resident setup:
1. Is Gemma-4-26B + Gemma-4-E4B + llama3.2-1b the optimal combination, or should we swap in higher-leverage models like Qwen3.6-35B-A3B-GGUF (MoE coding/research), deepseek-r1-8b-FLM (deep reasoning), or gpt-oss-20b-mxfp4?
2. What exact 4 resident models should be loaded right now to maximize coding power, deep mathematical reasoning, fast tool dispatch, and dense embeddings?

Provide a crisp, actionable recommendation in under 180 words."""

print("=" * 80)
print("☁️ CONSULTING OLLAMA CLOUD MODELS ON OPTIMAL LOCAL MODEL RESIDENCY")
print("=" * 80)

# Query kimi-k2.6:cloud
print("▶ Querying kimi-k2.6:cloud...")
try:
    resp1 = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": "kimi-k2.6:cloud", "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 350}},
        timeout=40.0
    )
    if resp1.status_code == 200:
        print("\n--- 🤖 [kimi-k2.6:cloud] Recommendation ---")
        print(resp1.json().get("response", "").strip())
except Exception as e:
    print(f"Notice: {e}")

# Query gpt-oss:120b-cloud
print("\n▶ Querying gpt-oss:120b-cloud...")
try:
    resp2 = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": "gpt-oss:120b-cloud", "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 350}},
        timeout=40.0
    )
    if resp2.status_code == 200:
        print("\n--- 🤖 [gpt-oss:120b-cloud] Recommendation ---")
        print(resp2.json().get("response", "").strip())
except Exception as e:
    print(f"Notice: {e}")

print("=" * 80)
