#!/usr/bin/env python3
import sys
import os
import asyncio
from pathlib import Path
import numpy as np

# Ensure path is set
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

# Escape hatch for local dev credentials
os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.flume.vacuum_encoder import encode_journey_text
from cohezion.flume.coe_evaluator import ChainOfEmbeddingEvaluator
from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry
from cohezion.core.persistence.surreal_client import SurrealClient, UniverseNode, PhysicsState


async def main():
    print("🚀 Initializing Dogfooding Experience Persistence Pipeline...")

    # 1. Define the 3 text payloads for this session's experiences

    # Experience 1: Production Dogfooding Cycle Execution
    exp1_prompt = "Execute the daily dogfooding cycle automation (daily_cycle.py)."
    exp1_response = """
    Ran DailyDogfoodingCycle successfully. Reviewed 8 levers (2 goals achieved, 4 priorities).
    Completed Auto-Improvement Cycle (parsed 3/5 lines, 60% baseline) and Phase Optimization Analysis.
    Saved results to ~/.config/cohezion/daily_cycles.jsonl.
    """

    # Experience 2: Verification of GAIA and HarnessPool Claims
    exp2_prompt = (
        "Verify local inference engine claims K, L, and M using claim_kl_pool_and_gaia.py."
    )
    exp2_response = """
    Executed local inference verification. Claim K (HarnessPool discovery: hermes, opencode, pi),
    Claim L (rank_models_by_amd_optimization sorting NPU < iGPU < CPU < Cloud),
    and Claim M (amd_optimized_hierarchy local-first orchestration) all passed successfully.
    """

    # Experience 3: Self-Healing System Checks
    exp3_prompt = "Execute the test suite to ensure workspace integrity and system status."
    exp3_response = """
    Ran the fast unit tests (make test-fast). Verified systemd stale path diagnostics, patch rollbacks,
    and connection repair paths. All 1,157 tests passed cleanly with no regressions.
    """

    print("🔮 Encoding payloads using FLUME Vacuum Domain Encoder (VDE)...")
    z1 = await encode_journey_text(exp1_prompt, exp1_response)
    z2 = await encode_journey_text(exp2_prompt, exp2_response)
    z3 = await encode_journey_text(exp3_prompt, exp3_response)
    print("✓ Encoding complete. Got three 256D latent vectors.")

    # 2. Score sequential trajectory via VDE CoE (Chain-of-Embedding) Evaluator
    print("📈 Evaluating trajectory geometry using Chain-of-Embedding (CoE)...")
    evaluator = ChainOfEmbeddingEvaluator()
    coe_result = evaluator.score_from_embeddings([np.array(z1), np.array(z2), np.array(z3)])
    print(
        f"✓ CoE Evaluation complete. Score: {coe_result['coe_score']} (M={coe_result['m_score']:.4f}, A={coe_result['a_score']:.4f})"
    )

    # 3. Ingest into MyceliumRegistry and run audit
    print("🍄 Ingesting experiences into MyceliumRegistry...")
    registry = MyceliumRegistry(min_entries_for_pattern=2)

    entry1 = JournalEntry(
        entry_id="dogfood_daily_cycle_20260604",
        content=f"Daily dogfood cycle results: {exp1_response.strip()}",
        domain="experiment",
    )
    entry2 = JournalEntry(
        entry_id="dogfood_claims_verification_20260604",
        content=f"Dogfood claims results: {exp2_response.strip()}",
        domain="pattern",
    )
    entry3 = JournalEntry(
        entry_id="dogfood_self_healing_tests_20260604",
        content=f"Self healing tests results: {exp3_response.strip()}",
        domain="experiment",
    )

    registry.ingest_entry(entry1)
    registry.ingest_entry(entry2)
    registry.ingest_entry(entry3)

    audit_report = registry.run_audit()
    print(
        f"✓ Mycelium Audit run: Scanned {audit_report.entries_scanned} entries, synthesized {audit_report.skills_synthesized} skills."
    )

    # 4. Save everything to SurrealDB
    print("💾 Connecting to SurrealDB to persist Akashic records...")
    db = SurrealClient()
    await db.connect()
    await db.setup_schema()

    # Store experience 1
    node1 = UniverseNode(
        id="experience_dogfood_daily_20260604",
        content=exp1_response,
        embedding=z1,
        node_type="experience",
        physics_state=PhysicsState(logic=0.9, control=0.95, novelty=0.8, z=0.5),
        metadata={"prompt": exp1_prompt, "date": "2026-06-04", "z_vector": z1},
    )
    await db.store_node(node1)

    # Store experience 2
    node2 = UniverseNode(
        id="experience_dogfood_claims_20260604",
        content=exp2_response,
        embedding=z2,
        node_type="experience",
        physics_state=PhysicsState(control=0.9, logic=0.9, precipitation=0.9, x=0.5),
        metadata={"prompt": exp2_prompt, "date": "2026-06-04", "z_vector": z2},
    )
    await db.store_node(node2)

    # Store experience 3
    node3 = UniverseNode(
        id="experience_dogfood_tests_20260604",
        content=exp3_response,
        embedding=z3,
        node_type="experience",
        physics_state=PhysicsState(logic=0.95, novelty=0.8, field=0.95, y=0.5),
        metadata={"prompt": exp3_prompt, "date": "2026-06-04", "z_vector": z3},
    )
    await db.store_node(node3)

    # Store CoE trajectory
    node4 = UniverseNode(
        id="coe_trajectory_dogfood_20260604",
        content="CoE evaluation of dogfooding trajectory: daily_cycle -> claims_verification -> self_healing_tests",
        node_type="coe_evaluation",
        physics_state=PhysicsState(control=0.95, logic=0.95, field=0.9),
        metadata={
            "coe_result": coe_result,
            "trajectory_ids": [
                "experience_dogfood_daily_20260604",
                "experience_dogfood_claims_20260604",
                "experience_dogfood_tests_20260604",
            ],
            "date": "2026-06-04",
        },
    )
    await db.store_node(node4)
    print(f"  ✓ Saved CoE Trajectory to SurrealDB with score {coe_result['coe_score']}")

    await db.close()
    print("✓ SurrealDB persistence complete.")

    # 5. Write pages to Obsidian vault
    vault_dir = Path("/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault")
    print(f"📝 Writing Markdown files to Obsidian vault at {vault_dir}...")

    # File 1: Experiments (Daily Cycle Execution)
    file1_path = vault_dir / "experiments" / "2026-06-04-dogfood-daily-cycle.md"
    file1_content = """---
date: 2026-06-04
project: cohezion
status: completed
outcome: success
tags: [experiment, dogfood, daily-cycle, automation]
---
# Production Daily Dogfood Cycle Execution

## Hypothesis
Executing `daily_cycle.py` will autonomously process dashboard reviews, run predictive adjustments, execute parser auto-improvements, and evaluate phase optimizations.

## Results
- Reviewed 8 levers. Goals achieved: 2/8. Identified 4 priorities (top: `validation_sample_size`).
- Auto-improvement cycle parsed 3/5 lines (60.0% accuracy).
- Logging completed successfully to `~/.config/cohezion/daily_cycles.jsonl`.
"""
    file1_path.parent.mkdir(parents=True, exist_ok=True)
    file1_path.write_text(file1_content)
    print(f"  ✓ Wrote: {file1_path.name}")

    # File 2: Experiments (GAIA and HarnessPool Claims)
    file2_path = vault_dir / "experiments" / "2026-06-04-dogfood-claims-verification.md"
    file2_content = """---
date: 2026-06-04
project: cohezion
status: completed
outcome: success
tags: [experiment, dogfood, claims-verification, gaia]
---
# GAIA and HarnessPool Claims Dogfooding Verification

## Hypothesis
Executing `claim_kl_pool_and_gaia.py` will successfully verify deterministic local inference engine and adapter claims without raising errors.

## Results
- **Claim K**: HarnessPool successfully discovered installed harnesses on PATH (`hermes`, `opencode`, `pi`).
- **Claim L**: `rank_models_by_amd_optimization` correctly sorted model lists (NPU < iGPU < CPU < Cloud).
- **Claim M**: `amd_optimized_hierarchy` built a 4-tier local orchestrator with NPU Gemma-4-E2B-it-GGUF as the first tier.
- All verification steps passed successfully.
"""
    file2_path.parent.mkdir(parents=True, exist_ok=True)
    file2_path.write_text(file2_content)
    print(f"  ✓ Wrote: {file2_path.name}")

    # File 3: Daily logs
    file3_path = vault_dir / "daily" / "2026-06-04-dogfooding-diary.md"
    file3_content = """---
date: 2026-06-04
tags: [daily, diary, dogfood]
---
# Dogfooding Diary: 2026-06-04

We completed comprehensive verification of the GAIA and Lemonade local inference engine and the daily automated dogfooding cycle.

- Executed the daily automated dogfooding cycle (`daily_cycle.py`) and recorded execution metrics.
- Verified local inference claims (K, L, and M) validating our routing logic and pool configuration.
- Successfully looped experiences through the FLUME VAE and persisted them in SurrealDB (port 8001).
- All 1,157 regression tests passing cleanly.
"""
    file3_path.parent.mkdir(parents=True, exist_ok=True)
    file3_path.write_text(file3_content)
    print(f"  ✓ Wrote: {file3_path.name}")

    print("🎉 All logging and persistence tasks completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
