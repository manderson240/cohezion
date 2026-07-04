"""vacuum_topology.py — FLUME latent → vacuum topology classifier.

Maps 12D FLUME trajectory points to quantum field theory analogues:

  * instanton  — saddle-point tunnel event: rapid sign-alternating transition
                 between meta-stable attractors; high oscillatory energy
  * soliton    — stable topological defect: energy localized in a few dims,
                 persistent, non-dissipating coherent excitation
  * trivial    — background vacuum: low-energy equilibrium, uniform distribution

Classification is cosine similarity to three unit-norm prototype cluster centers
in R^12.  Pure numpy; no torch/scipy required.

Integration with JourneyTracker:
    Each trajectory point from track_execution() carries a ``vacuum_topology``
    key in its metadata dict, e.g.:
        {"label": "soliton", "confidence": 0.73, "l2_norm": 1.12}
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

_DIMS = 12
_SQRT12 = math.sqrt(_DIMS)

# ---------------------------------------------------------------------------
# Prototype cluster centres (unit-norm 12D vectors)
# ---------------------------------------------------------------------------

# trivial vacuum: uniform distribution — every axiomatic dimension equally excited
# Analogy: the Minkowski vacuum; no preferred mode, homogeneous background.
_TRIVIAL_CENTER: np.ndarray = np.full(_DIMS, 1.0 / _SQRT12, dtype=np.float64)

# soliton: energy localized in first 4 dims, zero elsewhere
# norm = sqrt(4 * 0.25) = 1 ✓
# Analogy: kink / vortex — spatially confined topological defect.
_SOLITON_CENTER: np.ndarray = np.array(
    [0.5, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64
)

# instanton: alternating ±1/√12 sign pattern
# Analogy: BPST instanton / bounce solution — maximally oscillatory in theory space,
# encoding a tunnelling event between two topological sectors.
_INSTANTON_CENTER: np.ndarray = np.array(
    [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0], dtype=np.float64
) / _SQRT12

# Verify unit norms at import time (silent: just log if off)
for _name, _ctr in [("trivial", _TRIVIAL_CENTER), ("soliton", _SOLITON_CENTER), ("instanton", _INSTANTON_CENTER)]:
    _norm = float(np.linalg.norm(_ctr))
    if abs(_norm - 1.0) > 1e-9:
        logger.warning("Prototype '%s' is not unit-norm (%.6f) — classifier may misbehave", _name, _norm)

VacuumClass = Literal["instanton", "soliton", "trivial"]

# Harness invariant (VT1): classify_point() must always return a member of this set
VACUUM_LABELS: frozenset[str] = frozenset({"instanton", "soliton", "trivial"})


@dataclass
class VacuumLabel:
    """Result of classifying a 12D FLUME latent point."""

    label: VacuumClass
    confidence: float          # cosine similarity to winning prototype [0, 1]
    l2_norm: float             # raw magnitude of the input vector
    runner_up: VacuumClass | None = None
    runner_up_confidence: float | None = None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "l2_norm": round(self.l2_norm, 4),
            "runner_up": self.runner_up,
            "runner_up_confidence": round(self.runner_up_confidence, 4)
            if self.runner_up_confidence is not None
            else None,
        }


class VacuumTopologyClassifier:
    """Classify 12D FLUME latent points as instanton / soliton / trivial.

    Usage::

        clf = VacuumTopologyClassifier()
        label = clf.classify(point.dimensions)
        print(label.label, label.confidence)

    The classifier is stateless and thread-safe.  Construct once and reuse.
    """

    # Vectors with L2 norm below this are definitively trivial (near-zero energy).
    TRIVIAL_NORM_GATE: float = 0.05

    def classify(self, point_12d: np.ndarray) -> VacuumLabel:
        """Classify a single 12D trajectory point.

        Args:
            point_12d: 12D numpy array (FLUME axiomatic coordinates).

        Returns:
            VacuumLabel with label, confidence, and runner-up info.
        """
        v = np.asarray(point_12d, dtype=np.float64).ravel()
        if v.shape[0] != _DIMS:
            raise ValueError(f"Expected {_DIMS}D vector, got shape {v.shape}")

        norm = float(np.linalg.norm(v))

        # Gate: near-zero energy → definitively trivial (no direction to compare)
        if norm < self.TRIVIAL_NORM_GATE:
            return VacuumLabel(label="trivial", confidence=1.0, l2_norm=norm)

        v_hat = v / norm

        # Cosine similarities (can be negative; clip to 0 for confidence display)
        cos_trivial = float(np.dot(v_hat, _TRIVIAL_CENTER))
        cos_soliton = float(np.dot(v_hat, _SOLITON_CENTER))
        cos_instanton = float(np.dot(v_hat, _INSTANTON_CENTER))

        scores: dict[VacuumClass, float] = {
            "trivial": max(0.0, cos_trivial),
            "soliton": max(0.0, cos_soliton),
            "instanton": max(0.0, cos_instanton),
        }

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_label, best_score = ranked[0]
        second_label, second_score = ranked[1]

        return VacuumLabel(
            label=best_label,
            confidence=best_score,
            l2_norm=norm,
            runner_up=second_label if second_score > 0.0 else None,
            runner_up_confidence=second_score if second_score > 0.0 else None,
        )

    def classify_many(self, points: list[np.ndarray]) -> list[VacuumLabel]:
        """Batch classify a list of 12D vectors."""
        return [self.classify(p) for p in points]

    def topological_diversity(self, points: list[np.ndarray]) -> dict:
        """Compute label distribution over a trajectory window.

        Returns fraction of each class plus a diversity score in [0, 1]
        (0 = all same class, 1 = uniform distribution across classes).
        """
        if not points:
            return {"trivial": 0.0, "soliton": 0.0, "instanton": 0.0, "diversity": 0.0}

        labels = [self.classify(p).label for p in points]
        n = len(labels)
        counts = {c: labels.count(c) for c in ("trivial", "soliton", "instanton")}
        fracs = {c: counts[c] / n for c in counts}

        # Shannon diversity normalised to [0, 1] over 3 classes
        entropy = 0.0
        for f in fracs.values():
            if f > 0.0:
                entropy -= f * math.log(f)
        max_entropy = math.log(3)
        fracs["diversity"] = round(entropy / max_entropy, 4)
        return fracs


# Module-level singleton — stateless, safe to share
_CLASSIFIER: VacuumTopologyClassifier | None = None


def classify_point(point_12d: np.ndarray) -> VacuumLabel:
    """Convenience function using the module singleton classifier."""
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = VacuumTopologyClassifier()
    return _CLASSIFIER.classify(point_12d)
