"""DirectLemonadeImageTier — SD-Turbo image generation via OmniRouter :13305 (stub).

Exports consumed by tests/inference/test_image_tier.py.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class ImageRequest:
    """Request parameters for image generation."""

    prompt: str
    size: str = "512x512"
    steps: int = 4
    n: int = 1
    model: str = "SD-Turbo"
    response_format: str = "b64_json"
    negative_prompt: str = ""


@dataclass
class ImageResult:
    """Result from an image generation request."""

    images: list[bytes]
    mime_type: str
    size: str
    n: int
    latency_ms: float
    bytes_total: int
    per_image_latency_ms: float
    port: int
    model: str
    prompt: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return len(self.images) > 0 and self.error is None

    def save(self, path: str, index: int = 0) -> None:
        """Write the image at *index* to *path*."""
        Path(path).write_bytes(self.images[index])


class DirectLemonadeImageTier:
    """SD-Turbo image tier via the Lemonade OmniRouter (:13305)."""

    DEFAULT_PORT: int = 13305

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 30.0) -> None:
        self.port = port
        self.timeout = timeout

    async def generate(self, request: ImageRequest) -> ImageResult:
        """Generate an image from *request* and return the result.

        Alias for :meth:`render` (OpenAI-compatible naming).
        """
        return await self.render(request)

    async def render(self, request: ImageRequest) -> ImageResult:
        """Generate images via the OmniRouter /v1/images/generations endpoint."""
        url = f"http://localhost:{self.port}/v1/images/generations"
        body: dict[str, object] = {
            "model": request.model,
            "prompt": request.prompt,
            "size": request.size,
            "steps": request.steps,
            "n": request.n,
            "response_format": request.response_format,
        }
        if request.negative_prompt:
            body["negative_prompt"] = request.negative_prompt

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            return ImageResult(
                images=[],
                mime_type="",
                size=request.size,
                n=request.n,
                latency_ms=latency_ms,
                bytes_total=0,
                per_image_latency_ms=0.0,
                port=self.port,
                model=request.model,
                prompt=request.prompt,
                error=str(exc),
            )

        latency_ms = (time.monotonic() - t0) * 1000
        images: list[bytes] = []
        for item in payload.get("data", []):
            if request.response_format == "b64_json":
                b64 = item.get("b64_json", "")
                if b64:
                    images.append(base64.b64decode(b64))
            elif item.get("url"):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        img_resp = await client.get(item["url"])
                        img_resp.raise_for_status()
                        images.append(img_resp.content)
                except Exception:
                    pass

        total = sum(len(i) for i in images)
        return ImageResult(
            images=images,
            mime_type="image/png",
            size=request.size,
            n=request.n,
            latency_ms=latency_ms,
            bytes_total=total,
            per_image_latency_ms=latency_ms / max(request.n, 1),
            port=self.port,
            model=request.model,
            prompt=request.prompt,
        )

    async def is_alive(self) -> bool:
        """Return True if the OmniRouter is responding on self.port."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://localhost:{self.port}/api/v1/health")
                return resp.status_code < 500
        except Exception:
            return False
