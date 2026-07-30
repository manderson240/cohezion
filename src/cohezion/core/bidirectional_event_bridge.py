"""Bi-Directional EventBus Bridge & Request-Reply RPC System.

Enables 2-way asynchronous communication between agents, background sessions,
and daemons using correlation IDs and acknowledgment streams over EventBus.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from cohezion.core.event_bus import Event, EventBus, EventType


logger = logging.getLogger(__name__)


class BiDirectionalEventBridge:
    """Bi-directional request-reply RPC bridge over EventBus."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._pending_requests: dict[str, asyncio.Future[Event]] = {}
        self._reply_handlers: dict[str, Callable[[Event], Any]] = {}

        @self.bus.subscribe()
        async def _on_event(event: Event) -> None:
            corr_id = event.payload.get("correlation_id")
            # Handle reply matching pending correlation_id
            if (
                corr_id
                and corr_id in self._pending_requests
                and not event.payload.get("is_request")
            ):
                future = self._pending_requests[corr_id]
                if not future.done():
                    future.set_result(event)
                return

            # Handle inbound request targeting an agent
            target_agent = event.payload.get("target_agent")
            if (
                target_agent
                and target_agent in self._reply_handlers
                and event.payload.get("is_request")
            ):
                handler = self._reply_handlers[target_agent]
                try:
                    res_payload = (
                        await handler(event)
                        if asyncio.iscoroutinefunction(handler)
                        else handler(event)
                    )
                    reply_event = Event(
                        type=EventType.CUSTOM,
                        source=target_agent,
                        payload={
                            "is_request": False,
                            "correlation_id": corr_id,
                            "reply_to": event.source,
                            "result": res_payload,
                            "status": "success",
                        },
                    )
                    await self.bus.publish(reply_event)
                except Exception as exc:
                    logger.error("Error in reply handler for %s: %s", target_agent, exc)
                    error_reply = Event(
                        type=EventType.CUSTOM,
                        source=target_agent,
                        payload={
                            "is_request": False,
                            "correlation_id": corr_id,
                            "reply_to": event.source,
                            "error": str(exc),
                            "status": "error",
                        },
                    )
                    await self.bus.publish(error_reply)

    def register_agent(self, agent_name: str, handler: Callable[[Event], Any]) -> None:
        """Register a bi-directional reply handler for target agent."""
        self._reply_handlers[agent_name] = handler
        logger.info("Registered bi-directional handler for agent '%s'", agent_name)

    async def request(
        self,
        sender_agent: str,
        target_agent: str,
        command: str,
        data: dict[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> Event:
        """Send a request to target_agent and await 2-way reply."""
        correlation_id = f"corr_{uuid.uuid4().hex[:12]}"
        future: asyncio.Future[Event] = asyncio.get_running_loop().create_future()
        self._pending_requests[correlation_id] = future

        req_event = Event(
            type=EventType.CUSTOM,
            source=sender_agent,
            payload={
                "is_request": True,
                "target_agent": target_agent,
                "command": command,
                "data": data or {},
                "correlation_id": correlation_id,
            },
        )

        try:
            await self.bus.publish(req_event)
            reply = await asyncio.wait_for(future, timeout=timeout_seconds)
            return reply
        finally:
            self._pending_requests.pop(correlation_id, None)


async def verify_bidirectional_bridge() -> dict[str, Any]:
    """Self-verification test for BiDirectionalEventBridge."""
    bus = EventBus()
    await bus.start()

    bridge = BiDirectionalEventBridge(bus)

    # Agent B registers a 2-way handler
    async def agent_b_handler(event: Event) -> dict[str, Any]:
        cmd = event.payload.get("command")
        return {"acknowledged": True, "processed_command": cmd, "echo": event.payload.get("data")}

    bridge.register_agent("agent_b", agent_b_handler)

    # Agent A sends a 2-way request to Agent B
    t0 = time.time()
    response = await bridge.request(
        sender_agent="agent_a",
        target_agent="agent_b",
        command="QUERY_STATE",
        data={"query": "active_models"},
        timeout_seconds=5.0,
    )
    duration_ms = (time.time() - t0) * 1000

    await bus.stop()

    payload = response.payload
    ok = (
        payload.get("status") == "success" and payload.get("result", {}).get("acknowledged") is True
    )

    return {
        "ok": ok,
        "roundtrip_ms": round(duration_ms, 2),
        "source": response.source,
        "result": payload.get("result"),
    }


if __name__ == "__main__":
    import sys

    res = asyncio.run(verify_bidirectional_bridge())
    print("Verification Result:", res)
    sys.exit(0 if res["ok"] else 1)
