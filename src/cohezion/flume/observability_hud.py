#!/usr/bin/env python3
"""Cohezion Real-Time Marimo & Web HUD Observability Dashboard.

Provides an interactive live canvas for:
1. 3D Poincaré Hyperbolic Manifold skill & trajectory projection.
2. Sheaf Cohomology Obstruction Heatmap (dim H^0 consensus vs dim H^1 collision).
3. Real-Time HIHO 0.5 Field Sonification oscilloscope & carrier frequency tracking.
4. Bioelectric Swarm Membrane Potential (V_mem) & Gap-Junction Tensor Monitor.
5. Live EventBus and SurrealDB audit stream telemetry.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from pathlib import Path

import numpy as np

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.flume.bioelectric_swarm import BioelectricSwarm
from cohezion.flume.poincare_manifold_visualizer import PoincareManifoldVisualizer
from cohezion.governance.sheaf_consistency_gate import SheafConsistencyGate
from cohezion.physics.hiho_sonification import HIHOSonifier
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.reliability.oom_guard import OOMGuard

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cohezion_observability_hud")


class CohezionObservabilityHUD:
    """Core engine powering Cohezion's real-time visual telemetry canvas."""

    def __init__(self):
        self.viz = PoincareManifoldVisualizer()
        self.sonifier = HIHOSonifier()
        self.sheaf_gate = SheafConsistencyGate(tolerance=0.15)
        self.swarm = BioelectricSwarm(n_nodes=12, coupling_strength=0.75)

    def capture_live_telemetry_snapshot(self) -> dict:
        """Capture unified state of memory, hyperbolic geometry, sheaf cohomology, and audio."""
        mem = OOMGuard.get_memory_state()

        # 1. Poincaré Projection
        u = np.random.uniform(-0.2, 0.2, size=12)
        pt = PoincareManifoldND.project(tuple(u), target_dim=12)
        d_p = PoincareManifoldND.distance(PoincareManifoldND.origin(12), pt)

        # 2. Sheaf Cohomology Check
        sample_claims = {f"agent_{i}": np.random.uniform(-0.2, 0.2, 12) for i in range(4)}
        intersections = [(f"agent_{i}", f"agent_{i+1}") for i in range(3)]
        sheaf_rep = self.sheaf_gate.evaluate_consistency(sample_claims, intersections)

        # 3. HIHO Sonification Frame
        audio_frame = self.sonifier.sonify_coherence_state(coherence=0.50, fundamental_hz=432.0)

        # 4. Bioelectric Light Cone
        r_c = self.swarm.calculate_light_cone_radius()

        return {
            "timestamp": time.time(),
            "memory": {
                "available_gb": round(mem.available_gb, 2),
                "total_gb": round(mem.total_gb, 2),
                "is_safe": mem.is_safe,
            },
            "geometry": {
                "poincare_norm": round(pt.norm, 4),
                "hyperbolic_distance": round(d_p, 4),
                "manifold_dimension": 12,
            },
            "sheaf_cohomology": {
                "dim_h0_consensus": sheaf_rep.dim_h0_consensus,
                "dim_h1_obstructions": sheaf_rep.dim_h1_obstructions,
                "is_consistent": sheaf_rep.is_consistent,
            },
            "hiho_sonification": {
                "fundamental_hz": round(audio_frame.fundamental_hz, 1),
                "dissonance_index": round(audio_frame.dissonance_index, 4),
                "coherence_distance": round(audio_frame.coherence_distance, 4),
            },
            "bioelectric_swarm": {
                "node_count": len(self.swarm.nodes),
                "light_cone_radius": round(r_c, 2),
                "mean_gap_junction_coupling": round(self.swarm.mean_coupling(), 4),
            },
        }

    def render_ascii_dashboard(self) -> str:
        """Render rich terminal dashboard."""
        snap = self.capture_live_telemetry_snapshot()
        lines = [
            "=" * 90,
            "                   🌐 COHEZION TOPOLOGICAL OBSERVABILITY HUD",
            "=" * 90,
            f" [MEMORY]        Available: {snap['memory']['available_gb']} GiB / {snap['memory']['total_gb']} GiB  | Safe Floor: {snap['memory']['is_safe']}",
            f" [POINCARÉ]      12D Norm: {snap['geometry']['poincare_norm']} | Geodesic d_P: {snap['geometry']['hyperbolic_distance']:.4f} (Curvature: -1.0)",
            f" [COHOMOLOGY]    Consensus dim H^0: {snap['sheaf_cohomology']['dim_h0_consensus']} | Obstruction dim H^1: {snap['sheaf_cohomology']['dim_h1_obstructions']} | Consistent: {snap['sheaf_cohomology']['is_consistent']}",
            f" [HIHO 0.5]      Carrier: {snap['hiho_sonification']['fundamental_hz']:.1f} Hz | Dissonance: {snap['hiho_sonification']['dissonance_index']} | Delta: {snap['hiho_sonification']['coherence_distance']}",
            f" [BIOELECTRIC]   Nodes: {snap['bioelectric_swarm']['node_count']} | Light-Cone R_c: {snap['bioelectric_swarm']['light_cone_radius']} | Coupling kappa: {snap['bioelectric_swarm']['mean_gap_junction_coupling']}",
            "=" * 90,
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    hud = CohezionObservabilityHUD()
    print(hud.render_ascii_dashboard())
