"""SkillStateEncoder — encode MGPO skill state + RubricVerdict into 256D vectors.

256D layout (manifold-compatible with ExperienceEncoder):
  [0:12]   12D trajectory (zeros unless JourneyTracker provides one)
  [12]     mgpo_weight (MGPO bell curve weight, 0–1)
  [13]     success_rate (0–1)
  [14]     rubric_passed (1.0=passed, 0.0=failed)
  [15]     invocation_count_norm (log-scaled, clipped to [0,1])
  [16:24]  reserved scalar metrics (zeros)
  [24:29]  5D operation type one-hot
  [29:256] 227D semantic fingerprint (SHA-256 of skill_name + context)
"""

from __future__ import annotations

import hashlib
import math

import numpy as np

_TOTAL_DIM = 256
_TRAJECTORY_END = 12
_MGPO_WEIGHT_DIM = 12
_SUCCESS_RATE_DIM = 13
_RUBRIC_PASSED_DIM = 14
_INVOCATION_COUNT_DIM = 15
_OP_TYPE_START = 24
_FINGERPRINT_START = 29
_FINGERPRINT_DIM = 227  # 256 - 29

_OPERATION_TYPES = ("generate", "analyze", "search", "transform", "persist")


class SkillStateEncoder:
    """Encode MGPO skill state and RubricVerdict into 256D float32 vectors.

    The encoding is fully deterministic: same inputs always produce the
    same vector, enabling stable nearest-neighbour retrieval on the
    FLUME manifold.
    """

    def encode_skill(
        self,
        skill_name: str,
        *,
        mgpo_weight: float,
        success_rate: float,
        invocation_count: int = 0,
        trajectory: list | np.ndarray | None = None,
        operation_type: str = "",
        context: str = "",
    ) -> np.ndarray:
        """Encode skill state without a rubric verdict (rubric_passed defaults to 1.0)."""
        return self._encode(
            skill_name=skill_name,
            mgpo_weight=mgpo_weight,
            success_rate=success_rate,
            rubric_passed=1.0,
            invocation_count=invocation_count,
            trajectory=trajectory,
            operation_type=operation_type,
            context=context,
        )

    def encode_rubric_verdict(
        self,
        skill_name: str,
        verdict: object,
        *,
        mgpo_weight: float,
        success_rate: float,
        invocation_count: int = 0,
        trajectory: list | np.ndarray | None = None,
        operation_type: str = "",
        context: str = "",
    ) -> np.ndarray:
        """Encode skill state with a RubricVerdict (dim 14 reflects verdict.passed)."""
        rubric_passed = 1.0 if getattr(verdict, "passed", True) else 0.0
        return self._encode(
            skill_name=skill_name,
            mgpo_weight=mgpo_weight,
            success_rate=success_rate,
            rubric_passed=rubric_passed,
            invocation_count=invocation_count,
            trajectory=trajectory,
            operation_type=operation_type,
            context=context,
        )

    # ── internal ──────────────────────────────────────────────────────────

    def _encode(
        self,
        skill_name: str,
        mgpo_weight: float,
        success_rate: float,
        rubric_passed: float,
        invocation_count: int,
        trajectory: list | np.ndarray | None,
        operation_type: str,
        context: str,
    ) -> np.ndarray:
        vec = np.zeros(_TOTAL_DIM, dtype=np.float32)

        # --- Dims [0:12]: trajectory ---
        if trajectory is not None:
            traj_arr = np.asarray(trajectory, dtype=np.float32).ravel()
            n = min(len(traj_arr), _TRAJECTORY_END)
            vec[:n] = traj_arr[:n]

        # --- Dims [12:16]: MGPO-specific scalars ---
        vec[_MGPO_WEIGHT_DIM] = float(np.clip(mgpo_weight, 0.0, 1.0))
        vec[_SUCCESS_RATE_DIM] = float(np.clip(success_rate, 0.0, 1.0))
        vec[_RUBRIC_PASSED_DIM] = float(np.clip(rubric_passed, 0.0, 1.0))
        invocation_norm = math.log1p(float(invocation_count)) / 10.0
        vec[_INVOCATION_COUNT_DIM] = float(np.clip(invocation_norm, 0.0, 1.0))

        # --- Dims [16:24]: reserved (zeros) ---

        # --- Dims [24:29]: operation type one-hot ---
        op = operation_type.lower() if isinstance(operation_type, str) else ""
        if op in _OPERATION_TYPES:
            vec[_OP_TYPE_START + _OPERATION_TYPES.index(op)] = 1.0

        # --- Dims [29:256]: semantic fingerprint ---
        fingerprint_key = f"{skill_name}|{context}"
        vec[_FINGERPRINT_START:] = _sha256_expand(fingerprint_key, _FINGERPRINT_DIM)

        return vec


def _sha256_expand(text: str, dim: int) -> np.ndarray:
    """Deterministic SHA-256 expansion to ``dim`` float32 values in [0, 1]."""
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    out = np.zeros(dim, dtype=np.float32)
    for i in range(dim):
        byte_val = hash_bytes[i % len(hash_bytes)]
        phase = (2.0 * math.pi * i) / dim
        out[i] = (
            0.5 + (byte_val / 255.0 - 0.5) * 0.6 + 0.1 * math.sin(phase) + 0.1 * math.cos(phase * 2)
        )
    return out
