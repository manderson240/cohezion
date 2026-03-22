"""Vault SSE subscription client for real-time vault change notifications."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx


logger = logging.getLogger(__name__)


@dataclass
class VaultEvent:
    """A vault change event received via SSE."""

    event_type: str
    path: str
    timestamp: str
    old_path: str | None = None


# Type for event callbacks
EventCallback = Callable[[VaultEvent], Awaitable[None]]


class VaultSubscriptionClient:
    """Async SSE client for vault change notifications.

    Connects to the Cloud Vault MCP server's /events/vault endpoint
    and dispatches events to registered callbacks.
    """

    def __init__(self, base_url: str = "http://localhost:8360", api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._callbacks: dict[str, list[EventCallback]] = {}
        self._global_callbacks: list[EventCallback] = []
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._client: httpx.AsyncClient | None = None

    def on_event(self, event_type: str):
        """Decorator to register a callback for a specific event type."""

        def decorator(func: EventCallback) -> EventCallback:
            if event_type not in self._callbacks:
                self._callbacks[event_type] = []
            self._callbacks[event_type].append(func)
            return func

        return decorator

    def on_all(self):
        """Decorator to register a callback for all events."""

        def decorator(func: EventCallback) -> EventCallback:
            self._global_callbacks.append(func)
            return func

        return decorator

    async def connect(self) -> None:
        """Start listening for SSE events with auto-reconnect."""
        self._running = True
        delay = self._reconnect_delay

        while self._running:
            try:
                headers = {}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"

                async with httpx.AsyncClient() as client:
                    self._client = client
                    async with client.stream(
                        "GET",
                        f"{self._base_url}/events/vault",
                        headers=headers,
                        timeout=None,
                    ) as response:
                        response.raise_for_status()
                        delay = self._reconnect_delay  # Reset on successful connect
                        logger.info("Connected to vault SSE stream")

                        event_type = None
                        async for line in response.aiter_lines():
                            if not self._running:
                                break

                            line = line.strip()
                            if not line or line.startswith(":"):
                                continue  # Comment or empty (heartbeat)

                            if line.startswith("event: "):
                                event_type = line[7:]
                            elif line.startswith("data: "):
                                data = line[6:]
                                if event_type and data:
                                    event = self._parse_event(event_type, data)
                                    if event:
                                        await self._dispatch(event)
                                    event_type = None

            except Exception as e:
                if not self._running:
                    break
                logger.warning("SSE connection lost: %s. Reconnecting in %.1fs", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_reconnect_delay)

        logger.info("Vault SSE subscription stopped")

    async def disconnect(self) -> None:
        """Stop listening for events."""
        self._running = False
        if self._client:
            await self._client.aclose()
            self._client = None

    def _parse_event(self, event_type: str, data: str) -> VaultEvent | None:
        """Parse SSE data into a VaultEvent."""
        try:
            parsed = json.loads(data)
            return VaultEvent(
                event_type=parsed.get("event_type", event_type),
                path=parsed.get("path", ""),
                timestamp=parsed.get("timestamp", ""),
                old_path=parsed.get("old_path"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug("Failed to parse SSE event: %s", e)
            return None

    async def _dispatch(self, event: VaultEvent) -> None:
        """Dispatch event to registered callbacks. Non-critical: exceptions logged."""
        # Type-specific callbacks
        for callback in self._callbacks.get(event.event_type, []):
            try:
                await callback(event)
            except Exception:
                logger.debug("Callback error for %s event", event.event_type, exc_info=True)

        # Global callbacks
        for callback in self._global_callbacks:
            try:
                await callback(event)
            except Exception:
                logger.debug("Global callback error", exc_info=True)
