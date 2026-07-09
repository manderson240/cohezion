"""DirectLemonadeSTTTier — Whisper-Large-v3-Turbo via OmniRouter :13305.

Exports consumed by tests/inference/test_stt_tier.py.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


_EXT_TO_MIME: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "webm": "audio/webm",
}

# Magic byte → extension (order matters: check longer prefixes first)
_MAGIC_MAP: list[tuple[bytes, str]] = [
    (b"RIFF", "wav"),
    (b"OggS", "ogg"),
    (b"fLaC", "flac"),
    (b"ID3", "mp3"),
]


@dataclass
class Segment:
    """A single transcription segment."""

    id: int = 0
    start: float = 0.0
    end: float = 0.0
    text: str = ""
    tokens: list[int] = field(default_factory=list)
    temperature: float = 0.0
    avg_logprob: float = 0.0
    compression_ratio: float = 1.0
    no_speech_prob: float = 0.0
    language: str = ""

    @classmethod
    def from_api(cls, raw: dict) -> Segment:
        return cls(
            id=raw.get("id", 0),
            start=raw.get("start", 0.0),
            end=raw.get("end", 0.0),
            text=raw.get("text", ""),
            tokens=raw.get("tokens", []),
            temperature=raw.get("temperature", 0.0),
            avg_logprob=raw.get("avg_logprob", 0.0),
            compression_ratio=raw.get("compression_ratio", 1.0),
            no_speech_prob=raw.get("no_speech_prob", 0.0),
            language=raw.get("language", ""),
        )


@dataclass
class STTRequest:
    """Request parameters for speech-to-text."""

    audio: bytes
    model: str = "Whisper-Large-v3-Turbo"
    language: str | None = None
    response_format: str = "json"
    temperature: float = 0.0
    prompt: str | None = None


@dataclass
class STTResult:
    """Result from a speech-to-text request."""

    text: str
    mime_type: str
    audio_bytes: int
    duration_s: float | None
    language: str | None
    segments: list[Segment]
    response_format: str
    latency_ms: float
    bytes_per_sec: float
    model: str
    port: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text.strip() else 0


def _detect_ext(source: Any) -> str:
    """Detect the audio file extension from the source (bytes or path string)."""
    if isinstance(source, (str, os.PathLike)):
        suffix = Path(source).suffix.lstrip(".").lower()
        return suffix if suffix in _EXT_TO_MIME else "mp3"
    if isinstance(source, (bytes, bytearray)):
        for magic, ext in _MAGIC_MAP:
            if source[: len(magic)] == magic:
                return ext
        # MP3 sync word: 0xFF followed by 0xE0–0xFF in second byte
        if len(source) >= 2 and source[0] == 0xFF and (source[1] & 0xE0) == 0xE0:
            return "mp3"
    return "mp3"


def _read_audio(source: Any) -> tuple[bytes, str, str]:
    """Read audio bytes from a file path, bytes object, or file-like object.

    Returns (data, filename, mime_type).
    """
    if isinstance(source, (str, os.PathLike)):
        p = Path(source)
        data = p.read_bytes()
        ext = p.suffix.lstrip(".").lower()
        mime = _EXT_TO_MIME.get(ext, "audio/mpeg")
        return data, p.name, mime
    if isinstance(source, (bytes, bytearray)):
        ext = _detect_ext(source)
        mime = _EXT_TO_MIME.get(ext, "audio/mpeg")
        return bytes(source), f"audio.{ext}", mime
    # File-like object
    data = source.read()
    ext = _detect_ext(data)
    mime = _EXT_TO_MIME.get(ext, "audio/mpeg")
    return data, f"audio.{ext}", mime


def build_stt_tier(port: int = 13305, timeout: float = 30.0) -> DirectLemonadeSTTTier:
    """Construct a DirectLemonadeSTTTier with the given port and timeout."""
    return DirectLemonadeSTTTier(port=port, timeout=timeout)


class DirectLemonadeSTTTier:
    """Whisper-Large-v3-Turbo STT tier via the Lemonade OmniRouter (:13305)."""

    DEFAULT_PORT: int = 13305
    DEFAULT_MODEL: str = "Whisper-Large-v3-Turbo"

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 30.0) -> None:
        self.port = port
        self.timeout = timeout

    async def transcribe(self, request: STTRequest) -> STTResult:
        """Transcribe audio from *request* and return the result."""
        url = f"http://localhost:{self.port}/v1/audio/transcriptions"
        audio_data, fname, fmime = _read_audio(request.audio)

        form_data: dict[str, str] = {"model": request.model}
        # Omit response_format when it is the default "json" (per OpenAI spec)
        if request.response_format != "json":
            form_data["response_format"] = request.response_format
        if request.language:
            form_data["language"] = request.language
        if request.temperature != 0.0:
            form_data["temperature"] = str(request.temperature)
        if request.prompt:
            form_data["prompt"] = request.prompt

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    files={"file": (fname, audio_data, fmime)},
                    data=form_data,
                )
                resp.raise_for_status()
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            return STTResult(
                text="",
                mime_type=fmime,
                audio_bytes=len(audio_data),
                duration_s=None,
                language=None,
                segments=[],
                response_format=request.response_format,
                latency_ms=latency_ms,
                bytes_per_sec=0.0,
                model=request.model,
                port=self.port,
                error=str(exc),
            )

        latency_ms = (time.monotonic() - t0) * 1000

        text = ""
        language: str | None = None
        duration_s: float | None = None
        segments: list[Segment] = []

        if request.response_format == "text":
            text = resp.content.decode("utf-8", errors="replace").strip()
        elif request.response_format == "verbose_json":
            body = resp.json()
            text = body.get("text", "")
            language = body.get("language")
            duration_s = body.get("duration")
            segments = [Segment.from_api(s) for s in body.get("segments", [])]
        else:  # json (default)
            body = resp.json()
            text = body.get("text", "")
            language = body.get("language")

        dur = duration_s or max(len(audio_data) / 32000, 1e-6)
        bps = len(audio_data) / dur

        return STTResult(
            text=text,
            mime_type=fmime,
            audio_bytes=len(audio_data),
            duration_s=duration_s,
            language=language,
            segments=segments,
            response_format=request.response_format,
            latency_ms=latency_ms,
            bytes_per_sec=bps,
            model=request.model,
            port=self.port,
        )

    async def is_alive(self) -> bool:
        """Return True if the OmniRouter is responding on self.port."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://localhost:{self.port}/api/v1/health")
                return resp.status_code < 500
        except Exception:
            return False
