"""Unit tests for Embedded Server and Embedded World Model in Kaggle Environments."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cohezion.kaggle.embedded_server import EmbeddedServerConfig, EmbeddedServerManager
from cohezion.kaggle.embedded_world_model import (
    EmbeddedWorldModel,
    TrajectoryRollout,
    WorldModelDomain,
)


def test_embedded_world_model_memory_footprint() -> None:
    wm = EmbeddedWorldModel(domain=WorldModelDomain.DISCRETE_GRID, latent_dim=16)
    # Strict mandate: < 15MB CPU RAM
    assert wm.memory_footprint_bytes < 15 * 1024 * 1024
    # In practice, compact projection weights are under 50KB!
    assert wm.memory_footprint_bytes < 50 * 1024


def test_embedded_world_model_poincare_encoding() -> None:
    wm = EmbeddedWorldModel(latent_dim=16)
    dummy_grid = [[1, 2, 0], [0, 1, 2], [2, 0, 1]]
    z = wm.encode(dummy_grid)

    assert isinstance(z, np.ndarray)
    assert z.shape == (16,)
    # Norm must be strictly strictly inside Poincaré unit ball: ||z|| < 1.0
    norm = np.linalg.norm(z)
    assert norm < 1.0
    assert norm >= 0.0


def test_poincare_geodesic_distance_properties() -> None:
    wm = EmbeddedWorldModel(latent_dim=16)
    u = wm.encode([1.0, 0.0, 0.5])
    v = wm.encode([0.0, 1.0, -0.5])

    dist_uv = wm.poincare_geodesic_distance(u, v)
    dist_vu = wm.poincare_geodesic_distance(v, u)
    dist_uu = wm.poincare_geodesic_distance(u, u)

    # Symmetry
    assert pytest.approx(dist_uv, rel=1e-5) == dist_vu
    # Identity of indiscernibles
    assert pytest.approx(dist_uu, abs=1e-6) == 0.0
    # Positive definiteness
    assert dist_uv > 0.0


def test_mental_simulation_rollout() -> None:
    wm = EmbeddedWorldModel(latent_dim=16)
    start_state = [[1, 1], [0, 0]]
    goal_state = [[0, 0], [1, 1]]
    z_goal = wm.encode(goal_state)

    actions = [0, 2, 3, 1]
    rollout = wm.simulate_rollout(
        initial_state=start_state,
        action_sequence=actions,
        goal_latent=z_goal,
        energy_threshold=2.0,
    )

    assert isinstance(rollout, TrajectoryRollout)
    assert len(rollout.predicted_latents) == 4
    assert len(rollout.step_energies) == 4
    assert rollout.total_energy == sum(rollout.step_energies)
    assert len(rollout.trajectory_hash) == 12


def test_mental_mcts_optimal_action_search() -> None:
    wm = EmbeddedWorldModel(latent_dim=16)
    start_state = [1.0, 2.0, 3.0]
    goal_state = [3.0, 2.0, 1.0]

    planned_actions = wm.plan_optimal_actions(
        current_state=start_state,
        goal_state=goal_state,
        horizon=4,
        candidate_branches=8,
    )

    assert len(planned_actions) == 4
    assert all(0 <= a < 8 for a in planned_actions)


def test_embedded_server_manager_environment_and_health() -> None:
    mgr = EmbeddedServerManager(EmbeddedServerConfig(port=13309))
    # Test healthy check with mocked httpx
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        assert mgr.is_healthy() is True

    # Test stop handles None cleanly
    mgr.stop()
    assert mgr.process is None
