"""Tests for Quadrature Nexus Scenario Dispatch."""

from unittest.mock import patch

from cohezion.universe.nexus_dispatch import NexusScenarioDispatcher
from cohezion.universe.scenarios import Scenario, ScenarioDifficulty, ScenarioType


class TestNexusScenarioDispatcher:
    """Test Nexus scenario dispatch to quadrature fabrics."""

    def test_dispatcher_creation(self):
        """Should create dispatcher with all 4 fabrics."""
        dispatcher = NexusScenarioDispatcher()
        assert dispatcher is not None
        assert dispatcher.nexus is not None

    def test_dispatch_navigation_to_space_fabric(self):
        """Navigation scenarios should route to Space fabric."""
        dispatcher = NexusScenarioDispatcher()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Navigate to target",
            target_state={"x": 1.0, "y": 0.5},
            reward_function=lambda traj: 1.0,
        )

        result = dispatcher.dispatch(scenario)
        assert result.fabric == "space"
        assert result.success is True

    def test_dispatch_maintenance_to_field_fabric(self):
        """Maintenance scenarios should route to Field fabric."""
        dispatcher = NexusScenarioDispatcher()

        scenario = Scenario(
            type=ScenarioType.MAINTENANCE,
            difficulty=ScenarioDifficulty(),
            description="Maintain coherence",
            target_state={"coherence": 0.5},
            reward_function=lambda traj: 1.0,
        )

        result = dispatcher.dispatch(scenario)
        assert result.fabric == "field"
        assert result.success is True

    def test_dispatch_judgment_to_control_fabric(self):
        """Judgment scenarios should route to Control fabric."""
        dispatcher = NexusScenarioDispatcher()

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

        result = dispatcher.dispatch(scenario)
        assert result.fabric == "control"
        assert result.success is True

    def test_dispatch_interruption_to_precipitation_fabric(self):
        """Interruption scenarios should route to Precipitation fabric."""
        dispatcher = NexusScenarioDispatcher()

        scenario = Scenario(
            type=ScenarioType.INTERRUPTION,
            difficulty=ScenarioDifficulty(interruption_count=2),
            description="Handle interruptions",
            target_state={"x": 1.0, "y": 0.0},
            reward_function=lambda traj: 1.0,
            interruptions=[
                {"step": 5, "context_reset": True},
            ],
        )

        result = dispatcher.dispatch(scenario)
        assert result.fabric == "precipitation"
        assert result.success is True

    def test_dispatch_records_perception_event(self):
        """Dispatch should record events via perception layer."""
        dispatcher = NexusScenarioDispatcher()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Test perception",
            target_state={"x": 1.0},
            reward_function=lambda traj: 1.0,
        )

        result = dispatcher.dispatch(scenario)
        assert result.success is True
        # Perception events should have been recorded
        assert len(dispatcher.dispatch_log) > 0

    def test_dispatch_multiple_scenarios(self):
        """Should dispatch multiple scenarios to correct fabrics."""
        dispatcher = NexusScenarioDispatcher()

        scenarios = [
            Scenario(
                type=ScenarioType.NAVIGATION,
                difficulty=ScenarioDifficulty(),
                description="Nav",
                target_state={"x": 1.0},
                reward_function=lambda traj: 1.0,
            ),
            Scenario(
                type=ScenarioType.JUDGMENT,
                difficulty=ScenarioDifficulty(),
                description="Judge",
                target_state={"x": 0.5},
                reward_function=lambda traj: 0.5,
            ),
        ]

        results = dispatcher.dispatch_batch(scenarios)
        assert len(results) == 2
        assert results[0].fabric == "space"
        assert results[1].fabric == "control"

    def test_dispatch_result_contains_scenario_info(self):
        """Dispatch result should contain scenario metadata."""
        dispatcher = NexusScenarioDispatcher()

        scenario = Scenario(
            type=ScenarioType.MAINTENANCE,
            difficulty=ScenarioDifficulty(),
            description="Coherence test",
            target_state={"coherence": 0.5},
            reward_function=lambda traj: 1.0,
        )

        result = dispatcher.dispatch(scenario)
        assert result.scenario_type == ScenarioType.MAINTENANCE
        assert result.fabric == "field"

    def test_all_fabric_mappings_covered(self):
        """Every ScenarioType should have a fabric mapping."""
        dispatcher = NexusScenarioDispatcher()

        for scenario_type in ScenarioType:
            fabric = dispatcher.get_fabric_for_type(scenario_type)
            assert fabric in ("space", "field", "control", "precipitation")
