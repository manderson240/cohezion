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

import asyncio
import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

LATENT_DIM = 256
SOURCE = "all-MiniLM-L6-v2@1110a243/gauss-proj256-seed7"  # keep in step with MODEL_REVISION
_MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
# Pinned weights revision (hub "main" as of 2026-10-31). A moving "main" would change every stored
# vector silently; bump this together with SOURCE and re-run tests/flume/test_canonical_latent.py.
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
_PROJECTION_SEED = 7
# Network fetch of the weights is OPT-IN (never at first use by accident) and time-bounded.
ALLOW_DOWNLOAD_ENV = "COHEZION_LATENT_ALLOW_DOWNLOAD"
DOWNLOAD_TIMEOUT_ENV = "COHEZION_LATENT_DOWNLOAD_TIMEOUT_S"
_DEFAULT_DOWNLOAD_TIMEOUT_S = 30.0
# A failed load is remembered this long, then retried (not for the process lifetime).
RETRY_AFTER_S = 300.0
# Calibrated on MiniLM-256 (bench, 40 paraphrase / 20 hard-negative / 20 unrelated pairs):
# 0.80 -> 0% unrelated false hits, 20% paraphrase recall, 15% hard-negative false hits.
# Lower thresholds buy recall only by serving hard negatives at the same rate (0.70: 42% / 45%).
# NO cosine threshold separates paraphrases from hard negatives on this encoder: e.g. "Move $100
# from savings to checking" vs its reverse = 0.993, "Should I sell/buy my shares" = 0.939,
# "Do not commit/Commit the secrets" = 0.931, "Open/Close the valve" = 0.911, all above 0.80 and
# the first two above 0.95, while most true paraphrases sit below 0.80. Raising or lowering the
# threshold only trades recall for false hits; it is a precision/recall dial, not a safety gate.
PARAPHRASE_THRESHOLD = 0.80


class TextLatentUnavailable(RuntimeError):  # noqa: N818 - name is the cross-repo contract
    """No real text encoder is available. Never answer with a substitute vector."""


# What a loaded backend raises at INFERENCE time: torch/allocator/tokenizer failures are
# RuntimeError ("DefaultCPUAllocator: can't allocate memory", "Already borrowed"), MemoryError and
# OSError (device/mmap), ValueError (tokenizer rejecting a value). They become the explicit
# "unavailable" state for this call only; programming errors (TypeError, AttributeError, ...)
# still propagate.
_INFERENCE_ERRORS = (RuntimeError, MemoryError, OSError, ValueError)


def _download_timeout() -> float:
    try:
        return float(os.environ.get(DOWNLOAD_TIMEOUT_ENV, _DEFAULT_DOWNLOAD_TIMEOUT_S))
    except ValueError:
        return _DEFAULT_DOWNLOAD_TIMEOUT_S


def _resolve_snapshot() -> str:
    """Local path of the pinned snapshot. Cache only unless the download is opted in.

    ``local_files_only=True`` never touches the network, so an offline box fails in milliseconds
    instead of retrying for 23-83 s. (Loading by bare model name under HF_HUB_OFFLINE=1 also fails
    on this stack with "Unrecognized processing class"; loading from the resolved path works.)
    """
    from huggingface_hub import snapshot_download

    try:
        return str(snapshot_download(_MODEL_REPO, revision=MODEL_REVISION, local_files_only=True))
    except Exception as exc:
        if os.environ.get(ALLOW_DOWNLOAD_ENV) != "1":
            raise OSError(
                f"{_MODEL_REPO}@{MODEL_REVISION[:8]} not in the local HF cache and download is "
                f"not enabled (set {ALLOW_DOWNLOAD_ENV}=1 to fetch once): {exc}"
            ) from exc

    box: dict[str, object] = {}

    def _fetch() -> None:
        try:
            box["path"] = str(
                snapshot_download(_MODEL_REPO, revision=MODEL_REVISION, etag_timeout=5)
            )
        except Exception as exc:  # reported through the join below
            box["error"] = exc

    worker = threading.Thread(target=_fetch, name="latent-weights-fetch", daemon=True)
    worker.start()
    worker.join(_download_timeout())
    if "path" in box:
        return str(box["path"])
    raise OSError(
        f"weights download failed or timed out ({_download_timeout()}s): {box.get('error')}"
    )


def _load_minilm() -> Callable[[str], np.ndarray]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(_resolve_snapshot(), device="cpu")
    max_tokens = int(model.max_seq_length)
    tokenizer = model.tokenizer

    # The HF fast tokenizer is a Rust object that raises RuntimeError("Already borrowed") when
    # two threads use it at once, and model.encode and count_tokens share it. One lock covers both.
    infer_lock = threading.Lock()

    def embed(text: str) -> np.ndarray:
        with infer_lock:
            return np.asarray(model.encode(text), dtype=np.float32)

    def count_tokens(text: str) -> int:
        with infer_lock:
            return len(tokenizer(text, add_special_tokens=True)["input_ids"])

    # The model silently truncates input past max_tokens; callers must not rely on the tail.
    embed.max_tokens = max_tokens  # type: ignore[attr-defined]
    embed.count_tokens = count_tokens  # type: ignore[attr-defined]
    return embed


