"""Tests for Bioelectric Scenario Navigator."""

import numpy as np

from cohezion.universe.bioelectric_navigator import BioelectricNavigator
from cohezion.universe.evo_agent import EVOAgent
from cohezion.universe.scenarios import Scenario, ScenarioDifficulty, ScenarioType


class TestBioelectricNavigator:
    """Test bioelectric scenario navigation."""

    def test_navigator_creation(self):
        """Should create navigator."""
        nav = BioelectricNavigator()
        assert nav is not None

    def test_navigate_navigation_scenario(self):
        """Should navigate agent through navigation scenario."""
        nav = BioelectricNavigator()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Navigate to target",
            target_state={"x": 1.0, "y": 0.5, "z": 0.0},
            reward_function=lambda traj: 1.0 if traj else 0.0,
        )

        agent = EVOAgent(agent_id="test-agent")
        max_steps = 20

        trajectory = nav.navigate_scenario(scenario, agent, max_steps=max_steps)

        # Should produce trajectory
        assert len(trajectory) > 0
        assert len(trajectory) <= max_steps
        # Each point should have position and bioelectric signal
        for point in trajectory:
            assert "state" in point
            assert "signal" in point
            assert "action" in point

    def test_navigate_with_interruptions(self):
        """Should handle interruptions during navigation."""
        nav = BioelectricNavigator()

        scenario = Scenario(
            type=ScenarioType.INTERRUPTION,
            difficulty=ScenarioDifficulty(interruption_count=2),
            description="Navigate with interruptions",
            target_state={"x": 1.0, "y": 0.0},
            reward_function=lambda traj: 1.0,
            interruptions=[
                {"step": 5, "context_reset": True, "forced_state_x": -0.5, "forced_state_y": 0.3},
                {
                    "step": 10,
                    "context_reset": True,
                    "forced_state_x": 0.2,
                    "forced_state_y": -0.4,
                },
            ],
        )

        agent = EVOAgent(agent_id="test-agent")

        trajectory = nav.navigate_scenario(scenario, agent, max_steps=15)

        # Should handle interruptions (context switches)
        assert len(trajectory) > 0
        # Should have interruption markers in trajectory
        # (Interruptions inject forced state changes)

    def test_navigate_ambiguous_scenario(self):
        """Should handle ambiguous target wells."""
        nav = BioelectricNavigator()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(ambiguity_level=0.7),
            description="Navigate with noisy target",
            target_state={"x": 0.5, "y": 0.5, "z": 0.0},
            reward_function=lambda traj: 1.0,
        )

        agent = EVOAgent(agent_id="test-agent")

        trajectory = nav.navigate_scenario(scenario, agent, max_steps=15)

        # Should still navigate despite ambiguity
        assert len(trajectory) > 0

    def test_navigate_judgment_scenario(self):
        """Should navigate judgment scenario with multiple wells."""
        nav = BioelectricNavigator()

        scenario = Scenario(
            type=ScenarioType.JUDGMENT,
            difficulty=ScenarioDifficulty(judgment_complexity=0.8),
            description="Choose optimal well",
            target_state={"x": 1.0, "y": 1.0, "quality": 0.9},
            reward_function=lambda traj: 0.9,
            competing_objectives=[
                {"x": 1.0, "y": 1.0, "quality": 0.9},
                {"x": -1.0, "y": -1.0, "quality": 0.3},
            ],
        )

        agent = EVOAgent(agent_id="test-agent")

        trajectory = nav.navigate_scenario(scenario, agent, max_steps=20)

        # Should navigate toward one of the objectives
        assert len(trajectory) > 0

    def test_morphospace_validation(self):
        """Should validate non-degenerate morphospace."""
        nav = BioelectricNavigator()

        # Scenario with degenerate wells (all same position)
        scenario = Scenario(
            type=ScenarioType.JUDGMENT,
            difficulty=ScenarioDifficulty(),
            description="Degenerate wells",
            target_state={"x": 0.0, "y": 0.0, "quality": 1.0},
            reward_function=lambda traj: 1.0,
            competing_objectives=[
                {"x": 0.0, "y": 0.0, "quality": 1.0},
                {"x": 0.0, "y": 0.0, "quality": 0.5},
            ],
        )

        agent = EVOAgent(agent_id="test-agent")

        # Should detect degenerate morphospace and handle it
        # (Either skip validation or regenerate wells)
        # Should not crash
        trajectory = nav.navigate_scenario(scenario, agent, max_steps=10)
        assert trajectory is not None

    def test_trajectory_includes_signals(self):
        """Trajectory should include bioelectric signals and actions."""
        nav = BioelectricNavigator()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Test",
            target_state={"x": 1.0, "y": 0.0, "z": 0.0},
            reward_function=lambda traj: 1.0,
        )

        agent = EVOAgent(agent_id="test-agent")

        trajectory = nav.navigate_scenario(scenario, agent, max_steps=5)

        # Each point should have state, signal, action
        for point in trajectory:
            assert "state" in point
            assert "signal" in point
            assert "action" in point
            assert isinstance(point["state"], np.ndarray)

    def test_agent_state_conversion(self):
        """Should convert between AxiomaticState and numpy."""
        nav = BioelectricNavigator()

        agent = EVOAgent(agent_id="test-agent")

        # Get numpy representation
        state_arr = agent.to_numpy()
        assert isinstance(state_arr, np.ndarray)
        assert state_arr.shape == (12,)

        # Update from numpy
        new_arr = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.2, 0.3])
        agent.update_from_numpy(new_arr)

        # State should have changed
        updated_arr = agent.to_numpy()
        np.testing.assert_array_equal(updated_arr, new_arr)
