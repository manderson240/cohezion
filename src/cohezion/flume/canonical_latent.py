"""The one canonical text latent: fixed width, explicit provenance, no silent fallback.

Chosen by measurement (scripts/ops/flume_latent_candidate_bench.py over
tests/fixtures/flume_latent_pairs.py): all-MiniLM-L6-v2, projected 384 -> 256 with a fixed
seeded Gaussian map. The trained FLUME ep21_distilled head is NOT used: it needs nomic
vectors as input and the nomic arm could not be scored (UNKNOWN), so wiring it would be
unmeasured. The projection is deterministic, so the width never depends on router state.

When the model cannot be loaded, ``encode`` raises ``TextLatentUnavailable``. It never
returns a hash vector or a vector of another width; callers must treat the exception as an
explicit "no latent" state (cache becomes a no-op, journey metadata omits the vector).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np


logger = logging.getLogger(__name__)

LATENT_DIM = 256
SOURCE = "all-MiniLM-L6-v2/gauss-proj256-seed7"
_MODEL_NAME = "all-MiniLM-L6-v2"
_PROJECTION_SEED = 7
# Calibrated on MiniLM-256 (bench, 40 paraphrase / 20 hard-negative / 20 unrelated pairs):
# 0.80 -> 0% unrelated false hits, 20% paraphrase recall, 15% hard-negative false hits.
# Lower thresholds buy recall only by serving hard negatives at the same rate (0.70: 42% / 45%).
PARAPHRASE_THRESHOLD = 0.80


class TextLatentUnavailable(RuntimeError):  # noqa: N818 - name is the cross-repo contract
    """No real text encoder is available. Never answer with a substitute vector."""


def _load_minilm() -> Callable[[str], np.ndarray]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(_MODEL_NAME, device="cpu")

    def embed(text: str) -> np.ndarray:
        return np.asarray(model.encode(text), dtype=np.float32)

    return embed


class CanonicalTextLatent:
    """Lazy, thread-safe text -> 256-d unit vector."""

    def __init__(self, embed_loader: Callable[[], Callable[[str], np.ndarray]] | None = None):
        self._loader = embed_loader or _load_minilm
        self._embed: Callable[[str], np.ndarray] | None = None
        self._error: str | None = None
        self._proj: np.ndarray | None = None
        self._lock = threading.Lock()

    source = SOURCE
    dim = LATENT_DIM

    def _ensure(self) -> Callable[[str], np.ndarray]:
        if self._embed is not None:
            return self._embed
        with self._lock:
            if self._embed is None:
                if self._error is not None:
                    raise TextLatentUnavailable(self._error)
                try:
                    self._embed = self._loader()
                except Exception as exc:  # converted to the explicit state
                    self._error = f"{type(exc).__name__}: {exc}"
                    logger.warning("canonical text latent unavailable (%s)", self._error)
                    raise TextLatentUnavailable(self._error) from exc
        return self._embed

    def encode(self, text: str) -> np.ndarray:
        """Return a unit-norm float32 vector of exactly LATENT_DIM, or raise."""
        raw = np.asarray(self._ensure()(text), dtype=np.float32).reshape(-1)
        if not np.isfinite(raw).all() or float(np.linalg.norm(raw)) < 1e-6:
            raise TextLatentUnavailable("encoder returned a zero or non-finite vector")
        if self._proj is None or self._proj.shape[0] != raw.shape[0]:
            rng = np.random.default_rng(_PROJECTION_SEED)
            self._proj = rng.standard_normal((raw.shape[0], LATENT_DIM)).astype(
                np.float32
            ) / np.sqrt(LATENT_DIM)
        z = (raw / np.linalg.norm(raw)) @ self._proj
        out: np.ndarray = (z / np.linalg.norm(z)).astype(np.float32)
        return out

    def encode_or_none(self, text: str) -> np.ndarray | None:
        try:
            return self.encode(text)
        except TextLatentUnavailable:
            return None

    def is_available(self) -> bool:
        try:
            self._ensure()
        except TextLatentUnavailable:
            return False
        return True

    @property
    def enabled(self) -> bool:
        return self.is_available()
