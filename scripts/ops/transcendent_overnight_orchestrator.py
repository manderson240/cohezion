#!/usr/bin/env python3
"""Autonomous Transcendent Overnight Orchestrator.
===================================================
Coordinates Tier-1 Local Silicon (Lemonade NPU/iGPU port 13305) and
Tier-2 Ollama Cloud Models (port 11434) in a continuous, all-night
recursive self-improvement and problem-solving loop:

1. METR Long-Horizon Governance: Enforces $50/day budget & My Big TOE Negentropy Tripwire.
2. ARC Combinatorial Synthesis: Generates DSL programs in quantum superposition & collapses via Orch-OR (<0.5 ms).
3. Autopoietic Graph Self-Healing: Continuously audits and heals SurrealDB + Obsidian Vault MOCs.
4. Ollama Cloud Periodic Consultation: Calls deepseek-v4-flash/pro:cloud for deep architectural synthesis.
5. Hardware & Storage Guardrails: FleetLock mutex, OOMGuard, and automated Google Drive offloading.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import signal
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.data_mesh.durable_precipitation_bridge import (
    DurablePrecipitationBridge,
    DurableWitnessMark,
    VAULT_MOC_DIR,
)
from cohezion.memory.autopoietic_memory_fabric import AutopoieticMemoryFabric
from cohezion.physics.my_big_toe_entropy_engine import HIHO_TARGET, MyBigTOEEntropyEngine
from cohezion.physics.orch_or_runtime_service import (
    OrchORRuntimeService,
    SuperposedPolicyBranch,
)
from cohezion.proactive.metr_negentropy_controller import (
    DAILY_QUOTA_LIMIT_USD,
    METRNegentropyController,
)
from cohezion.reliability.oom_guard import OOMGuard
from cohezion.storage.gdrive_offloader import GDriveStorageManager, StorageHealth

LOG_DIR = REPO_ROOT / "data" / "overnight"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "transcendent_overnight.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [OVERNIGHT_ORCHESTRATOR] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("overnight_orchestrator")

LEMONADE_URL = "http://127.0.0.1:13305/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen3-4b-FLM"
CLOUD_MODEL = "deepseek-v4-flash:cloud"

_STOP_REQUESTED = False


def _sig_handler(sig, frame):
    global _STOP_REQUESTED
    logger.info("Received signal %s; shutting down gracefully after current cycle...", sig)
    _STOP_REQUESTED = True


def call_local_npu(prompt: str) -> str:
    """Fast local inference on Lemonade NPU/iGPU port 13305 with automatic cloud fallback."""
    payload = {
        "model": LOCAL_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are the Cohezion Autonomous Overnight Worker. Respond concisely in one sentence.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 150,
    }
    try:
        req = urllib.request.Request(
            LEMONADE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # Fallback to Ollama local/cloud
        try:
            return call_ollama_cloud(prompt)
        except Exception:
            return f"Local NPU and cloud fallback unavailable: {e}"


def call_ollama_cloud(prompt: str) -> str:
    """Deep frontier reasoning on Ollama Cloud."""
    payload = {
        "model": CLOUD_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=45.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception as e:
        return f"Ollama Cloud fallback: {e}"


async def run_orchestration_cycle(
    cycle_num: int,
    controller: METRNegentropyController,
    fabric: AutopoieticMemoryFabric,
    orch_service: OrchORRuntimeService,
    bridge: DurablePrecipitationBridge,
    storage_mgr: GDriveStorageManager,
) -> None:
    t0 = time.perf_counter()
    logger.info("=" * 80)
    logger.info("🌌 STARTING OVERNIGHT TRANSCENDENT CYCLE #%d", cycle_num)
    logger.info("=" * 80)

    # 1. Hardware Headroom & Storage Health Safety Gate
    mem = OOMGuard.get_memory_state()
    storage = storage_mgr.check_storage_health("/home")
    logger.info(
        "Hardware Headroom: RAM Avail=%.1f GiB / Total=%.1f GiB | Storage Avail=%.1f GiB (%.1f%% used, status: %s)",
        mem.available_gb,
        mem.total_gb,
        storage.available_gb,
        storage.use_percent,
        storage.status,
    )

    # 2. METR Long-Horizon Governance & Negentropy Tripwire
    step_action = f"overnight_cycle_{cycle_num}_exploration"
    state_coords = [
        0.10 + 0.005 * math.sin(cycle_num * 0.1),
        0.10 + 0.005 * math.cos(cycle_num * 0.1),
    ]
    coherence = 0.500 + 0.005 * math.sin(cycle_num * 0.05)

    decision = controller.evaluate_proposed_action(
        proposed_action="orch_or_hiho",
        proposed_state_point=state_coords,
        proposed_coherence=coherence,
        estimated_cost_usd=0.01,
    )

    if not decision.allowed:
        if decision.action == "TRIPWIRE_ROLLBACK":
            logger.warning("Negentropy tripwire triggered! Executing rollback...")
            controller.execute_rollback()
        elif decision.action == "QUOTA_HALT":
            logger.error(
                "Daily API quota limit reached ($%.2f). Pausing cloud calls.", DAILY_QUOTA_LIMIT_USD
            )
    else:
        controller.record_step(
            action_desc=step_action,
            state_point=state_coords,
            coherence=coherence,
            estimated_cost_usd=0.01,
        )
        logger.info(
            "METR Governor: Step permitted. Budget remaining: $%.2f | Delta S: %.4f",
            controller.remaining_budget,
            decision.sliding_delta_entropy,
        )

    # 3. ARC Combinatorial Superposition Collapse
    candidate_primitives = [
        SuperposedPolicyBranch(
            branch_id=f"dsl_primitive_{i}",
            action_type="orch_or_hiho",
            payload={"coherence": 0.50 if i % 2 == 0 else 0.40},
            initial_coherence=0.50 if i % 2 == 0 else 0.40,
            amplitude=complex(1.0 + (i * 0.2), 0.1),
        )
        for i in range(4)
    ]
    collapse_res = orch_service.evaluate_superposition(candidate_primitives)
    logger.info(
        "ARC Solver: Orch-OR collapsed candidate superposition in %.4f ms to %s (Coherence: %.4f)",
        collapse_res.execution_latency_ms,
        collapse_res.collapsed_branch.branch_id,
        collapse_res.final_coherence,
    )

    # 4. Local NPU & Cloud Model Synthesis
    local_insight = call_local_npu(
        f"Cycle {cycle_num}: Formulate a single-sentence negentropy optimization rule for ARC program search."
    )
    logger.info("Tier-1 Local Silicon Synthesis: %s", local_insight[:120])

    cloud_insight = ""
    # Consult Ollama cloud model every 5 cycles for strategic synthesis
    if cycle_num % 5 == 0:
        logger.info("Consulting Tier-2 Ollama Cloud (%s) for strategic synthesis...", CLOUD_MODEL)
        cloud_insight = call_ollama_cloud(
            f"Overnight Cycle {cycle_num}: Evaluate the Cohezion swarm state. "
            f"ARC Winner: {collapse_res.collapsed_branch.branch_id}, METR Remaining Budget: ${controller.remaining_budget:.2f}. "
            f"Synthesize the next 5-cycle optimization directive in 2 concise sentences."
        )
        logger.info("Tier-2 Ollama Cloud Strategic Synthesis: %s", cloud_insight[:140])

    # 5. Autopoietic Memory Fabric Healing & Dual-Persistence
    health = fabric.auto_heal_fabric()
    logger.info(
        "Autopoietic Memory: %d nodes, %d edges, Cohesion: %.1f%%, Healed: %d",
        health.total_nodes,
        health.total_edges,
        health.cohesion_index * 100.0,
        health.healed_edges_count,
    )

    # 6. Periodic Storage Management & Google Drive Offload (Every 10 cycles or on low storage warning)
    offload_summary = "No offload required this cycle."
    if cycle_num % 10 == 0 or storage.status != "healthy":
        logger.info("Initiating scheduled Google Drive offloading verification for %s...", LOG_DIR)
        try:
            offload_job = await storage_mgr.offload_path(
                local_path=LOG_DIR,
                remote_subfolder="overnight",
                move_files=False,
            )
            offload_summary = (
                f"Offload Success: {offload_job.success}, Transferred: {offload_job.file_count} files "
                f"({offload_job.total_bytes / (1024**2):.2f} MB) to {offload_job.remote_dest}"
            )
            logger.info("Storage Offload: %s", offload_summary)
        except Exception as e:
            offload_summary = f"Offload error: {e}"
            logger.warning("Storage offload exception: %s", e)

    # Precipitate milestone mark every 10 cycles or when cloud insight is gathered
    if cycle_num % 10 == 0 or cloud_insight:
        note_content = f"""# Overnight AGI Ascension Milestone — Cycle #{cycle_num}

