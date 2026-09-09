from __future__ import annotations

import httpx
import time
from typing import Any, Optional
from cohezion.inference.transports.base import BaseInferenceTransport, TransportResponse

class OllamaCloudTransport(BaseInferenceTransport):
    """Transport adapter for Ollama Cloud endpoints (:11434)."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.url = f"{self.base_url}/api/generate"

    async def query(self, prompt: str, model_id: str, params: Optional[dict[str, Any]] = None) -> Optional[TransportResponse]:
        t0 = time.perf_counter()
        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": params or {}
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(self.url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw = (data.get("response") or data.get("thinking") or "").strip()
                    if "</think>" in raw:
                        raw = raw.split("</think>")[-1].strip()
                    
                    return TransportResponse(
                        content=raw,
                        model_name=model_id,
                        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                        verified=True
                    )
        except Exception:
            return None
        return None

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False
