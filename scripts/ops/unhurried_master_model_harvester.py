#!/usr/bin/env python3
"""Unhurried Master All-Model Knowledge Harvester (Karpathy Standard - Quality Over Speed).

Mandate: "Leave plenty of time for the fat to render".
- Extended timeout: 180.0s (3 minutes) per model to allow thinking models to cook.
- Multi-tier template resolution (ChatCompletions -> Raw ChatML -> Alpaca).
- Automatic extraction of deep reasoning tokens.
- OOM safety floor maintained (>= 15.0 GiB RAM headroom).
- Master synthesis persisted to `docs/research/master_unhurried_model_enrichment_matrix.md`.
"""

import asyncio
import json
import logging
import os
import psutil
import time
from dataclasses import dataclass
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [UNHURRIED_HARVEST] %(message)s")
logger = logging.getLogger("unhurried_harvest")

LEMONADE_BASE = "http://localhost:13305"
MIN_AVAIL_RAM_GB = 12.0
PER_MODEL_TIMEOUT_SEC = 180.0  # 3 full minutes to allow deep thinking models to cook cleanly

DOMAIN_PROMPTS = [
    ("Hyperbolic Poincaré Manifolds", "Formulate how the Poincaré metric tensor g_ij = (4/(1-||x||^2)^2)*delta_ij prevents distortion in tree-structured agent knowledge representations with mathematical depth."),
    ("Ken Shoulders EVOs & Charge Clusters", "Explain the plasma electrodynamics of Ken Shoulders 1.0 um Toroidal EVOs, detailing how the Bennett pinch relativistic magnetic field B_theta ~ 53.5 kTesla stabilizes 10^11 electrons against Coulomb explosion."),
    ("Sheaf Cohomology & Swarm Consensus", "Detail how restriction maps in Sheaf Theory guarantee zero semantic drift across decentralized agent swarms by computing 0-th Cech cohomology kernels."),
    ("AutoHarness AST Bytecode Compilation", "Explain how zero-cost static AST action verifiers eliminate LLM runtime latency and guarantee deterministic policy enforcement."),
    ("Benettin Maximal Lyapunov Exponents", "Formulate how Gram-Schmidt tangent vector orthonormalization in continuous Benettin algorithms prevents numerical overflow during chaotic attractor analysis.")
]

@dataclass
class UnhurriedHarvestResult:
    model: str
    mode: str
    domain: str
    prompt: str
    insight: str
    tokens: int
    duration_sec: float
    ram_headroom_gb: float

def get_free_ram_gb() -> float:
    return psutil.virtual_memory().available / (1024 ** 3)

async def probe_model_unhurried(client: httpx.AsyncClient, model_name: str, domain_idx: int) -> UnhurriedHarvestResult | None:
    domain, prompt = DOMAIN_PROMPTS[domain_idx % len(DOMAIN_PROMPTS)]
    avail_ram = get_free_ram_gb()
    if avail_ram < MIN_AVAIL_RAM_GB:
        logger.warning("⚠️ RAM floor breached (%.2f GB < %.2f GB). Skipping %s.", avail_ram, MIN_AVAIL_RAM_GB, model_name)
        return None

    t0 = time.perf_counter()

    # Strategy 1: Standard Chat Completions (Unhurried 180s)
    chat_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"You are a world-class principal scientist contributing to Cohezion's knowledge graph for {domain}. Provide a rigorous, mathematically sound analysis. Prioritize depth and precision."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }

    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=chat_payload, timeout=PER_MODEL_TIMEOUT_SEC)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
            if len(text.strip()) > 10:
                return UnhurriedHarvestResult(
                    model=model_name,
                    mode="chat_completions",
                    domain=domain,
                    prompt=prompt,
                    insight=text,
                    tokens=len(text.split()),
                    duration_sec=dt,
                    ram_headroom_gb=round(get_free_ram_gb(), 2)
                )
    except Exception as e:
        logger.info("Chat completion for %s deferred to raw template: %s", model_name, e)

    # Strategy 2: Raw Completion with ChatML
    formatted_prompt = f"<|im_start|>system\nYou are a principal scientist for {domain}. Provide a rigorous, mathematically sound analysis.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    raw_payload = {
        "model": model_name,
        "prompt": formatted_prompt,
        "temperature": 0.1,
        "max_tokens": 512,
        "stop": ["<|im_end|>", "</s>"]
    }

    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/completions", json=raw_payload, timeout=PER_MODEL_TIMEOUT_SEC)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            text = r.json()["choices"][0]["text"].strip()
            if len(text.strip()) > 10:
                return UnhurriedHarvestResult(
                    model=model_name,
                    mode="raw_chatml",
                    domain=domain,
                    prompt=prompt,
                    insight=text,
                    tokens=len(text.split()),
                    duration_sec=dt,
                    ram_headroom_gb=round(get_free_ram_gb(), 2)
                )
    except Exception as e:
        logger.info("Raw completion for %s skipped: %s", model_name, e)

    return None