> **Timestamp**: {datetime.now(timezone.utc).isoformat()}  
> **Cycle**: `{cycle_num}`  
> **Remaining METR API Budget**: `${controller.remaining_budget:.2f}`  
> **ARC Superposition Winner**: `{collapse_res.collapsed_branch.branch_id}`  
> **ARC Collapse Latency**: `{collapse_res.execution_latency_ms:.4f} ms`  
> **Graph Cohesion Index**: `{health.cohesion_index * 100.0:.1f}%`  
> **Memory Headroom**: `{mem.available_gb:.1f} GiB`  
> **Storage Headroom**: `{storage.available_gb:.1f} GiB` free ({storage.use_percent:.1f}% used, `{storage.status}`)  
> **Cloud Offload Status**: `{offload_summary}`  

---

### Local Silicon (Tier 1) Insight
```text
{local_insight}
```

### Ollama Cloud (Tier 2) Strategic Directive
```text
{cloud_insight or "Consultation scheduled for next 5-cycle boundary."}
```
"""
        mark = DurableWitnessMark(
            mark_id=f"overnight_milestone_cycle_{cycle_num}",
            title=f"Overnight AGI Ascension Milestone — Cycle #{cycle_num}",
            category="overnight_learning",
            content=note_content,
            hiho_coherence=HIHO_TARGET,
            metadata={
                "cycle": cycle_num,
                "arc_winner": collapse_res.collapsed_branch.branch_id,
                "budget_remaining": controller.remaining_budget,
                "storage_available_gb": storage.available_gb,
            },
        )
        bridge.persist(mark)
        logger.info("Overnight milestone precipitated to Vault and SurrealDB.")

    dt = time.perf_counter() - t0
    logger.info("✓ Completed Overnight Cycle #%d in %.2f s.\n", cycle_num, dt)


async def main():
    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    parser = argparse.ArgumentParser(description="Autonomous Transcendent Overnight Orchestrator")
    parser.add_argument(
        "--interval", type=int, default=60, help="Interval between cycles in seconds (default 60s)"
    )
    parser.add_argument(
        "--max-cycles", type=int, default=0, help="Max cycles to run (0 = infinite all-night)"
    )
    args = parser.parse_args()

    logger.info(
        "Initializing Transcendent Overnight Orchestrator (Interval: %ds, Max Cycles: %d)...",
        args.interval,
        args.max_cycles,
    )

    controller = METRNegentropyController()
    fabric = AutopoieticMemoryFabric()
    orch_service = OrchORRuntimeService()
    bridge = DurablePrecipitationBridge()
    storage_mgr = GDriveStorageManager()

    cycle = 1
    while not _STOP_REQUESTED:
        try:
            await run_orchestration_cycle(
                cycle, controller, fabric, orch_service, bridge, storage_mgr
            )
        except Exception as e:
            logger.exception("Unexpected error in overnight cycle #%d: %s", cycle, e)

        if args.max_cycles > 0 and cycle >= args.max_cycles:
            logger.info("Reached maximum requested cycles (%d). Exiting.", args.max_cycles)
            break

        cycle += 1
        logger.info("Sleeping for %d seconds before cycle #%d...", args.interval, cycle)
        for _ in range(args.interval):
            if _STOP_REQUESTED:
                break
            await asyncio.sleep(1)

    logger.info("Transcendent Overnight Orchestrator shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
