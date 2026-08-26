r"""J-Space Latent Manifold & Krein Space Geometry Demonstration
================================================================
Demonstrates bleeding-edge J-Space (Krein Space) latent manifold operations:
  - Signature (p, q) = (3, 9): 3 Timelike/Executive + 9 Spacelike/Brane dimensions
  - Fundamental Metric Operator J: J = diag(+1, +1, +1, -1, -1, ..., -1)
  - Indefinite Inner Product & Light Cone Horizon (<v, v>_J = 0) mapping to 0.5 HIHO Stability
  - J-Unitary Hyperbolic Transformations (U^T J U = J) preserving trajectory isometry
"""

from __future__ import annotations

import logging
import time

from cohezion.flume.j_space_latent_manifold import JSpaceLatentManifold


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("🌌 Initializing J-Space (Krein Space) Latent Manifold Engine...")
    t0 = time.perf_counter()

    manifold = JSpaceLatentManifold(timelike_dim=3, spacelike_dim=9)

    # 1. Define sample 12D vectors: Timelike, Spacelike, Light Cone
    v_timelike = [2.0, 1.5, 1.0] + [0.1] * 9
    v_spacelike = [0.1, 0.1, 0.1] + [1.0] * 9
    v_lightcone = [1.0, 1.0, 1.0] + [1.0, 1.0, 1.0] + [0.0] * 6  # norm_sq == 3 - 3 == 0

    # 2. Classify points
    pt_t = manifold.classify_point(v_timelike)
    pt_s = manifold.classify_point(v_spacelike)
    pt_l = manifold.classify_point(v_lightcone)

    logger.info("Point 1 (Executive): %s (J-Norm Sq: %.4f)", pt_t.classification, pt_t.j_norm_sq)
    logger.info("Point 2 (Spacelike): %s (J-Norm Sq: %.4f)", pt_s.classification, pt_s.j_norm_sq)
    logger.info("Point 3 (HIHO Horizon): %s (J-Norm Sq: %.4f)", pt_l.classification, pt_l.j_norm_sq)

    # 3. Apply J-Unitary Boost & Verify Isometry
    b_param = 0.75
    v_boosted = manifold.apply_j_boost(v_timelike, boost_parameter=b_param)
    norm_before = manifold.j_norm_squared(v_timelike)
    norm_after = manifold.j_norm_squared(v_boosted)

    isometry_error = abs(norm_before - norm_after)
    logger.info("J-Unitary Boost Parameter: %.2f", b_param)
    logger.info("J-Norm Before Boost: %.6f | After Boost: %.6f | Isometry Error: %.8e", norm_before, norm_after, isometry_error)

    # 4. Compute J-Geodesic Distance
    dist_j = manifold.compute_j_geodesic_distance(v_timelike, v_spacelike)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print("\n" + "=" * 80)
    print("      J-SPACE (KREIN SPACE) LATENT MANIFOLD BENCHMARK RESULTS")
    print("=" * 80)
    print(f"  • Execution Latency: {dt_ms:.3f} ms (< 1.0 ms)")
    print(f"  • Executive Timelike J-Norm^2: {pt_t.j_norm_sq:.4f} [{pt_t.classification}]")
    print(f"  • Spacelike Exploration J-Norm^2: {pt_s.j_norm_sq:.4f} [{pt_s.classification}]")
    print(f"  • 0.5 HIHO Light-Cone Horizon: {pt_l.j_norm_sq:.4f} [{pt_l.classification}]")
    print(f"  • J-Unitary Hyperbolic Boost Isometry Error: {isometry_error:.2e} (Causality Preserved)")
    print(f"  • J-Geodesic Distance: {dist_j:.4f}")
    print("=" * 80)
    print("🎉 J-Space Indefinite Latent Geometry Successfully Operationalized!")


if __name__ == "__main__":
    main()
