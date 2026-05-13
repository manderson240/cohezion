"""Holographic projection for 12D FLUME trajectory mapping.

Handles the embedding pipeline: text → 2048D latent → 12D axiomatic coordinates.
Supports FLUME VAE semantic encoding (primary) and SHA-256 hash expansion (fallback).

Used by JourneyTracker to convert task descriptions and execution step sequences
into 12D trajectory coordinates.
"""

import hashlib
import logging
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

# Holographic projection constants
HASH_DIMS = 2048
CHUNK_SIZE = 128
AXIOMATIC_DIMS = 12
MAX_CACHE_SIZE = 1000

# Operation-specific 12D modulation profiles.
# Each profile emphasizes different axiomatic dimensions based on operation type.
# Dimension order: novelty, logic, field, spatial, temporal, precipitation,
#                  coherence, efficiency, convergence, smoothness, resonance, harmony
MODULATION_PROFILES: dict[str, np.ndarray] = {
    "generate": np.array([0.9, 0.8, 0.4, 0.3, 0.5, 0.5, 0.6, 0.5, 0.4, 0.3, 0.5, 0.4]),
    "analyze": np.array([0.5, 0.9, 0.8, 0.4, 0.3, 0.4, 0.7, 0.6, 0.5, 0.4, 0.6, 0.5]),
    "search": np.array([0.6, 0.5, 0.4, 0.9, 0.4, 0.3, 0.6, 0.8, 0.4, 0.5, 0.5, 0.4]),
    "transform": np.array([0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.5, 0.5, 0.6, 0.6]),
    "persist": np.array([0.3, 0.4, 0.5, 0.4, 0.9, 0.8, 0.7, 0.5, 0.6, 0.4, 0.5, 0.5]),
}


def _try_load_flume_encoder() -> Any:
    """Auto-initialize FLUME encoder if checkpoint exists. Returns None on any failure."""
    try:
        from cohezion.flume.vae_encoder import FlumeVAEEncoder

        enc = FlumeVAEEncoder(fallback_to_hash=False)
        if enc.enabled:
            logger.info("FLUME semantic encoder active (v%d)", enc._version)
            return enc
    except Exception as e:
        logger.debug("FLUME encoder not loaded: %s", e)
    return None


def _try_load_temporal_encoder() -> Any:
    """Auto-initialize TemporalVAELoader if checkpoint exists. Returns None on failure."""
    try:
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        loader = TemporalVAELoader()
        if loader.enabled:
            logger.info("TemporalVAE encoder loaded from checkpoint")
            return loader
        logger.debug("TemporalVAE checkpoint not found — sequence encoding unavailable")
    except Exception as e:
        logger.debug("TemporalVAELoader not loaded: %s", e)
    return None


