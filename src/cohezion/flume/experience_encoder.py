"""Encode agentic execution experiences as 256D vectors for FLUME VAE training.

256D encoding scheme:
  [0:12]   12D axiomatic trajectory (from JourneyTracker)
  [12:24]  12 scalar execution metrics
  [24:29]  5 operation type one-hot
  [29:256] 227 semantic fingerprint (deterministic SHA-256 hash expansion)
"""

from __future__ import annotations

import hashlib
import math

import numpy as np


# Dimension layout
_TRAJECTORY_DIM = 12  # dims [0:12]
_METRICS_DIM = 12  # dims [12:24]
_OP_TYPE_DIM = 5  # dims [24:29]
_FINGERPRINT_DIM = 227  # dims [29:256]
TOTAL_DIM = _TRAJECTORY_DIM + _METRICS_DIM + _OP_TYPE_DIM + _FINGERPRINT_DIM  # 256

# Canonical operation types (matches JourneyTracker.OperationType)
OPERATION_TYPES = ("generate", "analyze", "search", "transform", "persist")

# Metric keys in canonical order (dims 12-23)
METRIC_KEYS = (
    "phi_score",
    "anomaly_score",
    "misalignment_score",
    "intent_confidence",
    "duration_s",
    "tokens_used",
    "cache_hit_rate",
    "success",
    "token_efficiency",
    "trajectory_smoothness",
    "trajectory_convergence",
    "cost_usd",
)


class ExperienceEncoder:
    """Encode a single execution experience dict into a 256D float32 vector.

    The encoding is fully deterministic: same input dict always produces
    the same output vector.
    """

    def encode(self, experience: dict) -> np.ndarray:
        """Encode an experience record into a 256D float32 vector.

        Parameters
        ----------
        experience : dict
            Must contain at least one of:
            - ``trajectory``: list/array of 12D floats
            - ``operation_type``: one of OPERATION_TYPES
            Additional scalar metrics are pulled by METRIC_KEYS names.

        Returns
        -------
        np.ndarray
            Shape ``(256,)`` dtype ``float32``.
        """
        vec = np.zeros(TOTAL_DIM, dtype=np.float32)

        # --- Dims [0:12]: 12D trajectory ---
        traj = experience.get("trajectory")
        if traj is not None:
            traj_arr = np.asarray(traj, dtype=np.float32).ravel()
            n = min(len(traj_arr), _TRAJECTORY_DIM)
            vec[:n] = traj_arr[:n]

        # --- Dims [12:24]: scalar execution metrics ---
        for i, key in enumerate(METRIC_KEYS):
            raw = experience.get(key, 0.0)
            val = float(raw) if raw is not None else 0.0
            # Log-scale normalization for duration and tokens
            if key == "duration_s":
                val = math.log1p(val) / 10.0  # log(1+s)/10 → ~0-1 for 0-22000s
            elif key == "tokens_used":
                val = math.log1p(val) / 15.0  # log(1+t)/15 → ~0-1 for 0-3M tokens
            elif key == "cost_usd":
                val = math.log1p(val * 100) / 10.0  # scale cents then log
            # Clamp to [0,1] for bounded metrics
            vec[_TRAJECTORY_DIM + i] = float(np.clip(val, -1.0, 2.0))

        # --- Dims [24:29]: operation type one-hot ---
        op_type = experience.get("operation_type", "")
        if isinstance(op_type, str):
            op_type = op_type.lower()
        if op_type in OPERATION_TYPES:
            idx = OPERATION_TYPES.index(op_type)
            vec[_TRAJECTORY_DIM + _METRICS_DIM + idx] = 1.0

        # --- Dims [29:256]: semantic fingerprint ---
        fingerprint_text = self._build_fingerprint_text(experience)
        vec[_TRAJECTORY_DIM + _METRICS_DIM + _OP_TYPE_DIM :] = self._sha256_expand(fingerprint_text, _FINGERPRINT_DIM)

        return vec

    @staticmethod
    def _build_fingerprint_text(experience: dict) -> str:
        """Build a stable text key from experience metadata for hashing."""
        parts = []
        for key in ("mission_id", "agent_id", "skill_name", "input_preview"):
            val = experience.get(key)
            if val:
                parts.append(str(val))
        return "|".join(parts) if parts else "unknown"

    @staticmethod
    def _sha256_expand(text: str, dim: int) -> np.ndarray:
        """Deterministic hash expansion to ``dim`` floats in [0, 1].

        Same approach as JourneyTracker._text_to_latent: SHA-256 bytes
        cycled with sine-wave modulation for smooth variation.
        """
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        out = np.zeros(dim, dtype=np.float32)
        for i in range(dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            phase = (2.0 * math.pi * i) / dim
            # Center at 0.5: byte_val/255 in [0,1] has mean 0.5; modulation is zero-mean
            out[i] = 0.5 + (byte_val / 255.0 - 0.5) * 0.6 + 0.1 * math.sin(phase) + 0.1 * math.cos(phase * 2)
        return out
