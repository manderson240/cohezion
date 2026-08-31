r"""Cross-Session Resource Reservation & Model Evaluation Orchestrator
====================================================================
Coordinates system resources across active sessions via `EventBus` and `CrossSessionEventBridge`:
  1. Broadcasts high-priority `RESOURCE_RESERVATION_REQUEST` to EventBus & SurrealDB `event_log`.
  2. Persists Kanban card to SurrealDB (`kanban_item`) and Obsidian Vault (`kanban/`).
  3. Triggers memory settlement and garbage collection.
  4. Acquires `FleetLock("modelload")` mutex and re-evaluates `Muse-Glimmer-30B-GGUF-UD-Q5_K_L`.
"""

from __future__ import annotations

import asyncio
import gc
import logging

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.load_safety import check_load_safe, effective_size_gb
from cohezion.inference.model_card_defaults import _match_model
from cohezion.reliability.oom_guard import OOMGuard
from cohezion.researcher.daily_researcher import FleetLock


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MODEL_ID = "Muse-Glimmer-30B-GGUF-UD-Q5_K_L"
REPORTED_SIZE_GB = 20.5


async def run_coordination_and_eval() -> None:
    logger.info(
        "📡 Step 1: Broadcasting Cross-Session Resource Reservation Request via EventBus..."
    )
    event_bus = await get_event_bus()
    bridge = CrossSessionEventBridge(
        event_bus=event_bus, session_id="antigravity_master_orchestrator"
    )
    await bridge.initialize()

    req_event = Event(
        type=EventType.CUSTOM,
        source="antigravity_master_orchestrator",
        priority=10,  # High priority
        payload={
            "action": "RESOURCE_RESERVATION_REQUEST",
            "target_model": MODEL_ID,
            "required_ram_gb": 35.0,
            "reason": "Exclusive model evaluation of Muse-Glimmer-30B GGUF",
        },
    )
    await event_bus.publish(req_event)
    logger.info(
        "✅ Published high-priority resource reservation request to local EventBus & SurrealDB event_log"
    )

    # Step 2: Persist Agentic Kanban Card across SurrealDB & Obsidian
    logger.info("📋 Step 2: Persisting Agentic Kanban Card to SurrealDB & Obsidian Vault...")
    card_data = {
        "id": "res_reservation_muse_glimmer_30b",
        "title": f"Resource Reservation: Evaluate {MODEL_ID}",
        "status": "in_progress",
        "priority": "high",
        "source": "antigravity_master_orchestrator",
        "category": "resource_coordination",
        "details": f"Reserving 35.0 GiB RAM for {MODEL_ID} evaluation.",
    }
    kanban_res = persist_item(card_data)
    logger.info("✅ Kanban Card Persisted: %s", kanban_res)

    # Step 3: Trigger Memory Settlement & Garbage Collection
    logger.info("🧹 Step 3: Triggering Memory Reclamation & Settlement...")
    gc.collect()
    await asyncio.sleep(1.0)
    mem_after = OOMGuard.get_memory_state()
    logger.info("📡 Post-Settlement Memory State: %.2f GiB available", mem_after.available_gb)

    # Step 4: Re-evaluate Muse-Glimmer-30B under FleetLock Mutex
    logger.info("🔒 Step 4: Acquiring FleetLock('modelload') for Model Evaluation...")
    flock = FleetLock()
    async with flock.acquire("modelload"):
        model_meta = {"size": REPORTED_SIZE_GB, "recipe": "gguf", "id": MODEL_ID}
        eff_size = effective_size_gb(model_meta)
        safe, reason = check_load_safe(model_meta, available_gb=mem_after.available_gb)

        card_defaults = _match_model(MODEL_ID)

        print("\n" + "=" * 90)
        print(f"      COORDINATED CROSS-SESSION MODEL EVALUATION: {MODEL_ID}")
        print("=" * 90)
        print("  • EventBus Resource Request: BROADCASTED & PERSISTED")
        print(f"  • Kanban Card State: {kanban_res}")
        print(f"  • Live Available RAM (Post-Settlement): {mem_after.available_gb:.2f} GiB")
        print(f"  • Required Model Footprint (1.7x Factor): {eff_size:.2f} GB")
        print(
            f"  • Model Load Safety Gate: {'✅ LOAD APPROVED FOR EVALUATION' if safe else '⚠️ LOAD HELD IN QUEUE'}"
        )
        print(f"    Reason: {reason}")
        print(f"  • Model Card Sampling Sweet-Spot: {card_defaults}")
        print("  • Evaluation Strategy: Sequential single-flight load under FleetLock mutex")
        print("=" * 90)
        print("🎉 Cross-Session Resource Coordination & Evaluation Complete!")


def main() -> None:
    asyncio.run(run_coordination_and_eval())


if __name__ == "__main__":
    main()
