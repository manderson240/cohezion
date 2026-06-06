#!/usr/bin/env python3
"""Cosmogenesis — generate our own universe models and showcase the cosmology.

Drives the real Cohezion SymmetryBreaking cosmogony through its full cooling
chain (the void -> 9 phase transitions -> a precipitated 12D universe), for
several seeds, then pushes each precipitated universe through the Quadrature
Nexus (4-fabric SO(3) gauge) to show its structure.

The cosmogonic chain (from cosmogony.py):
  VOID -> Quadrature -> SO(12) -> SO(3)^4 -> Phase -> U(1)^4 -> Z2^4
       -> HIHO -> COHESION -> Precipitate

Each step breaks a symmetry (Landau order parameter), cooling from T=250 to ~0.
The universe self-organizes toward the HIHO 0.5 equilibrium — the cosmology
DERIVES the coherence attractor rather than assuming it.

Output: a JSON bundle the visual report renders as:
  - the temperature->symmetry phase-transition timeline (cosmology)
  - the order-parameter decay (symmetry breaking)
  - each generated universe's precipitated 12D state through the 4 fabrics
  - a per-universe coherence + Yang-Mills curvature

Run:  PYTHONPATH=<src> python cosmogenesis.py [--universes 6] [--out cosmos.json]
"""

from __future__ import annotations

import argparse
import json
import logging

import numpy as np

from cohezion.physics.cosmogony import SymmetryBreaking
from cohezion.physics.fiber_bundle import FiberBundle, FABRIC_NAMES, FABRIC_SLICES
from cohezion.physics.gauge_theory import FourFabricGauge

logging.disable(logging.INFO)  # cosmogony logs every transition at INFO


def cool_one_universe(universe_id: str, seed: int) -> dict:
    """Cool a single universe from the void to precipitate, capturing the chain."""
    sb = SymmetryBreaking(universe_id=universe_id)
    sb.reset()
    sb._rng = np.random.default_rng(seed)  # seed the precipitation randomness

    # Capture a (T, symmetry, coherence) snapshot as we cool.
    timeline = []
    T_start = sb.temperature
    timeline.append({"T": round(T_start, 1), "symmetry": sb.symmetry.value, "stage": 0})

    for _ in range(60):
        sb.cool(delta_t=4.5)
        st = sb.generate_12d_state()
        coh = round(float(1.0 - min(4.0 * np.var(st), 1.0)), 4)
        timeline.append(
            {
                "T": round(sb.temperature, 2),
                "symmetry": sb.symmetry.value,
                "stage": sb.stage,
                "coherence": coh,
            }
        )

    transitions = [
        {
            "stage": ev.stage,
            "T_c": round(ev.critical_temperature, 1),
            "T": round(ev.actual_temperature, 2),
            "from": ev.from_symmetry.value,
            "to": ev.to_symmetry.value,
            "order_param": round(float(ev.order_parameter_value), 4),
        }
        for ev in sb.state.transitions
    ]

    # The precipitated universe: its final 12D state.
    universe = sb.generate_12d_state()
    return {
        "universe_id": universe_id,
        "seed": seed,
        "final_symmetry": sb.symmetry.value,
        "stages": sb.stage,
        "transitions": transitions,
        "timeline": timeline,
        "state12": [round(float(x), 4) for x in universe],
        "raw_state": universe.tolist(),
    }


def through_quadrature(state12: list[float]) -> dict:
    """Push a precipitated universe through the four-fabric quadrature nexus."""
    state = np.asarray(state12, dtype=np.float64)
    fb = FiberBundle(dim=12, n_fabrics=4)
    decomp = fb.decompose(state)
    gauge = FourFabricGauge()
    ym, is_hiho = gauge.update_and_compute(state, target=0.5)
    fabrics = {}
    for i, name in enumerate(FABRIC_NAMES):
        fabrics[name] = {
            "norm": round(float(decomp.base[i]), 4),
            "raw": [round(float(x), 4) for x in state[FABRIC_SLICES[name]]],
        }
    return {
        "fabrics": fabrics,
        "yang_mills_action": round(float(ym), 6),
        "is_hiho": bool(is_hiho),
        "coherence": round(float(1.0 - min(4.0 * np.var(state), 1.0)), 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universes", type=int, default=6)
    ap.add_argument("--out", default="cosmos.json")
    args = ap.parse_args()

    import cohezion.physics.cosmogony as mod

    print(f"provenance OK: SymmetryBreaking -> {mod.__file__}")
    print(f"cooling {args.universes} universes from the void to precipitate ...\n")

    universes = []
    for i in range(args.universes):
        u = cool_one_universe(f"universe-{i:02d}", seed=100 + i)
        u["quadrature"] = through_quadrature(u["state12"])
        universes.append(u)
        q = u["quadrature"]
        print(
            f"  {u['universe_id']}  {u['stages']} stages -> {u['final_symmetry']:12} "
            f"coherence={q['coherence']:.3f}  S_YM={q['yang_mills_action']:.5f}  "
            f"hiho={q['is_hiho']}"
        )

    # The canonical phase-transition chain (same for all; take the first universe's).
    canonical_chain = universes[0]["transitions"]

    bundle = {
        "fabric_names": FABRIC_NAMES,
        "canonical_chain": canonical_chain,
        "universes": universes,
        "summary": {
            "n_universes": len(universes),
            "mean_coherence": round(
                float(np.mean([u["quadrature"]["coherence"] for u in universes])), 4
            ),
            "all_reach_precipitate": all(u["final_symmetry"] == "Precipitate" for u in universes),
        },
    }
    with open(args.out, "w") as f:
        json.dump(bundle, f, indent=2)

    print(
        f"\ncosmogonic chain: {' -> '.join([canonical_chain[0]['from']] + [t['to'] for t in canonical_chain])}"
    )
    print(
        f"mean coherence across {len(universes)} universes: {bundle['summary']['mean_coherence']}"
    )
    print(f"all reached Precipitate: {bundle['summary']['all_reach_precipitate']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