class CanonicalTextLatent:
    """Lazy, thread-safe text -> 256-d unit vector."""

    def __init__(self, embed_loader: Callable[[], Callable[[str], np.ndarray]] | None = None):
        self._loader = embed_loader or _load_minilm
        self._embed: Callable[[str], np.ndarray] | None = None
        self._error: str | None = None
        self._error_at = 0.0
        self.skipped_calls = 0
        self._skip_logged_at = -RETRY_AFTER_S  # first skip always logs
        self._proj: np.ndarray | None = None
        self._lock = threading.Lock()

    source = SOURCE
    dim = LATENT_DIM

    def _ensure(self) -> Callable[[str], np.ndarray]:
        if self._embed is not None:
            return self._embed
        with self._lock:
            if self._embed is None:
                if self._error is not None and time.monotonic() - self._error_at < RETRY_AFTER_S:
                    raise TextLatentUnavailable(self._error)
                try:
                    self._embed = self._loader()
                    self._error = None
                except Exception as exc:  # converted to the explicit state
                    self._error = f"{type(exc).__name__}: {exc}"
                    self._error_at = time.monotonic()
                    logger.warning("canonical text latent unavailable (%s)", self._error)
                    raise TextLatentUnavailable(self._error) from exc
        return self._embed

    def _infer(self, fn: Callable[[str], Any], text: str) -> Any:
        """Run one backend call; an inference-time failure becomes ``TextLatentUnavailable``.

        ``_ensure()`` is resolved by the caller OUTSIDE this guard (its own unavailable error is
        already explicit), and the encoder is NOT marked dead: a transient OOM or "Already
        borrowed" must not disable the latent for RETRY_AFTER_S. Never falls back to a hash vector.
        """
        try:
            return fn(text)
        except TextLatentUnavailable:
            raise
        except _INFERENCE_ERRORS as exc:
            logger.warning(
                "text latent backend failed at inference (%s: %s)", type(exc).__name__, exc
            )
            raise TextLatentUnavailable(f"inference failed: {type(exc).__name__}: {exc}") from exc

    def encode(self, text: str) -> np.ndarray:
        """Return a unit-norm float32 vector of exactly LATENT_DIM, or raise.

        ``text`` must be a ``str`` (TypeError otherwise): a list or other value reaches the
        backend as a batch and would return a flattened mix at another width.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        embed = self._ensure()
        raw = np.asarray(self._infer(embed, text), dtype=np.float32).reshape(-1)
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

    async def aencode(self, text: str) -> np.ndarray:
        """``encode`` off the event loop (the first call loads weights: seconds, not ms)."""
        return await asyncio.to_thread(self.encode, text)

    @property
    def max_tokens(self) -> int | None:
        """Backend input limit in tokens (inputs beyond it are silently truncated), if known."""
        return getattr(self._embed, "max_tokens", None)

    def exceeds_token_limit(self, text: str) -> bool:
        """True when ``text`` is longer than the backend's input window (its tail is ignored).

        Unknown (no counter on the backend) is reported as False; the real backend always has one.
        """
        counter = getattr(self._ensure(), "count_tokens", None)
        limit = self.max_tokens
        return bool(counter and limit and self._infer(counter, text) > limit)

    def encode_or_none(self, text: str, *, strict_window: bool = False) -> np.ndarray | None:
        """``encode`` or None. A None is never silent: skipped calls are counted and a warning is
        logged at most once per RETRY_AFTER_S, so empty ``flume_state``/``z_vector`` fields and
        skipped cache tiers downstream are traceable to this cause.

        ``strict_window=True`` is for callers that use the vector as an IDENTITY (cache keys): a
        text longer than the backend window is reported as None instead of being embedded from
        its head alone, since two different long texts sharing a head would collide at cosine 1.0.
        The default stays False so non-identity callers keep embedding long contexts.

        Returns None (never raises) for an unavailable backend, an inference-time backend
        failure, and a non-``str`` input (callers pass free-form context; None means "no latent").
        """
        try:
            if not isinstance(text, str):
                raise TextLatentUnavailable(f"input is {type(text).__name__}, not str")
            if strict_window and self.exceeds_token_limit(text):
                raise TextLatentUnavailable(
                    f"text exceeds the encoder window ({self.max_tokens} tokens)"
                )
            return self.encode(text)
        except TextLatentUnavailable as exc:
            self.skipped_calls += 1
            now = time.monotonic()
            if now - self._skip_logged_at >= RETRY_AFTER_S:
                self._skip_logged_at = now
                logger.warning(
                    "text latent unavailable: %d call(s) returned None so far (%s)",
                    self.skipped_calls,
                    exc,
                )
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
