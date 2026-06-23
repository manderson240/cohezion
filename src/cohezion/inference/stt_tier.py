"""DirectLemonadeSTTTier — Whisper-Large-v3-Turbo via OmniRouter :13305 (stub).

Exports consumed by tests/inference/test_stt_tier.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Segment:
    """A single transcription segment."""

    start: float
    end: float
    text: str
    language: str = ""


@dataclass
class STTRequest:
    """Request parameters for speech-to-text."""

    audio: bytes
    model: str = "Whisper-Large-v3-Turbo"
    language: str | None = None
    response_format: str = "json"


@dataclass
class STTResult:
    """Result from a speech-to-text request."""

    text: str
    segments: list[Segment] = field(default_factory=list)
    language: str = ""
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _detect_ext(audio: bytes) -> str:
    """Detect the audio file extension from the first few magic bytes."""
    raise NotImplementedError


def _read_audio(source: Any) -> bytes:
    """Read audio bytes from a file path, bytes object, or file-like object."""
    raise NotImplementedError


def build_stt_tier(port: int = 13305, timeout: float = 30.0) -> "DirectLemonadeSTTTier":
    """Construct a DirectLemonadeSTTTier with the given port and timeout."""
    return DirectLemonadeSTTTier(port=port, timeout=timeout)


class DirectLemonadeSTTTier:
    """Whisper-Large-v3-Turbo STT tier via the Lemonade OmniRouter (:13305)."""

    DEFAULT_PORT: int = 13305

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 30.0) -> None:
        self.port = port
        self.timeout = timeout

    async def transcribe(self, request: STTRequest) -> STTResult:
        """Transcribe audio from *request* and return the result."""
        raise NotImplementedError
