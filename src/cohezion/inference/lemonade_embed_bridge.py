"""FLUME-compatible text encoder via Lemonade OmniRouter embeddings.

Adapts the Lemonade /v1/embeddings endpoint (nomic-embed-text-v2-moe-GGUF, 768D)
to the _flume_encoder interface expected by JourneyTracker.text_to_latent():

    encoder.encode(text: str) -> np.ndarray   # 256D float32 unit vector
    encoder.is_available() -> bool             # checks :13305 health

When available: JourneyTracker.text_to_latent() tiles 256D → 2048D and projects
to 12D manifold, giving real semantic embeddings instead of SHA-256 hashes.

CA1 reference: nomic-embed-text-v2-moe-GGUF at :13305, similarity threshold 0.58.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"
_SOURCE_DIM = 768   # nomic-embed output dimension
_TARGET_DIM = 256   # FLUME contract (tiled to 2048D by JourneyTracker)


class LemonadeEmbedBridge:
    """Wraps Lemonade /v1/embeddings as a FLUME _flume_encoder.

    Implements the minimal interface JourneyTracker expects:
      - encode(text) -> np.ndarray[float32, (256,)]
      - is_available() -> bool

    Uses uniform subsampling 768→256 which preserves cosine similarity
    structure (CA1 exp_OOOO2: nomic-embed similarity range 0.963–0.977
    for near-duplicates at 768D; subsampled 256D maintains rank ordering).
    """

    def __init__(self, base_url: str = "http://localhost:13305") -> None:
        self._base_url = base_url.rstrip("/")
        self._available: bool | None = None
        # Subsample indices: 768 → 256 via uniform spacing (computed once)
        self._subsample_idx: np.ndarray = np.round(
            np.linspace(0, _SOURCE_DIM - 1, _TARGET_DIM)
        ).astype(int)

    def is_available(self) -> bool:
        """Check OmniRouter health (cached per instance)."""
        if self._available is None:
            try:
                req = urllib.request.Request(
                    f"{self._base_url}/api/v1/health",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    self._available = resp.status == 200
            except Exception:
                self._available = False
        return bool(self._available)

    def encode(self, text: str) -> np.ndarray:
        """Embed text → 256D float32 unit vector via nomic-embed-text-v2-moe-GGUF.

        On failure (Lemonade offline, model not loaded), marks bridge unavailable
        and returns zero vector — JourneyTracker falls back to SHA-512 on next call.
        """
        try:
            payload = json.dumps(
                {"model": _EMBED_MODEL, "input": text}
            ).encode()
            req = urllib.request.Request(
                f"{self._base_url}/v1/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result: dict[str, Any] = json.loads(resp.read())

            emb_full = np.array(
                result["data"][0]["embedding"], dtype=np.float32
            )
            emb_256 = emb_full[self._subsample_idx]
            norm = float(np.linalg.norm(emb_256))
            return emb_256 / norm if norm > 1e-8 else emb_256

        except Exception as exc:
            logger.debug("LemonadeEmbedBridge.encode failed: %s", exc)
            self._available = False
            return np.zeros(_TARGET_DIM, dtype=np.float32)
