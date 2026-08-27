# src/cohezion/flume/scalar_manifold_coordinates.py
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


__all__ = [
    "ScalarManifoldCoordinates",
    "compute_entropy_density",
    "compute_scalar_metrics",
    "verify_scalar_manifold",
]


@dataclass(frozen=True)
class ScalarManifoldCoordinates:
    """
    Scalar coordinates that complement the 12D FLUME latent vector manifold.

    Attributes:
        coherence_overlap: Coherence overlap scalar C_0.5, bounded to [0.0, 1.0].
        entropy_density: Shannon entropy density S_ent, representing disorder.
        phase_velocity: Phase velocity of the latent manifold dynamics.
        precipitation_scalar: Precipitation/condensation scalar P_precip.
    """

    coherence_overlap: float
    entropy_density: float
    phase_velocity: float
    precipitation_scalar: float


def compute_entropy_density(probabilities: Iterable[float]) -> float:
    """
    Compute the Shannon entropy density from a discrete probability distribution.

    S_ent = -sum(p_i * log(p_i))

    Args:
        probabilities: Iterable of state probabilities (need not be normalized).

    Returns:
        The entropy density as a non-negative scalar.
    """
    probs = [float(p) for p in probabilities if float(p) > 0.0]
    total = sum(probs)
    if total <= 0.0:
        return 0.0

    normalized = (p / total for p in probs)
    return -sum(p * math.log(p) for p in normalized)


def compute_scalar_metrics(
    coherence: float,
    entropy: float,
    velocity: float,
) -> ScalarManifoldCoordinates:
    """
    Compute the scalar manifold coordinates for a given physical state.

    The coherence overlap scalar is defined as:
        C_0.5 = max(0.0, 1.0 - 2.0 * |c - 0.5|)

    The precipitation scalar is modeled as a saturating response of coherent
    phase motion:
        P_precip = C_0.5 * (1 - exp(-max(0.0, velocity)))

    Args:
        coherence: Coherence parameter c, ideally in [0.0, 1.0].
        entropy: Precomputed entropy density S_ent (non-negative).
        velocity: Phase velocity (may be signed; magnitude drives precipitation).

    Returns:
        A frozen ScalarManifoldCoordinates dataclass.
    """
    # Enforce physical bounds on the coherence parameter.
    c = max(0.0, min(1.0, float(coherence)))

    # Coherence overlap scalar around the critical overlap 0.5.
    coherence_overlap = max(0.0, 1.0 - 2.0 * abs(c - 0.5))

    # Entropy density is accepted as a precomputed non-negative scalar.
    entropy_density = max(0.0, float(entropy))

    # Phase velocity is preserved as-is.
    phase_velocity = float(velocity)

    # Precipitation scalar: coherent condensation driven by phase velocity.
    speed = max(0.0, phase_velocity)
    precipitation_scalar = coherence_overlap * (1.0 - math.exp(-speed))

    return ScalarManifoldCoordinates(
        coherence_overlap=coherence_overlap,
        entropy_density=entropy_density,
        phase_velocity=phase_velocity,
        precipitation_scalar=precipitation_scalar,
    )


async def verify_scalar_manifold() -> None:
    """
    Self-verification test ensuring that a coherence of 0.5 maximizes stability.

    Verifies:
      - C_0.5 peaks at 1.0 when coherence == 0.5.
      - Boundary coherences (0.0 and 1.0) yield minimal overlap (0.0).
      - Precipitation scalar is likewise maximized at the critical coherence.
    """
    test_points = [0.0, 0.25, 0.5, 0.75, 1.0]
    metrics = [compute_scalar_metrics(c, entropy=0.5, velocity=1.0) for c in test_points]

    overlaps = [m.coherence_overlap for m in metrics]
    precipitations = [m.precipitation_scalar for m in metrics]

    critical_index = test_points.index(0.5)

    assert max(overlaps) == overlaps[critical_index] == 1.0
    assert min(overlaps) == 0.0
    assert max(precipitations) == precipitations[critical_index]
    assert all(0.0 <= p <= 1.0 for p in precipitations)
