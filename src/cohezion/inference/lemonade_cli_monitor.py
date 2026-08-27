"""Lemonade CLI & Fleet State Monitor.

Parses Lemonade CLI status and model registry on port 13305 to determine
currently loaded models, active devices (GPU/NPU/CPU), and busy states,
publishing real-time EventBus telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Any

import httpx

from cohezion.core.event_bus import Event, EventBus, EventType


logger = logging.getLogger(__name__)


class LemonadeCLIMonitor:
    """Monitor Lemonade CLI and endpoint status on port 13305."""

    DEFAULT_ENDPOINT: str = "http://localhost:13305"

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, event_bus: EventBus | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.bus = event_bus

    def get_cli_status(self) -> dict[str, Any]:
        """Execute `lemonade status` and return parsed loaded models and device metadata."""
        try:
            res = subprocess.run(
                ["lemonade", "status"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            if res.returncode != 0:
                logger.warning("lemonade status returned code %d", res.returncode)
                return {"ok": False, "loaded_models": [], "devices": {}}

            output = res.stdout
            loaded_models: list[str] = []
            devices: dict[str, str] = {}

            lines = output.splitlines()
            in_table = False
            for line in lines:
                if line.startswith("Model") and "Type" in line and "Device" in line:
                    in_table = True
                    continue
                if in_table and line.strip() and not line.startswith("---"):
                    parts = line.split()
                    if len(parts) >= 3:
                        model_name = parts[0]
                        device = parts[2]
                        loaded_models.append(model_name)
                        devices[model_name] = device

            return {
                "ok": True,
                "loaded_models": loaded_models,
                "devices": devices,
                "raw_output": output[:1000],
            }
        except Exception as exc:
            logger.error("Failed to execute lemonade status: %s", exc)
            return {"ok": False, "loaded_models": [], "devices": {}, "error": str(exc)}

    async def get_active_endpoint_models(self) -> list[str]:
        """Fetch models exposed on Lemonade :13305 /v1/models."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.endpoint}/v1/models")
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    return [m.get("id", "") for m in data if m.get("id")]
        except Exception as exc:
            logger.debug("Failed to query /v1/models: %s", exc)
        return []

    async def publish_fleet_status(self, source: str = "lemonade_cli_monitor") -> Event:
        """Fetch state and publish Event.fleet_status on EventBus."""
        cli_info = self.get_cli_status()
        loaded = cli_info.get("loaded_models", [])
        devices = cli_info.get("devices", {})

        event = Event.fleet_status(
            source=source,
            loaded_models=loaded,
            busy_models=[],  # Reserved for active request tracking
            devices=devices,
        )

        if self.bus:
            await self.bus.publish(event)
            logger.info("Published fleet status: %d models loaded", len(loaded))

        return event


async def verify_lemonade_cli_monitor() -> dict[str, Any]:
    """Isolated self-verification test for LemonadeCLIMonitor."""
    bus = EventBus()
    await bus.start()
    events_captured: list[Event] = []

    @bus.subscribe(EventType.FLEET_STATUS)
    async def on_fleet_status(event: Event):
        events_captured.append(event)

    monitor = LemonadeCLIMonitor(event_bus=bus)
    status_info = monitor.get_cli_status()
    await monitor.publish_fleet_status("verify_test")

    await bus.stop()

    return {
        "ok": status_info.get("ok", False),
        "loaded_models_count": len(status_info.get("loaded_models", [])),
        "event_published": len(events_captured) == 1,
        "captured_event_source": events_captured[0].source if events_captured else "",
        "captured_models": events_captured[0].payload.get("loaded_models", [])
        if events_captured
        else [],
    }


if __name__ == "__main__":
    import sys

    res = asyncio.run(verify_lemonade_cli_monitor())
    print("Verification Result:", res)
    sys.exit(0 if res["ok"] else 1)
