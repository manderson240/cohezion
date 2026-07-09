"""DirectLemonadeTTSTier — kokoro-v1 TTS via OmniRouter :13305.

Exports consumed by tests/inference/test_tts_tier.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx


_FORMAT_TO_MIME: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "opus": "audio/opus",
    "flac": "audio/flac",
    "pcm": "audio/pcm",
    "aac": "audio/aac",
}


@dataclass
class TTSRequest:
    """Request parameters for text-to-speech."""

    text: str
    voice: str = "default"
    speed: float = 1.0
    response_format: str = "mp3"
    model: str = "kokoro-v1"


@dataclass
class TTSResult:
    """Result from a text-to-speech request."""

    audio: bytes
    mime_type: str
    latency_ms: float
    voice: str = "default"
    bytes_per_char: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and len(self.audio) > 0


def build_tts_tier(port: int = 13305, timeout: float = 30.0) -> DirectLemonadeTTSTier:
    """Construct a DirectLemonadeTTSTier with the given port and timeout."""
    return DirectLemonadeTTSTier(port=port, timeout=timeout)


class DirectLemonadeTTSTier:
    """kokoro-v1 TTS tier via the Lemonade OmniRouter (:13305)."""

    DEFAULT_PORT: int = 13305

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 30.0) -> None:
        self.port = port
        self.timeout = timeout

    async def speak(self, request: TTSRequest) -> TTSResult:
        """Synthesize speech from *request* and return the result."""
        url = f"http://localhost:{self.port}/v1/audio/speech"
        mime = _FORMAT_TO_MIME.get(request.response_format, "audio/mpeg")
        n_chars = max(len(request.text), 1)

        payload = {
            "model": request.model,
            "input": request.text,
            "voice": request.voice,
            "response_format": request.response_format,
            "speed": request.speed,
        }

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                audio = resp.content
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            return TTSResult(
                audio=b"",
                mime_type=mime,
                latency_ms=latency_ms,
                voice=request.voice,
                bytes_per_char=0.0,
                error=str(exc),
            )

        latency_ms = (time.monotonic() - t0) * 1000
        return TTSResult(
            audio=audio,
            mime_type=mime,
            latency_ms=latency_ms,
            voice=request.voice,
            bytes_per_char=len(audio) / n_chars,
        )

    async def is_alive(self) -> bool:
        """Return True if the OmniRouter is responding on self.port."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://localhost:{self.port}/api/v1/health")
                return resp.status_code < 500
        except Exception:
            return False
