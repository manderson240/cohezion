"""/api/physics size/iteration params are bounded at the API boundary.

Before: out-of-range values were accepted and silently clamped inside the handler (e.g.
epochs=10_000 ran 500 epochs and returned 200), or not clamped at all (atom_count,
ring_count). The ``Query`` bounds mirror the handler clamps exactly, so nothing a handler
would actually honour starts failing -- only the silent substitution becomes a 422.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app


client = TestClient(app)

# (path, param, first value above the maximum)
ABOVE_MAX = [
    ("/api/physics/bioelectric", "n_cells", 129),
    ("/api/physics/hamiltonian/simulate", "epochs", 501),
    ("/api/physics/hamiltonian/simulate", "n_agents", 33),
    ("/api/physics/hamiltonian/simulate", "z_dim", 65),
    ("/api/physics/emergence/detect", "n_agents", 65),
    ("/api/physics/emergence/detect", "n_cycles", 1001),
    ("/api/physics/emergence/detect", "z_dim", 65),
    ("/api/physics/bec/status", "atom_count", 1_000_000_001),
    ("/api/physics/toroidal/status", "ring_count", 1001),
]


@pytest.mark.parametrize(("path", "param", "value"), ABOVE_MAX)
def test_value_above_max_is_rejected(path, param, value):
    """DISCRIMINATING: before the bounds each of these returned 200."""
    resp = client.get(path, params={param: value})
    assert resp.status_code == 422, f"{path}?{param}={value} -> {resp.status_code}"


@pytest.mark.parametrize("path", sorted({p for p, _, _ in ABOVE_MAX}))
def test_defaults_still_succeed(path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(("path", "param", "value"), ABOVE_MAX)
def test_the_maximum_itself_is_accepted(path, param, value):
    """The bound is inclusive: le=N must not be an off-by-one ge=N-1."""
    assert client.get(path, params={param: value - 1}).status_code == 200
