#!/usr/bin/env python3
"""Sequential Multi-Model Knowledge Harvest & Enrichment Demo.

Cycles through multiple specialized local models sequentially:
1. `DeepSeek-Qwen3-8B-GGUF` -> Sheaf Cohomology & Categorical Swarm Topology.
2. `Gemma-4-E4B-it-GGUF` -> Ken Shoulders EVOs & Micro-Borehole Plasma Dynamics.
3. `gpt-oss-20b-mxfp4-GGUF` -> Zero-Cost AST AutoHarness Invariants & ZKFV.
"""

import asyncio
import logging
import os
import time

from cohezion.compound.sequential_model_enricher import SequentialModelEnricher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ENRICHER] %(message)s")
logger = logging.getLogger("demo_enricher")

HARVEST_TASKS = [
    (
        "DeepSeek-Qwen3-8B-GGUF",
        "Sheaf Cohomology & Topology",
        "Formulate how 0-th Cech cohomology Laplacians eliminate semantic consensus drift across distributed agent swarms in 2 dense mathematical sentences."
    ),
    (
        "Gemma-4-E4B-it-GGUF",
        "Ken Shoulders EVOs & Plasma Physics",
        "Explain how Ken Shoulders 1.0 um Toroidal Exotic Vacuum Objects achieve charge stabilization via Bohr-Coulomb dielectric shielding in 2 dense sentences."
    ),
    (
        "gpt-oss-20b-mxfp4-GGUF",
        "AutoHarness & Formal Verifiers",
        "State why zero-cost AST bytecode compilers bypass LLM inference calls with 0.00 ms latency during agentic action verification in 2 concise sentences."
    )
]

async def run_sequential_harvest():
    enricher = SequentialModelEnricher()
    print("\n" + "=" * 105)
    print("🎡 SEQUENTIAL MULTI-MODEL KNOWLEDGE HARVEST & ENRICHMENT CAROUSEL")
    print("=" * 105)

    for idx, (model, domain, prompt) in enumerate(HARVEST_TASKS, 1):
        print(f"\n[{idx}/3] Harvesting Knowledge from `{model}` for Domain: '{domain}'...")
        res = await enricher.enrich_from_model(model, domain, prompt, max_tokens=256)
        if res:
            print(f"  • Duration: {res.duration_sec}s | Words: {res.tokens_generated}")
            print(f"  • Synthesized Insight:\n    {res.synthesized_insight}")
        else:
            print(f"  ⚠️ Harvest skipped or failed for {model}")

    print("\n" + "=" * 105)
    print(f"🎉 SEQUENTIAL ENRICHMENT HARVEST COMPLETED ({len(enricher.insights)} Insights Ingested)!")
    print("=" * 105 + "\n")

    # Persist summary
    os.makedirs("docs/research", exist_ok=True)
    summary_path = "docs/research/sequential_model_enrichment_harvest.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# 🎡 Sequential Model Knowledge Enrichment Harvest\n\n")
        f.write(f"**Date**: 2026-08-24\n**Total Insights Harvested**: {len(enricher.insights)}\n\n")
        for ins in enricher.insights:
            f.write(f"### Model: `{ins.model_name}` | Domain: `{ins.domain}`\n")
            f.write(f"- **Prompt**: {ins.prompt}\n")
            f.write(f"- **Synthesis** ({ins.duration_sec}s):\n\n> {ins.synthesized_insight}\n\n---\n\n")
    logger.info("Saved enrichment harvest report to %s", summary_path)

if __name__ == "__main__":
    asyncio.run(run_sequential_harvest())