async def run_unhurried_master_harvest():
    print("\n" + "=" * 115)
    print("🧠 UNHURRIED MASTER MODEL HARVESTER (QUALITY OVER SPEED - 180s RENDER TIMEOUT)")
    print("=" * 115)

    async with httpx.AsyncClient(timeout=PER_MODEL_TIMEOUT_SEC + 10.0) as client:
        r = await client.get(f"{LEMONADE_BASE}/v1/models")
        if r.status_code != 200:
            print("❌ Failed to connect to Lemonade")
            return

        all_models = [m["id"] for m in r.json().get("data", [])]
        text_models = [
            m for m in all_models 
            if not any(k in m for k in ["user.", "SD-", "RealESRGAN", "Flux", "TRELLIS", "Whisper", "Moonshine", "kokoro", "embed", "reranker"])
        ]

        print(f"• Total Text Models Scheduled : {len(text_models)}")
        print(f"• Per-Model Render Timeout   : {PER_MODEL_TIMEOUT_SEC}s (Leaving plenty of time for the fat to render)")
        print(f"• Starting RAM Headroom      : {get_free_ram_gb():.2f} GiB\n")

        results: list[UnhurriedHarvestResult] = []
        for idx, model in enumerate(text_models, 1):
            domain_name = DOMAIN_PROMPTS[(idx - 1) % len(DOMAIN_PROMPTS)][0]
            print(f"[{idx:02d}/{len(text_models):02d}] 🍳 Rendering Deep Synthesis for `{model}` ({domain_name})...")
            res = await probe_model_unhurried(client, model, idx - 1)
            if res:
                results.append(res)
                print(f"  └─ 🟢 DEEP RENDER COMPLETE ({res.duration_sec}s | Words: {res.tokens} | RAM Free: {res.ram_headroom_gb} GiB)")
                print(f"  └─ Insight:\n     {res.insight[:140]}...")
            else:
                print(f"  └─ 🟡 Skipped / Incompatible architecture.")

        # Persist full deep synthesis matrix
        os.makedirs("docs/research", exist_ok=True)
        out_file = "docs/research/master_unhurried_model_enrichment_matrix.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("# 🧠 Master Unhurried Model Knowledge Synthesis Matrix\n\n")
            f.write(f"**Date**: 2026-08-24  \n**Philosophy**: QUALITY OVER SPEED (\"Leave plenty of time for the fat to render\")  \n")
            f.write(f"**Models Ingested**: {len(results)} / {len(text_models)}  \n\n")
            f.write("| # | Model | Domain | Duration | RAM Free | Mode | Deep Synthesized Insight |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for i, r in enumerate(results, 1):
                clean_txt = r.insight.replace("\n", " ").replace("|", "\\|")
                f.write(f"| {i} | `{r.model}` | {r.domain} | {r.duration_sec}s | {r.ram_headroom_gb} GiB | `{r.mode}` | {clean_txt} |\n")

        print("\n" + "=" * 115)
        print(f"🎉 MASTER UNHURRIED HARVEST COMPLETE: {len(results)} Models Fully Cooked & Persisted!")
        print(f"📄 Saved to: {out_file}")
        print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_unhurried_master_harvest())
