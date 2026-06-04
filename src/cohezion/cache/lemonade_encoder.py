"""Lemonade-backed semantic text encoder using nomic-embed-text-v2-moe-GGUF.

768D embeddings with clean semantic discrimination:
  near-duplicate similarity: 0.96-0.98
  unrelated similarity: 0.15-0.20
  optimal threshold: 0.58

Latency: ~6ms per embedding (vs 500ms+ for cache miss savings → 80x+ ROI).
"""

import json
import logging
import urllib.error
import urllib.request

import numpy as np


logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:13305/v1/embeddings"
_DEFAULT_MODEL = "nomic-embed-text-v2-moe-GGUF"
_DEFAULT_TIMEOUT = 8  # seconds

# Threshold calibrated empirically (exp_OOOO2):
# near-dupe range 0.963-0.977, unrelated range 0.154-0.202 → midpoint 0.58
OPTIMAL_THRESHOLD = 0.58
EMBEDDING_DIM = 768


class LemonadeEmbedEncoder:
    """Semantic encoder via lemonade /v1/embeddings API.

    Parameters
    ----------
    base_url : str
        Lemonade embeddings endpoint URL
    model : str
        Embedding model name available on lemonade
    timeout : float
        Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.embedding_dim = EMBEDDING_DIM
        self._available: bool | None = None  # lazy probe

    def is_available(self) -> bool:
        """Check if the lemonade embedding endpoint is reachable."""
        if self._available is not None:
            return self._available
        try:
            self._raw_embed("probe")
            self._available = True
        except Exception:
            self._available = False
        return self._available

    def _raw_embed(self, text: str) -> np.ndarray:
        payload = json.dumps({"model": self.model, "input": text}).encode()
        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            d = json.loads(resp.read())
        vec = np.array(d["data"][0]["embedding"], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def encode(self, text: str) -> np.ndarray:
        """Encode text to normalized 768D embedding.

        Returns zero vector (not cached) on failure.
        """
        if not text or not isinstance(text, str):
            return np.zeros(self.embedding_dim, dtype=np.float32)
        try:
            return self._raw_embed(text[:512])
        except Exception as e:
            logger.debug(f"LemonadeEmbedEncoder.encode failed: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)


_encoder_instance: LemonadeEmbedEncoder | None = None


def get_lemonade_encoder() -> LemonadeEmbedEncoder:
    """Get or create singleton lemonade encoder."""
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = LemonadeEmbedEncoder()
    return _encoder_instance
