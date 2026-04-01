"""Seed-based universe generation.

Each universe is defined by a unique FlumePhysics weight configuration.
Deterministic: same seed always produces identical weights.
"""

from __future__ import annotations

import logging

import numpy as np

from cohezion.mass_sim.config import UniverseSpec


logger = logging.getLogger(__name__)


def _import_flume_physics():
    """Import FlumePhysics from Rust extension, fall back to pure-Python."""
    try:
        from cohezion_core.cohezion_core_rs import FlumePhysics

        logger.info("Using Rust FlumePhysics (fast path)")
        return FlumePhysics
    except ImportError:
        from cohezion.mass_sim.flume_physics_py import FlumePhysicsPy

        logger.info("cohezion_core_rs unavailable, using pure-Python FlumePhysics")
        return FlumePhysicsPy


class UniverseFactory:
    """Generate FlumePhysics instances from seed-based weight configurations."""

    @staticmethod
    def create(
        spec: UniverseSpec,
        delta_scale: float = 0.01,
        hiho_damping: float = 0.05,
        weights: dict[str, np.ndarray] | None = None,
    ):
        """Create a FlumePhysics instance.

        Parameters
        ----------
        spec : UniverseSpec
            Universe weight configuration.
        delta_scale : float
            Scale factor for state updates per epoch.
        hiho_damping : float
            HIHO attractor strength toward 0.5 equilibrium.
        weights : dict[str, np.ndarray] | None
            Pre-trained weights with keys: w1, b1, w2, b2, gamma, beta.
            If None, uses Xavier initialization from seed.
        """
        FlumePhysics = _import_flume_physics()

        if weights is not None:
            w1 = weights["w1"].astype(np.float32)
            b1 = weights["b1"].astype(np.float32)
            w2 = weights["w2"].astype(np.float32)
            b2 = weights["b2"].astype(np.float32)
            gamma = weights["gamma"].astype(np.float32)
            beta = weights["beta"].astype(np.float32)
            logger.info(
                "Creating FlumePhysics with pre-trained weights (w1 norm=%.3f, w2 norm=%.3f)",
                np.linalg.norm(w1),
                np.linalg.norm(w2),
            )
        else:
            rng = np.random.default_rng(spec.seed)

            # Xavier initialization for stable gradient flow
            scale_w1 = np.sqrt(2.0 / (spec.z_dim + spec.hidden_dim))
            w1 = rng.normal(0, scale_w1, (spec.hidden_dim, spec.z_dim)).astype(np.float32)
            b1 = np.zeros(spec.hidden_dim, dtype=np.float32)

            scale_w2 = np.sqrt(2.0 / (spec.hidden_dim + spec.z_dim))
            w2 = rng.normal(0, scale_w2, (spec.z_dim, spec.hidden_dim)).astype(np.float32)
            b2 = np.full(spec.z_dim, 0.02, dtype=np.float32)

            # LayerNorm: gamma=1 (scale), beta=0.5 (shift output to HIHO target)
            gamma = np.ones(spec.hidden_dim, dtype=np.float32)
            beta = np.full(spec.hidden_dim, 0.5, dtype=np.float32)

        return FlumePhysics(
            w1,
            b1,
            w2,
            b2,
            gamma,
            beta,
            delta_scale=delta_scale,
            hiho_damping=hiho_damping,
        )

    @staticmethod
    def create_batch(seeds: list[int], z_dim: int = 256, hidden_dim: int = 512) -> list:
        """Create multiple universe physics engines."""
        return [
            UniverseFactory.create(UniverseSpec(f"universe_{s}", s, z_dim, hidden_dim))
            for s in seeds
        ]

    @staticmethod
    def weight_fingerprint(spec: UniverseSpec) -> dict:
        """Compute weight norms for a universe spec (without creating FlumePhysics)."""
        rng = np.random.default_rng(spec.seed)
        scale_w1 = np.sqrt(2.0 / (spec.z_dim + spec.hidden_dim))
        w1 = rng.normal(0, scale_w1, (spec.hidden_dim, spec.z_dim)).astype(np.float32)
        scale_w2 = np.sqrt(2.0 / (spec.hidden_dim + spec.z_dim))
        w2 = rng.normal(0, scale_w2, (spec.z_dim, spec.hidden_dim)).astype(np.float32)
        return {
            "seed": spec.seed,
            "w1_frobenius": float(np.linalg.norm(w1)),
            "w2_frobenius": float(np.linalg.norm(w2)),
            "w1_spectral": float(np.linalg.norm(w1, ord=2)),
            "w2_spectral": float(np.linalg.norm(w2, ord=2)),
        }
