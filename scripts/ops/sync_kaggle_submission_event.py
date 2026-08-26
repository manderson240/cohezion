#!/usr/bin/env python3
"""Publish Kaggle Kernel Submission Event to EventBus & Dual-Persist to SurrealDB / Obsidian."""

import asyncio
import os

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item

async def main():
    event_bus = await get_event_bus()
    session_id = "kaggle_pokemon_submission_session"
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id=session_id)
    await bridge.initialize()

    ev = Event(
        type=EventType.CUSTOM,
        source="kaggle_grandmaster_engine",
        priority=10,
        payload={
            "competition": "pokemon-tcg-ai-battle-challenge-strategy",
            "kernel_slug": "manderson240/cohezion-ismcts-cfr-pokemon-tcg",
            "status": "KernelWorkerStatus.COMPLETE",
            "decision_latency_ms": 0.56,
            "architecture": "Pure Python ISMCTS + Online Outcome Sampling CFR"
        }
    )
    await event_bus.publish(ev)

    persist_item({
        "id": "kaggle_pokemon_tcg_kernel_deployed",
        "title": "Kaggle Pokémon TCG Strategy Agent Deployed & Executed",
        "status": "done",
        "priority": "highest",
        "source": "kaggle_grandmaster_engine",
        "category": "kaggle_competitions",
        "details": "Pushed and successfully ran manderson240/cohezion-ismcts-cfr-pokemon-tcg on Kaggle (KernelWorkerStatus.COMPLETE, 0.56ms latency).",
    })
    print("✓ Dual-persisted Kaggle submission card to SurrealDB and Obsidian Vault!")

if __name__ == "__main__":
    asyncio.run(main())
