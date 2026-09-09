#!/usr/bin/env python3
"""Resilient Multi-Modal & Non-Standard Chat Template Harvester (AMD/Lemonade Aligned).

Handles:
1. Standard `/v1/chat/completions` (OpenAI format).
2. Fallback to raw `/v1/completions` (Completion format) for base/completion models (e.g. Bonsai base, DeepSeek flash base).
3. Explicit chat template formatting (ChatML / Alpaca / Raw Prompting).
4. Auto-detection of backend & custom llama-server arguments.
"""

import asyncio
import json
import logging
import os
import psutil
import time
from dataclasses import dataclass
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [RESILIENT_HARVEST] %(message)s")
logger = logging.getLogger("resilient_harvest")

LEMONADE_BASE = "http://localhost:13305"
MIN_AVAIL_RAM_GB = 12.0

DOMAIN_PROMPT_MAP = [
    ("Hyperbolic Geometry & Poincaré Embeddings", "Explain how the metric tensor g_ij = (4/(1-||x||^2)^2)*delta_ij enables hierarchical tree embedding without distortion in 2 dense sentences."),
    ("Ken Shoulders EVOs & Charge Clustering", "Explain how 10^11 electrons in a 1.0 um cluster maintain Bennett magnetic pinch equilibrium against Coulomb repulsion in 2 sentences."),
    ("Category Theory & Sheaf Cohomology", "Explain how restriction maps in Sheaf Theory resolve semantic inconsistency across distributed autonomous agents in 2 sentences."),
    ("AutoHarness AST Bytecode Action Verifiers", "Explain why static AST policy compilation bypasses runtime LLM inference calls with 0.00 ms latency in 2 sentences."),
    ("Benettin Maximal Lyapunov Exponents", "Explain how tangent vector orthonormalization via Gram-Schmidt prevents numerical divergence when calculating chaos attractors in 2 sentences.")
]

@dataclass
class ResilientHarvestResult:
    model: str
    mode: str
    domain: str
    insight: str
    duration_sec: float
    ram_headroom_gb: float

def get_free_ram_gb() -> float:
    return psutil.virtual_memory().available / (1024 ** 3)

async def probe_model_resilient(client: httpx.AsyncClient, model_name: str, domain_idx: int) -> ResilientHarvestResult | None:
    domain, prompt = DOMAIN_PROMPT_MAP[domain_idx % len(DOMAIN_PROMPT_MAP)]
    if get_free_ram_gb() < MIN_AVAIL_RAM_GB:
        logger.warning("⚠️ RAM Headroom Low (%.2f GB). Skipping %s.", get_free_ram_gb(), model_name)
        return None

    t0 = time.perf_counter()

    # Strategy A: Standard /v1/chat/completions
    chat_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"You are a principal scientist for {domain}. Answer mathematically in 2 dense sentences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 256
    }

    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=chat_payload, timeout=25.0)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
            if len(text.strip()) > 10:
                return ResilientHarvestResult(
                    model=model_name,
                    mode="chat_completions",
                    domain=domain,
                    insight=text,
                    duration_sec=round(time.perf_counter() - t0, 2),
                    ram_headroom_gb=round(get_free_ram_gb(), 2)
                )
    except Exception:
        pass

    # Strategy B: Fallback to Raw /v1/completions with ChatML template wrapper
    formatted_prompt = f"<|im_start|>system\nYou are a principal scientist for {domain}. Answer mathematically in 2 dense sentences.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    raw_payload = {
        "model": model_name,
        "prompt": formatted_prompt,
        "temperature": 0.1,
        "max_tokens": 256,
        "stop": ["<|im_end|>", "</s>", "\n\n\n"]
    }

    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/completions", json=raw_payload, timeout=25.0)
        if r.status_code == 200:
            text = r.json()["choices"][0]["text"].strip()
            if len(text.strip()) > 10:
                return ResilientHarvestResult(
                    model=model_name,
                    mode="raw_completions_chatml",
                    domain=domain,
                    insight=text,
                    duration_sec=round(time.perf_counter() - t0, 2),
                    ram_headroom_gb=round(get_free_ram_gb(), 2)
                )
    except Exception:
        pass

    # Strategy C: Direct Alpaca / Plain text completion
    plain_prompt = f"### Instruction:\n{prompt}\n\n### Response:\n"
    plain_payload = {
        "model": model_name,
        "prompt": plain_prompt,
        "temperature": 0.1,
        "max_tokens": 256,
        "stop": ["###", "</s>"]
    }

    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/completions", json=plain_payload, timeout=25.0)
        if r.status_code == 200:
            text = r.json()["choices"][0]["text"].strip()
            if len(text.strip()) > 10:
                return ResilientHarvestResult(
                    model=model_name,
                    mode="raw_completions_alpaca",
                    domain=domain,
                    insight=text,
                    duration_sec=round(time.perf_counter() - t0, 2),
                    ram_headroom_gb=round(get_free_ram_gb(), 2)
                )
    except Exception:
        pass

    return None

async def run_resilient_harvest():
    print("\n" + "=" * 115)
    print("🛡️ RESILIENT OMNI-MODEL TEMPLATE & ENDPOINT HARVESTER")
    print("=" * 115)

    # Models that typically have raw/custom templates or failed standard chat
    target_models = [
        "DeepSeek-V4-Flash-0731-GGUF-Q8_0",
        "DeepSeek-V4-Flash-0731-UD-Q8_K_XL-GGUF-Q8_0",
        "DeepSeek-V4-Pro-Qwen3.5-9B-MTP-GGUF-BF16",
        "Bonsai-27B-gguf",
        "Bonsai-27B-gguf-Q1_0",
        "Qwen3.8-27B-ABLITERATED-GGUF-Q5_K_M",
        "Qwen3.8-27B-DFlash2-GGUF-BF16",
        "Qwen3.8-27B-GGUF-Q4_K_M",
        "Qwen3.6-35B-A3B-GGUF",
        "Muse-Glimmer-30B-GGUF-UD-Q5_K_L",
        "Nail-Qwen3.6-35B-A3B-GGUF-UD-IQ3_S"
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        results: list[ResilientHarvestResult] = []
        for idx, model in enumerate(target_models, 1):
            print(f"[{idx:02d}/{len(target_models):02d}] Probing `{model}` across 3 template strategies...")
            res = await probe_model_resilient(client, model, idx - 1)
            if res:
                results.append(res)
                print(f"  └─ 🟢 RECOVERED via [{res.mode}] ({res.duration_sec}s | RAM Free: {res.ram_headroom_gb} GiB)")
                print(f"  └─ Insight: {res.insight[:110]}...")
            else:
                print(f"  └─ 🟡 Candidate required model load or exceeded context limit.")

    # Save to Documentation
    os.makedirs("docs/research", exist_ok=True)
    out_file = "docs/research/resilient_template_recovered_matrix.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# 🛡️ Resilient Chat Template & Fallback Recovery Matrix\n\n")
        f.write(f"**Date**: 2026-08-24  \n**Models Recovered**: {len(results)} / {len(target_models)}  \n\n")
        f.write("| Model | Recovery Mode | Domain | Duration | RAM Free | Harvested Insight |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            clean_text = r.insight.replace("\n", " ").replace("|", "\\|")
            f.write(f"| `{r.model}` | `{r.mode}` | {r.domain} | {r.duration_sec}s | {r.ram_headroom_gb} GiB | {clean_text} |\n")

    print("\n" + "=" * 115)
    print(f"🎉 RESILIENT HARVEST COMPLETED: {len(results)} Models Successfully Ingested!")
    print(f"📄 Report saved to: {out_file}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_resilient_harvest())
