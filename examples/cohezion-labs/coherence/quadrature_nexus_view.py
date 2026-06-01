#!/usr/bin/env python3
"""Push every captured Cohezion state through the Quadrature Nexus.

The "quadrature" is the four-fabric SO(3) gauge structure on the 12D manifold:
every 12D state factors into FOUR FABRICS, each a 3D fiber over the base —

    Space          = dims 0..2     Field        = dims 3..5
    Control        = dims 6..8     Precipitation = dims 9..11
    (4 fabrics) × (3 fiber params) = 12 parameters total.

For each state we compute, using the REAL Cohezion physics components:
  - FiberBundle.decompose  -> per-fabric base norm + 3D fiber direction
  - FourFabricGauge        -> per-fabric SO(3) field-strength energy + Yang-Mills action
  - HIHO coherence         -> 1 - 4*var, peaks at the 0.5 equilibrium

Inputs are every real state we captured this session:
  - the 4+ agentic journeys persisted in SurrealDB (journey_roundtrip.point_12d)
  - canonical reference states (HIHO equilibrium 0.5, and a perturbed state)

Output: a JSON bundle the visual report renders as the 4-fabrics × 12-params grid.

Run:  PYTHONPATH=<src> python quadrature_nexus_view.py [--out quad_view.json]
"""

from __future__ import annotations

import argparse
import base64
import json
import urllib.request

import numpy as np

from cohezion.physics.fiber_bundle import FiberBundle, FABRIC_NAMES, FABRIC_SLICES
from cohezion.physics.gauge_theory import FourFabricGauge

SURREAL = "http://localhost:8001/sql"
AUTH = base64.b64encode(b"root:root").decode()


def fetch_journeys() -> list[dict]:
    """Pull real captured journey 12D points from SurrealDB."""
    req = urllib.request.Request(
        SURREAL,
        data=b"SELECT session_id, answer, task, point_12d, coherence FROM journey_roundtrip WHERE is_real_latent = true;",
        headers={
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "surreal-ns": "cohezion",
            "surreal-db": "main",
            "Authorization": f"Basic {AUTH}",
        },
    )
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=10).read())[0]["result"]
        return [
            {
                "label": f"journey:{r['session_id']}({r['answer']})",
                "state": [float(x) for x in r["point_12d"]],
                "task": r.get("task", "")[:48],
            }
            for r in res
        ]
    except Exception as e:
        print(f"[surreal] {type(e).__name__}: {e}")
        return []


def quadrature(label: str, state12: list[float], task: str = "") -> dict:
    """Push one 12D state through the four-fabric quadrature nexus."""
    state = np.asarray(state12, dtype=np.float64)
    fb = FiberBundle(dim=12, n_fabrics=4)
    decomp = fb.decompose(state)

    # SO(3) gauge: per-fabric field strength + Yang-Mills action at the HIHO target.
    gauge = FourFabricGauge()
    ym_action, is_hiho = gauge.update_and_compute(state, target=0.5)

    # per-fabric breakdown: norm (base), 3D fiber direction, the raw triplet
    fabrics = {}
    for i, name in enumerate(FABRIC_NAMES):
        sl = FABRIC_SLICES[name]
        triplet = state[sl]
        fabrics[name] = {
            "norm": round(float(decomp.base[i]), 4),
            "fiber_dir": [round(float(x), 4) for x in decomp.fiber[i]],
            "raw": [round(float(x), 4) for x in triplet],
        }

    # HIHO coherence of the full state (1 - 4*var), peaks at 0.5-equilibrium
    coherence = round(float(1.0 - min(4.0 * np.var(state), 1.0)), 4)

    return {
        "label": label,
        "task": task,
        "state12": [round(float(x), 4) for x in state],
        "fabrics": fabrics,
        "yang_mills_action": round(float(ym_action), 6),
        "is_hiho": bool(is_hiho),
        "coherence": coherence,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="quad_view.json")
    args = ap.parse_args()

    import cohezion.physics.fiber_bundle as mod

    print(f"provenance OK: FiberBundle -> {mod.__file__}")

    states: list[dict] = []
    # Canonical references first.
    states.append(
        {
            "label": "HIHO equilibrium (all 0.5)",
            "state": [0.5] * 12,
            "task": "reference: perfect coherence",
        }
    )
    rng = np.random.default_rng(7)
    states.append(
        {
            "label": "perturbed (random)",
            "state": [round(float(x), 3) for x in rng.uniform(0.1, 0.9, 12)],
            "task": "reference: off-equilibrium",
        }
    )
    # Real captured journeys.
    journeys = fetch_journeys()
    states.extend(journeys)
    print(
        f"pushing {len(states)} states through the quadrature nexus "
        f"({len(journeys)} real journeys + 2 references)"
    )

    results = [quadrature(s["label"], s["state"], s.get("task", "")) for s in states]

    bundle = {
        "fabric_names": FABRIC_NAMES,
        "fabric_slices": {k: [v.start, v.stop] for k, v in FABRIC_SLICES.items()},
        "states": results,
    }
    with open(args.out, "w") as f:
        json.dump(bundle, f, indent=2)

    # Console table
    print(
        f"\n{'state':32} {'Space':>7} {'Field':>7} {'Control':>8} {'Precip':>7} "
        f"{'S_YM':>9} {'coh':>6} hiho"
    )
    for r in results:
        fn = r["fabrics"]
        print(
            f"{r['label'][:32]:32} "
            f"{fn['Space']['norm']:7.3f} {fn['Field']['norm']:7.3f} "
            f"{fn['Control']['norm']:8.3f} {fn['Precipitation']['norm']:7.3f} "
            f"{r['yang_mills_action']:9.5f} {r['coherence']:6.3f} {r['is_hiho']}"
        )
    print(f"\nwrote {args.out} ({len(results)} states)")


if __name__ == "__main__":
    main()
