"""EVO modality handlers — text, audio, image, video.

Each handler wraps a Lemonade :13305 endpoint and returns a ModalityResult.
All handlers fail-soft (never raise), consistent with Constitution §fail-soft for
non-blocking modalities.

Lemonade 10.6.0 support status:
  text  — local LLM synthesis via :13305 chat/completions (NPU→iGPU tier) [fully operational]
  audio — TTS via kokoro-v1, ASR via Whisper                               [fully operational]
  image — SD-Turbo (Lite) / Flux-2-Klein-9B (Dense)                        [fully operational]
  video — not yet in lemonade 10.6.0 catalog                               [forward-wired, graceful stub]

N3 OOM: modality handlers do NOT load models — they hit the router which pre-loaded
them. ctx_size=0 hazard is the router's responsibility (already bounded per N3).

TextModality delegates to the Triune orchestrator via make_local_execute_fn() so
EVO trace steps generate real synthesis on AMD silicon (NPU → iGPU → CPU).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_LEMONADE_BASE = "http://localhost:13305"
_TTS_TIMEOUT = 15  # seconds — kokoro-v1 is fast
_IMAGE_TIMEOUT = 30  # seconds — diffusion takes longer
_TEXT_TIMEOUT = 30  # seconds — synthesis via 35B reasoner can take ~1.5s

# NoThinking variant: same Qwen3.6-35B weights but with reasoning tokens disabled.
# The MTP/default variants put all tokens into <think> blocks before generating content,
# so max_tokens runs out before any content is produced. NoThinking routes directly
# to the output layer. (Verified 2026-06-12 against live :13305 catalog.)
_TEXT_MODEL = "Qwen3.6-35B-A3B-NoThinking"


@dataclass
class ModalityResult:
    """Outcome of a single modality invocation."""

    modality: str
    success: bool
    output: str  # text, audio size string, image URL, or empty on failure
    error: str | None = None
    latency_ms: float = 0.0


class TextModality:
    """Text modality — local LLM synthesis via Triune orchestrator (:13305 router).

    Dispatches the EVO step description to the NPU→iGPU→CPU tier for reasoning
    synthesis. The router selects the appropriate model (Gemma-4-E4B for iGPU,
    llama3.2-1b-FLM for NPU short outputs) based on the task classifier.

    Falls back gracefully to prompt echo when Lemonade is unavailable — preserves
    the fail-soft contract and keeps tests from requiring a live server.
    """

    name = "text"
    # Compact system prompt: keeps TTS/journey context short for NPU tier
    _SYSTEM = (
        "You are an EVO agent synthesizing one insight from an experiential voyage step. "
        "Reply in one sentence. Be specific. Focus on what changed in the latent space."
    )

    def invoke(self, prompt: str, **kwargs: Any) -> ModalityResult:
        """Synthesize one insight from the EVO step via local LLM inference."""
        model = kwargs.get("text_model", _TEXT_MODEL)
        t0 = time.perf_counter()
        try:
            payload = json.dumps(
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": self._SYSTEM},
                        {"role": "user", "content": prompt[:500]},
                    ],
                    "max_tokens": 80,
                    "temperature": 0.4,
                    "stream": False,
                }
            ).encode()
            req = urllib.request.Request(
                f"{_LEMONADE_BASE}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TEXT_TIMEOUT) as resp:
                data = json.load(resp)
            latency_ms = (time.perf_counter() - t0) * 1000
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            model_used = data.get("model", "unknown")
            if not text:
                return ModalityResult(
                    modality="text",
                    success=False,
                    output="",
                    error="empty response from router",
                    latency_ms=latency_ms,
                )
            logger.debug(
                "TextModality: synthesis via %s (%.0fms): %s",
                model_used,
                latency_ms,
                text[:80],
            )
            return ModalityResult(
                modality="text",
                success=True,
                output=text,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.debug("TextModality LLM failed (non-blocking, falling back): %s", exc)
            # Fail-soft: return echo so the EVO pipeline can continue without a live server
            return ModalityResult(
                modality="text",
                success=False,
                output=prompt[:200],
                error=str(exc),
            )


class AudioModality:
    """Audio modality — TTS via kokoro-v1 on Lemonade :13305.

    Invokes the OpenAI-compatible /v1/audio/speech endpoint. Returns byte count
    on success so the modality result is serializable without persisting audio blobs.

    ASR (transcription) path is available at /v1/audio/transcriptions but requires
    a binary audio payload — omitted here since EVO journeys are text-driven.
    """

    name = "audio"

    def invoke(self, prompt: str, **kwargs: Any) -> ModalityResult:
        """Convert task description to speech via kokoro-v1."""
        voice = kwargs.get("voice", "af_heart")
        t0 = time.perf_counter()
        try:
            payload = json.dumps(
                {
                    "model": "kokoro-v1",
                    "input": prompt[:1000],  # cap to avoid unbounded TTS requests
                    "voice": voice,
                    "response_format": "mp3",
                }
            ).encode()
            req = urllib.request.Request(
                f"{_LEMONADE_BASE}/v1/audio/speech",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TTS_TIMEOUT) as resp:
                audio_bytes = resp.read()
            latency_ms = (time.perf_counter() - t0) * 1000
            return ModalityResult(
                modality="audio",
                success=True,
                output=f"tts:{len(audio_bytes)}B kokoro-v1 voice={voice}",
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.debug("AudioModality TTS failed (non-blocking): %s", exc)
            return ModalityResult(
                modality="audio",
                success=False,
                output="",
                error=str(exc),
            )


class ImageModality:
    """Image modality — SD-Turbo (Lite) or Flux-2-Klein-9B (Dense) via Lemonade :13305."""

    name = "image"

    def __init__(self, model: str = "SD-Turbo") -> None:
        self._model = model

    def invoke(self, prompt: str, **kwargs: Any) -> ModalityResult:
        """Generate image from prompt via Lemonade images/generations endpoint."""
        model = kwargs.get("image_model", self._model)
        t0 = time.perf_counter()
        try:
            payload = json.dumps(
                {
                    "model": model,
                    "prompt": prompt[:300],
                    "n": 1,
                    "size": "512x512",
                }
            ).encode()
            req = urllib.request.Request(
                f"{_LEMONADE_BASE}/v1/images/generations",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_IMAGE_TIMEOUT) as resp:
                data = json.load(resp)
            latency_ms = (time.perf_counter() - t0) * 1000
            url = data.get("data", [{}])[0].get("url", "")
            return ModalityResult(
                modality="image",
                success=bool(url),
                output=url,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.debug("ImageModality failed (non-blocking): %s", exc)
            return ModalityResult(
                modality="image",
                success=False,
                output="",
                error=str(exc),
            )


class VideoModality:
    """Video modality — not yet in lemonade 10.6.0 catalog; forward-wired for compatibility.

    The original directive specifies "extending to video" — this handler registers the
    modality in the EVO journey for observability and forward-compatibility. When lemonade
    adds a `video`-label recipe (tracked upstream), the invoke() body will activate.

    Does NOT raise — returns a structured ModalityResult so the EVO pipeline can record
    video intent in the journey without blocking on unsupported capability.
    """

    name = "video"
    CATALOG_GAP = (
        "video generation requires a `video`-label recipe not yet available in "
        "lemonade 10.6.0 (extending to video: wired for forward compatibility)"
    )

    def invoke(self, prompt: str, **kwargs: Any) -> ModalityResult:
        logger.info("VideoModality intent logged — %s", self.CATALOG_GAP)
        return ModalityResult(
            modality="video",
            success=False,
            output="",
            error=self.CATALOG_GAP,
        )


_REGISTRY: dict[str, Any] = {
    "text": TextModality(),
    "audio": AudioModality(),
    "image": ImageModality(),
    "video": VideoModality(),
}


def get_modality(name: str) -> Any:
    """Return the registered handler for a modality, falling back to TextModality."""
    return _REGISTRY.get(name, TextModality())
