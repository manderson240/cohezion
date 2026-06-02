"""Lemonade nomic-embed text encoder (768D) for the semantic cache.

Primary embedding backend on AMD Strix Halo / XDNA2, where sentence-transformers
segfaults under ROCm. Serves `nomic-embed-text-v2-moe-GGUF` over lemonade's
OpenAI-compatible ``/v1/embeddings`` endpoint (router port 13305, ~6ms latency).

Calibration (harness invariant CA1, exp_OOOO2, 2026-05-29):
  - 768D nomic-embed similarity threshold = 0.58 (0% false positives, 100% hit rate;
    near-duplicate similarity 0.963-0.977, unrelated 0.15-0.20).

This module is import-safe with NO network at import time: ``get_lemonade_encoder()``
builds a lazy client and ``is_available()`` probes the endpoint on demand, so the
semantic cache imports cleanly even when the local fleet is offline (it then falls
back to the next encoder tier).
"""

from __future__ import annotations

import json
import logging
import urllib.request

import numpy as np

logger = logging.getLogger(__name__)

# Encoder-calibrated cosine threshold for 768D nomic-embed (harness CA1).
OPTIMAL_THRESHOLD: float = 0.58

_DEFAULT_BASE_URL = "http://localhost:13305"
_DEFAULT_MODEL = "nomic-embed-text-v2-moe-GGUF"
_EMBED_DIM = 768


class LemonadeEncoder:
    """OpenAI-compatible embeddings client for lemonade-served nomic-embed.

    Lazy: no network call until ``is_available()`` or ``encode()`` is invoked.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        embedding_dim: int = _EMBED_DIM,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_dim = embedding_dim
        self.timeout = timeout

    def is_available(self) -> bool:
        """Return True if the lemonade embeddings endpoint is reachable."""
        try:
            req = urllib.request.Request(f"{self.base_url}/v1/models")
            with urllib.request.urlopen(req, timeout=2.0) as resp:  # noqa: S310 (fixed localhost)
                return resp.status == 200
        except Exception:
            return False

    def encode(self, text: str) -> np.ndarray:
        """Embed ``text`` to an L2-normalized 768D vector via lemonade.

        Raises on transport/parse failure so callers can fall back to the next
        encoder tier (the semantic cache wraps this in try/except).
        """
        payload = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v1/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (fixed localhost)
            data = json.loads(resp.read())
        vec = np.asarray(data["data"][0]["embedding"], dtype=np.float32)
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 0 else vec


_ENCODER: LemonadeEncoder | None = None


def get_lemonade_encoder() -> LemonadeEncoder:
    """Return the process-wide lemonade encoder singleton (lazy, no network at call)."""
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = LemonadeEncoder()
    return _ENCODER


def reset_lemonade_encoder() -> None:
    """Reset the singleton (test isolation)."""
    global _ENCODER
    _ENCODER = None
