from __future__ import annotations

import httpx
import time
from typing import Any, Optional
from cohezion.inference.transports.base import BaseInferenceTransport, TransportResponse

class LemonadeTransport(BaseInferenceTransport):
    """Transport adapter for the Lemonade OmniRouter (:13305)."""
    
    def __init__(self, port: int = 13305):
        self.port = port
        self.url = f"http://localhost:{port}/v1/chat/completions"

    async def query(self, prompt: str, model_id: str, params: Optional[dict[str, Any]] = None) -> Optional[TransportResponse]:
        t0 = time.perf_counter()
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            ** (params or {})
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(self.url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    msg = data["choices"][0]["message"]
                    raw = (msg.get("content") or msg.get("reasoning_content") or "").strip()
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
                res = await client.get(f"http://localhost:{self.port}/v1/models")
                return res.status_code == 200
        except Exception:
            return False
