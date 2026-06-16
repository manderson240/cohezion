"""Lemonade multimodal client — TTS, STT, embeddings via :13305 router.

Wraps live non-LLM capabilities of the Lemonade unified router:
  - kokoro-v1 (0.354GB): OpenAI-compatible TTS via POST /v1/audio/speech
  - Whisper-Large-v3-Turbo (~1.5GB): STT via POST /v1/audio/transcriptions
  - nomic-embed-text-v2-moe-GGUF (768D): embeddings via POST /v1/embeddings

All methods are non-fatal: errors are logged at DEBUG level and a safe empty
value is returned so callers never need to handle exceptions.

OOM safety: SD-Turbo is intentionally excluded (image gen, OOM risk under load).
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)

_KOKORO_MODEL = "kokoro-v1"
_WHISPER_MODEL = "Whisper-Large-v3-Turbo"
_EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"


class LemonadeMultimodalClient:
    """Thin synchronous client for Lemonade's non-LLM capabilities.

    Uses httpx for HTTP, all with a 30s default timeout (overridden for
    availability checks). All failures are swallowed — callers get safe
    empty values instead of exceptions.
    """

    def __init__(self, base_url: str = "http://localhost:13305") -> None:
        import httpx

        self._client = httpx.Client(base_url=base_url, timeout=30.0)

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    def speak(self, text: str, voice: str = "af_sky", speed: float = 1.0) -> bytes:
        """Convert *text* to speech via kokoro-v1.

        Returns raw audio bytes (mp3).  Returns b"" on any failure.
        """
        try:
            resp = self._client.post(
                "/v1/audio/speech",
                json={
                    "model": _KOKORO_MODEL,
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                },
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.debug("LemonadeMultimodalClient.speak failed: %s", exc)
            return b""

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribe *audio_bytes* via Whisper-Large-v3-Turbo.

        Returns transcription text.  Returns "" on any failure.
        """
        try:
            resp = self._client.post(
                "/v1/audio/transcriptions",
                files={"file": (filename, audio_bytes, "audio/wav")},
                data={"model": _WHISPER_MODEL},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")
        except Exception as exc:
            logger.debug("LemonadeMultimodalClient.transcribe failed: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed *texts* via nomic-embed-text-v2-moe-GGUF (768D).

        Returns a list of float vectors, one per input text.
        Returns [] on any failure.
        """
        try:
            resp = self._client.post(
                "/v1/embeddings",
                json={"model": _EMBED_MODEL, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [item["embedding"] for item in data]
        except Exception as exc:
            logger.debug("LemonadeMultimodalClient.embed failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the Lemonade router is reachable (2s timeout)."""
        try:
            resp = self._client.get("/v1/models", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_multimodal_client(
    base_url: str = "http://localhost:13305",
) -> LemonadeMultimodalClient | None:
    """Return a client if the Lemonade router is reachable, else None."""
    client = LemonadeMultimodalClient(base_url=base_url)
    if client.is_available():
        return client
    logger.debug("make_multimodal_client: Lemonade router unreachable at %s", base_url)
    return None


# ---------------------------------------------------------------------------
# FUTURE HOOKS
# ---------------------------------------------------------------------------
# - SD-Turbo image generation (POST /v1/images/generations) once a memory
#   gate is in place to prevent OOM when combined with Whisper + kokoro.
# - Async variant (httpx.AsyncClient) for use in async compound loops.
# - Streaming TTS (chunked response) for low-latency narration.