def text_to_latent(
    text: str,
    flume_encoder: Any | None = None,
) -> np.ndarray:
    """Generate 2048D embedding from text.

    Uses FLUME encoder (256D tiled to 2048D) when available,
    otherwise falls back to SHA-256 hash expansion.

    Parameters
    ----------
    text : str
        Input text to embed.
    flume_encoder : optional
        FlumeVAEEncoder instance, or None for hash fallback.

    Returns
    -------
    np.ndarray
        2048D normalized array with values in [-1, 1].
    """
    if flume_encoder is not None:
        try:
            flume_256d = flume_encoder.encode(text)
            latent = np.tile(flume_256d, HASH_DIMS // len(flume_256d))
            latent = 2.0 * (latent - np.min(latent)) / (np.max(latent) - np.min(latent) + 1e-8) - 1.0
            return latent
        except Exception as e:
            logger.debug("FLUME encoder failed, falling back to hash: %s", e)

    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()

    latent = np.zeros(HASH_DIMS)
    for i in range(HASH_DIMS):
        byte_idx = i % len(hash_bytes)
        phase = (2.0 * np.pi * i) / HASH_DIMS
        latent[i] = (hash_bytes[byte_idx] / 255.0) * 0.5 + 0.25 * np.sin(phase) + 0.25 * np.cos(phase * 2)

    latent = 2.0 * (latent - np.min(latent)) / (np.max(latent) - np.min(latent) + 1e-8) - 1.0
    return latent


def encode_step_sequence(
    steps: list[dict],
    temporal_encoder: Any | None = None,
    flume_encoder: Any | None = None,
) -> np.ndarray:
    """Encode a sequence of execution steps to 2048D using TemporalEncoder.

    Falls back to encoding the last step's trajectory via text_to_latent
    if TemporalEncoder is unavailable.

    Parameters
    ----------
    steps : list[dict]
        Ordered list of execution step dicts.
    temporal_encoder : optional
        TemporalVAELoader instance, or None.
    flume_encoder : optional
        FlumeVAEEncoder instance, or None.

    Returns
    -------
    np.ndarray
        2048D normalized latent vector.
    """
    if not steps:
        return np.zeros(HASH_DIMS, dtype=np.float32)

    if temporal_encoder is not None:
        try:
            import torch

            from cohezion.flume.trajectory_dataset import _record_to_step

            step_vecs = np.stack([_record_to_step(s) for s in steps])
            tensor = torch.from_numpy(step_vecs).float()
            latent_256d = temporal_encoder.encode_sequence(tensor)
            latent = np.tile(latent_256d, HASH_DIMS // len(latent_256d))
            min_v, max_v = latent.min(), latent.max()
            latent = 2.0 * (latent - min_v) / (max_v - min_v + 1e-8) - 1.0
            return latent.astype(np.float32)
        except Exception as e:
            logger.debug("TemporalEncoder encoding failed, using fallback: %s", e)

    last_task = steps[-1].get("task_description", "")
    if not last_task:
        # Fall back to a deterministic text representation of the entire sequence.
        # Include all fields (including lists via repr) so different step data
        # produces different encodings even when scalar fields are identical.
        last_task = " ".join(repr(sorted(s.items())) for s in steps)
    if last_task:
        return text_to_latent(last_task, flume_encoder=flume_encoder)

    return np.zeros(HASH_DIMS, dtype=np.float32)


def holographic_project(
    latent_2048d: np.ndarray,
    projection_cache: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """Project 2048D embedding to 12D using chunk-mean averaging.

    Parameters
    ----------
    latent_2048d : np.ndarray
        2048D embedding vector.
    projection_cache : dict, optional
        Cache dict for memoization. Modified in-place if provided.

    Returns
    -------
    np.ndarray
        12D normalized vector with values in [0, 1].
    """
    latent_hash = hashlib.sha256(latent_2048d.tobytes()).hexdigest()[:8]

    if projection_cache is not None and latent_hash in projection_cache:
        return projection_cache[latent_hash]

    num_chunks = HASH_DIMS // CHUNK_SIZE
    chunk_means = np.array([np.mean(latent_2048d[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]) for i in range(num_chunks)])

    indices = np.linspace(0, len(chunk_means) - 1, AXIOMATIC_DIMS)
    result_12d = np.interp(indices, np.arange(len(chunk_means)), chunk_means)

    result_12d = (result_12d - np.min(result_12d)) / (np.max(result_12d) - np.min(result_12d) + 1e-8)

    if projection_cache is not None:
        if len(projection_cache) >= MAX_CACHE_SIZE:
            oldest_key = next(iter(projection_cache))
            del projection_cache[oldest_key]
        projection_cache[latent_hash] = result_12d

    return result_12d


def step_to_axiomatic(
    projection_12d: np.ndarray,
    operation_type: str,
    coherence: float,
    efficiency: float,
) -> np.ndarray:
    """Apply operation-specific modulation to 12D projection.

    Parameters
    ----------
    projection_12d : np.ndarray
        12D base projection.
    operation_type : str
        Type of operation (generate, analyze, search, transform, persist).
    coherence : float
        Quality metric (0.0-1.0).
    efficiency : float
        Token efficiency (0.0-1.0).

    Returns
    -------
    np.ndarray
        12D axiomatic vector with values clipped to [0, 1].
    """
    modulation = MODULATION_PROFILES.get(operation_type, MODULATION_PROFILES["transform"])
    quality_weight = 0.5 * coherence + 0.5 * efficiency
    axiomatic = projection_12d * (1.0 - quality_weight) + modulation * quality_weight
    return np.clip(axiomatic, 0.0, 1.0)
