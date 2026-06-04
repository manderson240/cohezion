"""
FLUME vacuum encoder — encodes agentic execution text as 256D vacuum objects.

Pipeline: text → nomic-embed-text-v2-moe (768D, port 13305) → FLUME VAE ep21-distilled → 256D z_vector

The z_vector is the 'vacuum object' representation of an agentic journey. Semantically similar
journeys (two NPU math queries) cluster close in latent space (dist≈0.025); topologically
distinct journey types are separated (NPU routing vs code generation: dist≈0.168).

These are 'exotic vacuum objects': stable attractor regions in the FLUME manifold that
correspond to fundamentally different phases of agentic behavior.

Validated in exp_YYYY3 (2026-05-30, round 15). Wired into orchestrator telemetry via exp_ZZZZ3.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)

_CHECKPOINT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "data"
    / "flume"
    / "checkpoints"
    / "flume_vae_ep21_distilled.pt"
)
_NOMIC_URL = "http://localhost:13305/v1/embeddings"
_NOMIC_MODEL = "nomic-embed-text-v2-moe-GGUF"
_LATENT_DIM = 256

_singleton: _VacuumEncoder | None = None


def _hash_fallback(text: str) -> np.ndarray:
    """Deterministic 256D fallback when nomic-embed or checkpoint is unavailable."""
    import hashlib

    digest = hashlib.sha256(text.encode()).digest()
    buf = (digest * (_LATENT_DIM // 32 + 1))[:_LATENT_DIM]
    z = np.frombuffer(buf, dtype=np.uint8).astype(np.float32) / 127.5 - 1.0
    n = np.linalg.norm(z)
    return (z / n * 0.38) if n > 1e-8 else z


class _VacuumEncoder:
    """Lazy-loaded singleton: nomic-embed(768D) → FLUME VAE ep21-distilled → 256D mu."""

    def __init__(self) -> None:
        import torch
        import torch.nn as nn

        if not _CHECKPOINT_PATH.exists():
            raise FileNotFoundError(f"FLUME checkpoint not found: {_CHECKPOINT_PATH}")

        ckpt = torch.load(str(_CHECKPOINT_PATH), map_location="cpu", weights_only=True)

        # Architecture from checkpoint weights: 768→384→256 encoder + 256→256 mu_head
        self._net = nn.Sequential(
            nn.Sequential(nn.Linear(768, 384), nn.ReLU(), nn.Linear(384, 256), nn.ReLU()),
            nn.Linear(256, _LATENT_DIM),
        )
        self._net[0].load_state_dict(ckpt["encoder"])
        self._net[1].load_state_dict(ckpt["mu_head"])
        self._net.eval()
        logger.info("VacuumEncoder loaded: 768D→384→256→256D mu (ep21-distilled)")

    async def encode(self, text: str) -> np.ndarray:
        """Encode journey text → 256D z_vector via nomic-embed + FLUME VAE."""
        import httpx
        import torch

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    _NOMIC_URL,
                    json={"model": _NOMIC_MODEL, "input": text[:512]},
                )
                resp.raise_for_status()
                emb = resp.json()["data"][0]["embedding"]
        except Exception as exc:
            logger.debug("nomic-embed unavailable, hash fallback: %s", exc)
            return _hash_fallback(text)

        x = torch.tensor([emb], dtype=torch.float32)
        with torch.no_grad():
            z = self._net(x)[0].numpy()
        return z


def get_vacuum_encoder() -> _VacuumEncoder | None:
    """Return the singleton encoder, loading lazily. Returns None on load failure."""
    global _singleton
    if _singleton is None:
        try:
            _singleton = _VacuumEncoder()
        except Exception as exc:
            logger.debug("VacuumEncoder unavailable: %s", exc)
    return _singleton


async def encode_journey_text(prompt: str, response: str) -> list[float]:
    """Encode a (prompt, response) pair as a 256D vacuum object.

    Returns list[float] suitable for FlumeJourneyEvent.z_vector.
    Falls back to hash-based vector if encoder or nomic-embed is unavailable.
    """
    text = f"prompt: {prompt[:200]} response: {response[:200]}"
    enc = get_vacuum_encoder()
    if enc is None:
        return _hash_fallback(text).tolist()
    try:
        z = await enc.encode(text)
        return z.tolist()
    except Exception as exc:
        logger.debug("encode_journey_text failed, hash fallback: %s", exc)
        return _hash_fallback(text).tolist()


_ATLAS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "flume" / "vacuum_atlas_v1.json"
_atlas_cache: dict | None = None


def load_vacuum_atlas() -> dict | None:
    """Load the persisted vacuum state atlas (phase centroids).

    Returns dict with 'phases' → {'content': {'centroid': list[float], ...}, 'route': ...}
    or None if the atlas file doesn't exist.
    """
    global _atlas_cache
    if _atlas_cache is None and _ATLAS_PATH.exists():
        import json

        with open(_ATLAS_PATH) as f:
            _atlas_cache = json.load(f)
        logger.debug(
            "Vacuum atlas loaded: %d phases, dim=%d",
            len(_atlas_cache["phases"]),
            _atlas_cache["dim"],
        )
    return _atlas_cache


def classify_journey_phase(z_vector: list[float]) -> tuple[str, float]:
    """Classify a 256D z_vector into a vacuum phase using the persisted atlas.

    Returns (phase_name, confidence_margin) where confidence_margin = |d_other - d_self|.
    Returns ('unknown', 0.0) if atlas not available.
    Threshold guidance: margin > 0.02 = high confidence (reliable for full prompt+response pairs),
    0.01-0.02 = medium (treat as soft signal), < 0.01 = abstain (short/ambiguous text).
    """
    atlas = load_vacuum_atlas()
    if atlas is None:
        return ("unknown", 0.0)
    z = np.array(z_vector)
    best_phase = "unknown"
    best_dist = float("inf")
    dists: dict[str, float] = {}
    for phase_name, phase_data in atlas["phases"].items():
        c = np.array(phase_data["centroid"])
        d = float(1.0 - np.dot(z, c) / (np.linalg.norm(z) * np.linalg.norm(c) + 1e-10))
        dists[phase_name] = d
        if d < best_dist:
            best_dist = d
            best_phase = phase_name
    sorted_dists = sorted(dists.values())
    margin = sorted_dists[1] - sorted_dists[0] if len(sorted_dists) >= 2 else 0.0
    return (best_phase, float(margin))
