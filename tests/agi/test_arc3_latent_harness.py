"""
test_arc3_latent_harness.py — Tests for ARC-AGI-3 Hybrid Latent Working Memory & Affordance Harness.
"""

import numpy as np
import pytest
from cohezion.agi.arc3_latent_harness import (
    PoincareManifold16D,
    ContinuousWorkingMemory,
    LatentResidualAdapter,
    HybridPoincareARC3Solver,
)


def test_poincare_manifold_geometry():
    """Verify Poincaré ball metric properties: bounds, symmetry, zero self-distance."""
    u = np.array([0.2, -0.3, 0.1, 0.4] + [0.0] * 12)
    v = np.array([-0.1, 0.5, 0.2, -0.2] + [0.0] * 12)

    # Clamping test
    clamped_u = PoincareManifold16D.clamp(u)
    assert np.linalg.norm(clamped_u) < 1.0

    # Self-distance is 0
    d_uu = PoincareManifold16D.distance(u, u)
    assert abs(d_uu) < 1e-6

    # Symmetry: d(u, v) == d(v, u)
    d_uv = PoincareManifold16D.distance(u, v)
    d_vu = PoincareManifold16D.distance(v, u)
    assert abs(d_uv - d_vu) < 1e-6
    assert d_uv > 0.0


def test_continuous_working_memory_recurrence():
    """Verify working memory tracks multi-step actions and detects circular states."""
    wm = ContinuousWorkingMemory(latent_dim=16, memory_dim=32, num_actions=8, seed=42)

    z1 = np.ones(16) * 0.1
    m1 = wm.step(z1, last_action=1)
    assert m1.shape == (32,)
    assert len(wm.trajectory_history) == 1
    assert wm.action_history == [1]

    # Circular trajectory simulation
    z2 = np.ones(16) * 0.1
    m2 = wm.step(z2, last_action=2)
    m3 = wm.step(z1, last_action=1)

    sim = wm.compute_temporal_similarity(lookback=4)
    assert 0.0 <= sim <= 1.0


def test_latent_residual_adapter_projection():
    """Verify adapter projects [m_t, z_t] into 16D latent delta."""
    adapter = LatentResidualAdapter(input_dim=48, hidden_dim=32, seed=42)
    m_t = np.random.randn(32)
    z_t = np.random.randn(16)

    delta = adapter.forward(m_t, z_t)
    assert delta.shape == (16,)
    assert not np.any(np.isnan(delta))
    assert not np.any(np.isinf(delta))


def test_hybrid_poincare_solver_action_selection():
    """Verify complete solver on a simulated 10x10 ARC grid."""
    solver = HybridPoincareARC3Solver(seed=20261016)

    # 10x10 grid with background 0, an affordance goal at (8, 8) with color 2
    grid = np.zeros((10, 10), dtype=np.int64)
    grid[8, 8] = 2  # target component
    grid[5, 5] = 1  # player initial pos

    avail = [1, 2, 3, 4, 5, 6]  # Up, Down, Left, Right, Interact, Click
    act, args = solver.select_action(grid, avail)

    assert act in avail
    assert isinstance(args, dict)

    # Next step: simulate moving right to (5, 6)
    grid2 = np.zeros((10, 10), dtype=np.int64)
    grid2[8, 8] = 2
    grid2[5, 6] = 1

    act2, args2 = solver.select_action(grid2, avail)
    assert act2 in avail
    assert solver.player_pos is not None
    # Solver should detect player moved
    assert solver.player_pos == (5, 6)
