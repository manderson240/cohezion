"""Lemonade v11.7.0 Feature Harness & Telemetry Bridge.

Directly leverages new built-in v11.7.0 capabilities:
1. `GET /v1/stats` & `/metrics`: Prefix-cache effectiveness and routing performance.
2. `GET/POST/DELETE /v1/models/{id}/options`: Inspect & configure per-model recipe options (e.g. ctx_size, llamacpp_args).
3. `POST /v1/models/register`: Dynamic user.* model definition registration without downloading files.
"""

from __future__ import annotations

from typing import Any

import httpx


class LemonadeV117Client:
    def __init__(self, base_url: str = "http://127.0.0.1:13305", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_server_stats(self) -> dict[str, Any]:
        """Fetch v11.7.0 prefix-cache hit rates and throughput telemetry."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/v1/stats")
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result

    async def get_model_options(self, model_id: str) -> dict[str, Any]:
        """Inspect model recipe options without loading the model."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/v1/models/{model_id}/options")
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result

    async def set_model_options(self, model_id: str, options: dict[str, Any]) -> dict[str, Any]:
        """Save persistent per-model recipe options."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/models/{model_id}/options", json=options)
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result

    async def register_model(self, model_def: dict[str, Any]) -> dict[str, Any]:
        """Register/update user.* model definitions without downloading files."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/models/register", json=model_def)
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result
