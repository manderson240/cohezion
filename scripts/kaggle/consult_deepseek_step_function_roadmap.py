#!/usr/bin/env python3
"""Consult deepseek-v4-pro:cloud on Ollama port 11434 with 2048D Poincaré AutoContext.

Formulates a bleeding-edge, step-function improvement roadmap across our 4 active,
unexpired competitions focused on 100% individual solo payouts ($S=1.0$):
1. ARC-AGI-2 ($700k): Neuro-Symbolic DSL Program Synthesis & TTT on D4 demos.
2. ARC-AGI-3 ($850k): Go-Explore archive & Macro-action compilation on unlimited CPU.
3. RSNA Knee Detection ($77k): 3D Cross-Planar Attention & Ledoit-Wolf calibration.
4. Enveda CASMI26 ($50k): Precursor formula gating (<5 ppm) & in-silico bond cleavage.

Persists to:
- docs/research/step_function_kaggle_breakthrough_roadmap.md
- SurrealDB learning:step_function_kaggle_roadmap
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.agents.ollama_cloud_agent import (
    AutoContextState,
    OllamaCloudAgent,
    OllamaCloudModel,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] %(message)s",
)
logger = logging.getLogger("step_function_consultant")


def persist_to_surrealdb_learning(key: str, data: dict) -> bool:
    """Persist learning record to SurrealDB on port 8001 or 8000."""
    endpoints = ["http://localhost:8001/sql", "http://127.0.0.1:8001/sql", "http://localhost:8000/sql"]
    auth = base64.b64encode(b"root:root").decode()

    # Quote key safely
    safe_key = key.replace(":", "_").replace("-", "_")
    surql = f"UPSERT learning:`{safe_key}` CONTENT {json.dumps(data)};"

    for ep in endpoints:
        try:
            req = urllib.request.Request(
                ep,
                data=surql.encode("utf-8"),
                headers={
                    "surreal-ns": "cohezion",
                    "surreal-db": "main",
                    "Content-Type": "text/plain",
                    "Authorization": f"Basic {auth}",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                body = resp.read().decode("utf-8")
                logger.info("SurrealDB persistence succeeded at %s: %s", ep, body[:120])
                return True
        except Exception as exc:
            logger.debug("SurrealDB at %s failed: %s", ep, exc)

    logger.warning("SurrealDB not reachable on standard ports; continuing gracefully.")
    return False


async def consult_deepseek() -> str:
    agent = OllamaCloudAgent(
        name="deepseek_strategic_architect",
        role="Grandmaster Kaggle Strategic Synthesis Specialist",
        model=OllamaCloudModel.DEEPSEEK_V4_PRO,
        system_prompt=(
            "You are the Grandmaster Kaggle Strategic Synthesis Specialist and Principal AI Architect for Cohezion.\n"
            "Your mandate is to engineer a transformative, step-function improvement roadmap across our 4 active, unexpired Kaggle competitions.\n"
            "All strategies are strictly optimized for 100% individual solo payouts ($S=1.0, solo competitor Mike Anderson / manderson240).\n\n"
            "Provide rigorous mathematical formulations, concrete architectural blueprints, and production-grade, typed Python code blocks.\n"
            "Adhere strictly to AutoHarness deterministic invariants: zero eval(), zero exec(), explicit return typing, and fully verifiable logic."
        ),
        base_url="http://localhost:11434",
    )

    goal = (
        "Formulate the definitive, step-function breakthrough roadmap across our 4 active, unexpired Kaggle competitions:\n\n"
        "1. ARC-AGI-2 ($700k pool, current 31.81%, Top 10 cutoff 33.89%, Gap +2.08% = 2-3 puzzles):\n"
        "   - Paradigm shift from static token/grid generation to Neuro-Symbolic DSL Program Synthesis: synthesizing executable, sandboxed Python AST functions verified on demonstration pairs.\n"
        "   - Test-Time Training (TTT) gradient adaptation: single-task meta-learning adapting the backbone weights on the D4 dihedral augmented demo pairs with low-rank update.\n"
        "   - Provide concrete typed Python implementation for the DSL synthesizer harness and TTT adaptation loop.\n\n"
        "2. ARC-AGI-3 Interactive ($850k pool, scored 0.25 on Kaggle CPU, Rank 1 is 19.45%):\n"
        "   - Full Go-Explore state archive architecture leveraging Kaggle's UNLIMITED CPU compute quota.\n"
        "   - Affordance frontier branching: cells with novel interactive delta signatures, non-reversible actions, and inventory changes.\n"
        "   - Macro-action compilation: BFS/A* pathfinding directly to affordance targets, compressing 40-step blind wandering into 1 atomic decision step.\n"
        "   - Provide concrete typed Python implementation of the Go-Explore Archive and Macro-Action BFS Compiler.\n\n"
        "3. RSNA Knee Detection ($77k pool, current 0.940-0.943, Podium 0.957, Gap +0.014):\n"
        "   - 3D Cross-Planar Attention: tri-planar joint feature fusion across Sagittal x Coronal x Axial views.\n"
        "   - Ledoit-Wolf empirical shrinkage covariance calibration: optimal shrinkage lambda* for cross-finding correlation matrices to eliminate calibration drift.\n"
        "   - Provide concrete typed PyTorch/NumPy implementation of 3D Cross-Planar Attention and Ledoit-Wolf shrinkage calibration.\n\n"
        "4. Enveda CASMI26 ($50k pool, current 0.328, Top 10 is 0.383, Rank 1 is 0.425):\n"
        "   - High-resolution precursor formula gating with strict <5.0 ppm mass tolerance filtering candidates before embedding ranking.\n"
        "   - In-silico bond cleavage matching: heuristic fragmentation matching between MS/MS peaks and candidate SMILES substructures.\n"
        "   - Provide concrete typed Python implementation for ppm gating and in-silico fragmentation scoring.\n\n"
        "Ensure all code is completely valid, syntactically clean, robust, and mathematically sound."
    )

    logger.info("Starting consultation with deepseek-v4-pro:cloud (timeout=450s)...")
    res = await agent.execute_turn(goal=goal, timeout_seconds=450.0)

    logger.info("Consultation completed! Latency: %.2f ms | Verified: %s | Conformal factor: %.4f",
                res.total_latency_ms, res.autoharness_verified, res.autocontext_conformal_factor)
    if res.thinking:
        logger.info("Thinking trace length: %d chars", len(res.thinking))

    return res.response


async def main() -> None:
    t0 = time.time()
    response = await consult_deepseek()
    elapsed = time.time() - t0

    # Persist raw response to temporary inspection file
    out_dir = REPO_ROOT / "docs" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    consultation_log = out_dir / "deepseek_v4_pro_consultation_raw.md"
    consultation_log.write_text(response, encoding="utf-8")
    logger.info("Wrote raw consultation to %s", consultation_log)


if __name__ == "__main__":
    asyncio.run(main())
