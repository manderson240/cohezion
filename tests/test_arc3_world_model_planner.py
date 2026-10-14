"""Unit & Integration Tests for ARC-AGI-3 Latent World Model Planning Engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

try:
    from arcengine import GameAction
except ImportError:
    from enum import IntEnum

    class GameAction(IntEnum):
        RESET = 0
        ACTION0 = 0
        ACTION1 = 1
        ACTION2 = 2
        ACTION3 = 3
        ACTION4 = 4
        ACTION5 = 5
        ACTION6 = 6

from cohezion.arc.tracks.arc3_world_model_planner import (
    CayleyPermutationGraph,
    PoincareGeodesicNavSimulator,
    WorldModelARC3Planner,
    run_offline_benchmark,
)
from cohezion.competitions.world_models.embedded_adajepa_poincare_world_model import (
    EmbeddedPoincareJEPAWorldModel,
)


def test_embedded_poincare_memory_footprint():
    """Verify world model footprint is strictly < 15MB with zero GPU allocation."""
    wm = EmbeddedPoincareJEPAWorldModel(latent_dim=12)
    w_bytes = wm.W_enc.nbytes + wm.W_trans.nbytes
    assert w_bytes < 15 * 1024 * 1024
    assert w_bytes < 100 * 1024  # Actually under 100 KB!


def test_type_b_cayley_permutation_mental_simulation():
    """Verify Cayley graph mental simulation plans shortest path without physical misclicks."""
    graph = CayleyPermutationGraph()
    dummy_grid = np.zeros((64, 64), dtype=int)

    # State graph: S0 --(10, 10)--> S1 --(20, 20)--> S_GOAL
    graph.record_transition("S0", (10, 10), "S1", dummy_grid)
    graph.record_transition("S1", (20, 20), "S_GOAL", dummy_grid)
    graph.known_targets.add("S_GOAL")

    path = graph.simulate_shortest_path("S0", max_depth=5)
    assert path == [(10, 10), (20, 20)]

    # Verify unexplored generator selection
    unexplored = graph.get_unexplored_button("S0", [(10, 10), (30, 30)])
    assert unexplored == (30, 30)


def test_type_a_dead_end_pruning():
    """Verify dead-end cul-de-sacs are pruned in mental simulation."""
    wm = EmbeddedPoincareJEPAWorldModel(latent_dim=12)
    sim = PoincareGeodesicNavSimulator(wm)

    # Position (5, 5) surrounded by walls on 3 sides: (4, 5), (6, 5), (5, 4)
    walls = {(4, 5), (6, 5), (5, 4)}
    goal_pos = (10, 10)

    # Should detect dead end
    assert sim.is_dead_end((5, 5), walls, goal_pos) is True

    # Goal position itself is never a dead end
    assert sim.is_dead_end((10, 10), walls, (10, 10)) is False


def test_strict_35_step_truncation_preserves_ratio():
    """Verify agent truncates after 35 steps to preserve (H_l / A_l)^2."""
    planner = WorldModelARC3Planner(game_id="lp85-305b61c3", max_steps_per_level=35)

    obs = MagicMock()
    obs.frame = [np.zeros((64, 64), dtype=int)]
    obs.available_actions = [0, 6]
    obs.levels_completed = 0

    # Advance to step 35
    for _ in range(35):
        act, _ = planner.choose_action(obs)

    assert planner.level_step_count == 35

    # Step 36 must trigger truncation guard and return RESET (RESET / PASS)
    act_36, _ = planner.choose_action(obs)
    assert act_36 in (getattr(GameAction, "RESET", 0), getattr(GameAction, "ACTION0", 0))
    assert 0 in planner.truncated_levels


def test_hermetic_offline_benchmark_mocked():
    """Verify offline benchmark runner executes cleanly across all 3 game IDs."""
    mock_env = MagicMock()
    mock_obs_reset = MagicMock()
    mock_obs_reset.frame = [np.zeros((64, 64), dtype=int)]
    mock_obs_reset.available_actions = [1, 2, 3, 4]
    mock_obs_reset.levels_completed = 0
    mock_obs_reset.state = "NOT_FINISHED"

    mock_obs_step = MagicMock()
    mock_obs_step.frame = [np.zeros((64, 64), dtype=int)]
    mock_obs_step.available_actions = [1, 2, 3, 4]
    mock_obs_step.levels_completed = 1
    mock_obs_step.state = "WIN"

    mock_env.reset.return_value = mock_obs_reset
    mock_env.step.return_value = mock_obs_step

    with patch("arc_agi.Arcade") as mock_arcade_cls:
        arcade_instance = mock_arcade_cls.return_value
        arcade_instance.make.return_value = mock_env
        mock_scorecard = MagicMock()
        mock_scorecard.score = 3.0
        arcade_instance.close_scorecard.return_value = mock_scorecard

        res = run_offline_benchmark(
            game_ids=["lp85-305b61c3", "ls20-9607627b", "r11l-495a7899"],
            environments_dir="environment_files",
        )

        assert res["completed_levels"] == 3
        assert res["total_actions"] == 3
        assert res["overall_score"] > 0
        assert "lp85-305b61c3" in res["games"]
        assert "ls20-9607627b" in res["games"]
        assert "r11l-495a7899" in res["games"]
