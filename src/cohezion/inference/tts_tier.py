"""DirectLemonadeTTSTier — kokoro-v1 TTS via OmniRouter :13305 (stub).

Exports consumed by tests/inference/test_tts_tier.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TTSRequest:
    """Request parameters for text-to-speech."""

    text: str
    voice: str = "default"
    speed: float = 1.0
    response_format: str = "mp3"


@dataclass
class TTSResult:
    """Result from a text-to-speech request."""

    audio: bytes
    mime_type: str
    latency_ms: float
    bytes_per_char: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and len(self.audio) > 0


class DirectLemonadeTTSTier:
    """kokoro-v1 TTS tier via the Lemonade OmniRouter (:13305)."""

    DEFAULT_PORT: int = 13305

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 30.0) -> None:
        self.port = port
        self.timeout = timeout

    async def speak(self, request: TTSRequest) -> TTSResult:
        """Synthesize speech from *request* and return the result."""
        raise NotImplementedError
