"""DirectLemonadeImageTier — SD-Turbo image generation via OmniRouter :13305 (stub).

Exports consumed by tests/inference/test_image_tier.py.
"""

from __future__ import annotations

from dataclasses import dataclass


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


class DirectLemonadeImageTier:
    """SD-Turbo image tier via the Lemonade OmniRouter (:13305)."""

    DEFAULT_PORT: int = 13305

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 30.0) -> None:
        self.port = port
        self.timeout = timeout

    async def generate(self, request: ImageRequest) -> ImageResult:
        """Generate an image from *request* and return the result."""
        raise NotImplementedError
