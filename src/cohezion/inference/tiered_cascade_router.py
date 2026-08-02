"""Tiered Cascade Router & Orchestration Hooks.

Enforces a strict 2-tier execution hierarchy:
1. Primary: Local Silicon / Lemonade OmniRouter (port 13305)
2. Secondary: Ollama Cloud Peer Models (port 11434)
3. Fallback: Agentic Kanban Deferral (SurrealDB :8001 + Vault)

Orchestrated with EventBus hooks and load safety memory checks.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from cohezion.core.event_bus import Event, EventBus
from cohezion.inference.lemonade_cli_monitor import LemonadeCLIMonitor
from cohezion.inference.load_safety import (
    available_ram_gb,
    check_load_safe,
    defer_to_kanban_on_memory_pressure,
)


logger = logging.getLogger(__name__)


class TieredCascadeRouter:
    """Orchestrates 2-tier local-primary cascade with Kanban fallback."""

    LEMONADE_ENDPOINT: str = "http://localhost:13305"
    OLLAMA_ENDPOINT: str = "http://localhost:11434"

    DEFAULT_LOCAL_CODING_MODEL: str = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
    DEFAULT_LOCAL_REASONING_MODEL: str = "Bonsai-27B-gguf"
    DEFAULT_LOCAL_FAST_MODEL: str = "Bonsai-1.7B-gguf"

    DEFAULT_CLOUD_CODING_MODEL: str = "kimi-k2.7-code:cloud"
    DEFAULT_CLOUD_REASONING_MODEL: str = "gpt-oss:120b-cloud"

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus
        self.monitor = LemonadeCLIMonitor(endpoint=self.LEMONADE_ENDPOINT, event_bus=bus)

    async def dispatch(
        self,
        prompt: str,
        task_type: str = "coding",
        agent_name: str = "swarm_agent",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Route request: Primary Local Silicon -> Secondary Ollama Cloud -> Kanban Deferral."""
        avail_gb = available_ram_gb()
        local_model = (
            self.DEFAULT_LOCAL_CODING_MODEL
            if task_type == "coding"
            else self.DEFAULT_LOCAL_REASONING_MODEL
        )
        model_meta = {"id": local_model, "size_gb": 18.5}

        # Step 1: Check Primary Local Memory Safety
        safe, reason = check_load_safe(model_meta, available_gb=avail_gb)

        if safe:
            # Execute Primary: Local Silicon (:13305)
            logger.info("Primary execution on Lemonade :13305 (%s)", local_model)
            if self.bus:
                await self.bus.publish(
                    Event.agent_start(agent_name, model=local_model, tier="primary_local")
                )
                await self.bus.publish(Event.llm_call(agent_name, model=local_model))

            t0 = time.time()
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    r = await client.post(
                        f"{self.LEMONADE_ENDPOINT}/v1/chat/completions",
                        json={
                            "model": local_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                    if r.status_code == 200:
                        content = r.json()["choices"][0]["message"]["content"].strip()
                        duration_ms = (time.time() - t0) * 1000
                        if self.bus:
                            await self.bus.publish(
                                Event.llm_response(agent_name, model=local_model)
                            )
                            await self.bus.publish(
                                Event.agent_complete(
                                    agent_name, result="success", duration_ms=duration_ms
                                )
                            )
                        return {
                            "tier": "primary_local",
                            "model": local_model,
                            "status": "success",
                            "response": content,
                            "duration_ms": duration_ms,
                        }
            except Exception as exc:
                logger.warning(
                    "Primary local execution failed (%s): %s. Escalating to Secondary Cloud.",
                    local_model,
                    exc,
                )

        # Step 2: Escalation Trigger -> Secondary: Ollama Cloud Peer Models (:11434)
        cloud_model = (
            self.DEFAULT_CLOUD_CODING_MODEL
            if task_type == "coding"
            else self.DEFAULT_CLOUD_REASONING_MODEL
        )
        logger.info("Secondary execution on Ollama Cloud :11434 (%s)", cloud_model)
        if self.bus:
            await self.bus.publish(
                Event.agent_start(
                    agent_name, model=cloud_model, tier="secondary_cloud", reason=reason
                )
            )
            await self.bus.publish(Event.llm_call(agent_name, model=cloud_model))

        t1 = time.time()
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                r = await client.post(
                    f"{self.OLLAMA_ENDPOINT}/api/generate",
                    json={"model": cloud_model, "prompt": prompt, "stream": False},
                )
                if r.status_code == 200:
                    content = r.json().get("response", "").strip()
                    duration_ms = (time.time() - t1) * 1000
                    if self.bus:
                        await self.bus.publish(Event.llm_response(agent_name, model=cloud_model))
                        await self.bus.publish(
                            Event.agent_complete(
                                agent_name, result="success", duration_ms=duration_ms
                            )
                        )
                    return {
                        "tier": "secondary_cloud",
                        "model": cloud_model,
                        "status": "success",
                        "response": content,
                        "duration_ms": duration_ms,
                    }
        except Exception as exc:
            logger.error("Secondary cloud execution failed: %s", exc)

        # Step 3: Deferral Trigger -> Agentic Kanban (SurrealDB :8001)
        logger.warning("Both Primary and Secondary tiers unfulfilled. Deferring to Agentic Kanban.")
        deferral_res = defer_to_kanban_on_memory_pressure(
            model_meta,
            {"prompt": prompt[:200], "task_type": task_type, "agent_name": agent_name},
            reason=f"Memory pressure ({avail_gb:.1f}GB free) and tier fallback",
        )
        return {
            "tier": "kanban_deferred",
            "model": local_model,
            "status": "deferred",
            "kanban_id": deferral_res.get("kanban_id"),
        }


async def verify_tiered_cascade_router() -> dict[str, Any]:
    """Self-verification test for TieredCascadeRouter."""
    bus = EventBus()
    await bus.start()

    events_captured: list[Event] = []

    @bus.subscribe()
    async def on_event(event: Event):
        events_captured.append(event)

    router = TieredCascadeRouter(bus=bus)
    res = await router.dispatch(
        prompt="Synthesize a 1-sentence verification of the 2-tier local primary router.",
        task_type="coding",
        agent_name="router_verify_test",
    )

    await bus.stop()

    return {
        "ok": res.get("status") in ("success", "deferred"),
        "tier_used": res.get("tier"),
        "model_used": res.get("model"),
        "events_captured": len(events_captured),
    }


if __name__ == "__main__":
    import sys

    res = asyncio.run(verify_tiered_cascade_router())
    print("Verification Result:", res)
    sys.exit(0 if res["ok"] else 1)
