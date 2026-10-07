"""Rust ``cohezion_physics_core`` must match the pure-Python fallback it accelerates.

``universe/components.py`` takes the Rust path whenever the extension imports, so the two
implementations must never drift. The Python fallback is the oracle: it predates the port
and nobody wrote it to pass this test.

Skips unless the extension is importable. Build it locally (offline, ~7 s):

    cd src/cohezion-physics-core
    PYO3_PYTHON=../../.venv/bin/python cargo build --release
    cp target/release/libcohezion_physics_core.so ../../.venv/lib/python3.13/site-packages/cohezion_physics_core.so

Measured 2026-10-06: CA 0/1536 mismatches over all 256 rules; MHD 0/3000 at rtol=1e-12.
"""

from __future__ import annotations

import random

import numpy as np
import pytest


rc = pytest.importorskip("cohezion_physics_core")

from cohezion.universe import components as C


@pytest.fixture(autouse=True)
def _python_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the engines onto the Python fallback so the comparison is Rust vs Python."""
    monkeypatch.setattr(C, "RUST_CORE_AVAILABLE", False)


@pytest.mark.parametrize("rule", range(256))
def test_ca_rule_matches_python(rule: int) -> None:
    rng = random.Random(rule)
    for n in (1, 2, 3, 17, 64):
        state = [rng.randint(0, 1) for _ in range(n)]
        state[0] = 1  # an all-zero state is re-seeded by the engine; keep inputs identical
        engine = C.CellularAutomataEngine(
            C.CellularAutomataState(grid_size=n, rule=rule, state=list(state))
        )
        assert list(rc.evolve_ca_simd(list(state), rule)) == engine.evolve(), (rule, n)


def test_mhd_matches_python_including_edge_shapes() -> None:
    rng = random.Random(0)
    engine = C.MagnetohydrodynamicsEngine()
    for k in range(1000):
        n = rng.choice([0, 1, 2, 3, 8, 256])
        vec = np.array([rng.uniform(-3, 3) for _ in range(n)], dtype=np.float64)
        if k % 25 == 0:
            vec[:] = 0.0  # zero norm: the scale branch must be skipped by both
        helicity, moment = rng.uniform(-2, 2), rng.uniform(0, 3)
        dt = rng.choice([0.0, 0.01, 0.1, 1.0])
        evo = C.EvoState(
            charge_density=1.0, magnetic_helicity=helicity, toroidal_moment=moment, coherence=0.5
        )
        expected = engine.apply_mhd_forces(evo, vec, dt)
        got = vec.copy()
        rc.apply_mhd_forces_simd(got, helicity, moment, dt)
        np.testing.assert_allclose(got, expected, rtol=1e-12, atol=1e-12)
