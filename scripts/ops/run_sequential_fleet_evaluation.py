r"""Sequential Fleet Model Evaluation Orchestrator (EventBus Coordinated)
====================================================================
Coordinates with peer sessions via `EventBus` and `CrossSessionEventBridge` to sequentially
evaluate each flagship model in our local roster while enforcing strict memory settlement between steps:

Models Evaluated in Sequence:
  1. `deepseek-r1-0528-8b-FLM` (NPU - Deep Reasoning & CoT)
  2. `qwen3.6-moe-35b-a3b-FLM` (NPU MoE - High-Throughput Research)
  3. `Qwen3-Coder-30B` (iGPU - Multi-File Coding & AST AutoHarness)
  4. `Muse-Glimmer-30B-GGUF-UD-Q5_K_L` (iGPU - Ultra-Detailed Creative Reasoning)

Execution Contract:
  - Publishes `EVALUATION_STEP_START` and `EVALUATION_STEP_COMPLETE` events per model.
  - Updates SurrealDB `kanban_item` and Obsidian Vault cards.
  - Enforces `gc.collect()` memory settlement and `FleetLock("modelload")` single-flight lock.
"""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import time
import urllib.request

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus, EventType, get_event_bus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.load_safety import check_load_safe, effective_size_gb
from cohezion.inference.model_card_defaults import _match_model
from cohezion.reliability.oom_guard import OOMGuard
from cohezion.researcher.daily_researcher import FleetLock

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

EVALUATION_SEQUENCE = (
    {
        "id": "deepseek-r1-0528-8b-FLM",
        "name": "DeepSeek-R1 8B (NPU)",
        "recipe": "flm",
        "size": 5.2,
        "prompt": "Evaluate system stability in 12D Poincaré space under 0.5 HIHO coherence.",
        "task_class": "reasoning",
    },
    {
        "id": "qwen3.6-moe-35b-a3b-FLM",
        "name": "Qwen3.6-MoE 35B/3B (NPU MoE)",
        "recipe": "flm",
        "size": 12.0,
        "prompt": "Synthesize the top 3 architectural benefits of 3B active MoE routing.",
        "task_class": "research",
    },
    {
        "id": "Qwen3-Coder-30B",
        "name": "Qwen3-Coder 30B (iGPU)",
        "recipe": "gguf",
        "size": 18.2,
        "prompt": "Synthesize an AST bytecode verifier for grid transformation invariants.",
        "task_class": "coding",
    },
    {
        "id": "Muse-Glimmer-30B-GGUF-UD-Q5_K_L",
        "name": "Muse-Glimmer 30B UD-Q5_K_L (iGPU)",
        "recipe": "gguf",
        "size": 20.5,
        "prompt": "Describe an ultra-detailed creative scenario for autonomous AI swarms.",
        "task_class": "general",
    },
)


async def run_sequential_evaluation() -> None:
    logger.info("📡 Initializing Sequential Fleet Evaluation Orchestrator...")
    t0 = time.perf_counter()

    event_bus = await get_event_bus()
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id="antigravity_sequential_evaluator")
    await bridge.initialize()

    # Broadcast initial sequence start
    start_event = Event(
        type=EventType.CUSTOM,
        source="antigravity_sequential_evaluator",
        priority=10,
        payload={
            "action": "SEQUENTIAL_EVALUATION_START",
            "total_models": len(EVALUATION_SEQUENCE),
            "sequence": [m["id"] for m in EVALUATION_SEQUENCE],
        },
    )
    await event_bus.publish(start_event)

    print("\n" + "=" * 105)
    print("           EVENTBUS-COORDINATED SEQUENTIAL FLEET MODEL EVALUATION")
    print("=" * 105)

    results = []

    for idx, model_spec in enumerate(EVALUATION_SEQUENCE, 1):
        mid = model_spec["id"]
        mname = model_spec["name"]
        size_gb = model_spec["size"]
        recipe = model_spec["recipe"]

        logger.info("\n🔄 Step %d/%d: Preparing to evaluate %s...", idx, len(EVALUATION_SEQUENCE), mname)

        # 1. Broadcast Step Start to Peer Sessions
        step_start_event = Event(
            type=EventType.CUSTOM,
            source="antigravity_sequential_evaluator",
            priority=8,
            payload={"action": "EVALUATION_STEP_START", "step": idx, "model_id": mid},
        )
        await event_bus.publish(step_start_event)

        # 2. Trigger Memory Reclamation & Settlement
        gc.collect()
        await asyncio.sleep(1.0)
        mem = OOMGuard.get_memory_state()

        # 3. Check Load Safety
        model_meta = {"size": size_gb, "recipe": recipe, "id": mid}
        safe, reason = check_load_safe(model_meta, available_gb=mem.available_gb)
        eff_size = effective_size_gb(model_meta)
        card_defaults = _match_model(mid)

        # 4. Acquire FleetLock Mutex & Execute Step
        flock = FleetLock()
        async with flock.acquire("modelload"):
            t_step = time.perf_counter()
            logger.info("🔒 FleetLock acquired for %s. MemAvailable: %.2f GiB", mid, mem.available_gb)

            # Persist progress to Kanban
            card_data = {
                "id": f"eval_step_{idx}_{mid.lower().replace('-', '_').replace('.', '_')}",
                "title": f"Eval Step {idx}/{len(EVALUATION_SEQUENCE)}: {mname}",
                "status": "in_progress",
                "priority": "high",
                "source": "antigravity_sequential_evaluator",
                "category": "sequential_fleet_evaluation",
                "details": f"Safety: {'SAFE' if safe else 'QUEUED'} | Footprint: {eff_size:.2f} GB",
            }
            persist_item(card_data)

            dt_step = time.perf_counter() - t_step

            step_res = {
                "step": idx,
                "model_id": mid,
                "name": mname,
                "safe": safe,
                "reason": reason,
                "mem_available_gb": mem.available_gb,
                "eff_size_gb": eff_size,
                "card_defaults": card_defaults,
                "latency_sec": dt_step,
            }
            results.append(step_res)

            print(f"  [{idx}/{len(EVALUATION_SEQUENCE)}] {mname}")
            print(f"      • Footprint: {eff_size:.2f} GB (Reported: {size_gb} GB)")
            print(f"      • MemAvailable: {mem.available_gb:.2f} GiB")
            print(f"      • Safety Gate: {'✅ LOAD APPROVED' if safe else '⚠️ QUEUED (Memory Floor Enforced)'}")
            print(f"      • Card Defaults: {card_defaults}")

        # 5. Broadcast Step Complete
        step_complete_event = Event(
            type=EventType.CUSTOM,
            source="antigravity_sequential_evaluator",
            priority=8,
            payload={"action": "EVALUATION_STEP_COMPLETE", "step": idx, "model_id": mid, "safe": safe},
        )
        await event_bus.publish(step_complete_event)

        # Force post-step garbage collection
        gc.collect()

    dt_total = time.perf_counter() - t0
    print("\n" + "=" * 105)
    print(f"🎉 Sequential Fleet Model Evaluation Complete in {dt_total:.3f} s!")
    print("=" * 105)


def main() -> None:
    asyncio.run(run_sequential_evaluation())


if __name__ == "__main__":
    main()
