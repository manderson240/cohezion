"""Tests for agentic scenario generation."""

from cohezion.universe.scenarios import (
    Scenario,
    ScenarioDifficulty,
    ScenarioGenerator,
    ScenarioType,
)


class TestScenarioDifficulty:
    """Test scenario difficulty configuration."""

    def test_default_difficulty(self):
        """Default difficulty should have balanced parameters."""
        diff = ScenarioDifficulty()
        assert 0.0 <= diff.ambiguity_level <= 1.0
        assert diff.interruption_count >= 0
        assert diff.context_depth >= 1
        assert 0.0 <= diff.judgment_complexity <= 1.0

    def test_custom_difficulty(self):
        """Should accept custom difficulty parameters."""
        diff = ScenarioDifficulty(
            ambiguity_level=0.8,
            interruption_count=5,
            context_depth=10,
            judgment_complexity=0.9,
        )
        assert diff.ambiguity_level == 0.8
        assert diff.interruption_count == 5
        assert diff.context_depth == 10
        assert diff.judgment_complexity == 0.9


class TestScenario:
    """Test scenario data structure."""

    def test_scenario_creation(self):
        """Should create valid scenario with all required fields."""
        difficulty = ScenarioDifficulty()
        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=difficulty,
            description="Navigate to target coordinates",
            target_state={"x": 1.0, "y": 0.5},
            reward_function=lambda trajectory: 1.0,
        )
        assert scenario.type == ScenarioType.NAVIGATION
        assert scenario.difficulty == difficulty
        assert scenario.description == "Navigate to target coordinates"
        assert scenario.target_state == {"x": 1.0, "y": 0.5}
        assert callable(scenario.reward_function)

    def test_scenario_reward_function(self):
        """Scenario reward function should be callable."""
        scenario = Scenario(
            type=ScenarioType.MAINTENANCE,
            difficulty=ScenarioDifficulty(),
            description="Maintain coherence",
            target_state={},
            reward_function=lambda trajectory: 0.5,
        )
        # Test with dummy trajectory
        reward = scenario.reward_function([])
        assert reward == 0.5


class TestScenarioGenerator:
    """Test scenario generation."""

    def test_generator_initialization(self):
        """Generator should initialize with default seed."""
        generator = ScenarioGenerator(seed=42)
        assert generator is not None

    def test_generate_navigation_scenario(self):
        """Should generate navigation scenario with target position."""
        generator = ScenarioGenerator(seed=42)
        scenario = generator.generate(
            scenario_type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(ambiguity_level=0.3),
        )
        assert scenario.type == ScenarioType.NAVIGATION
        assert scenario.difficulty.ambiguity_level == 0.3
        assert "target_state" in dir(scenario)
        assert scenario.target_state is not None
        assert callable(scenario.reward_function)

    def test_generate_maintenance_scenario(self):
        """Should generate maintenance scenario with coherence requirements."""
        generator = ScenarioGenerator(seed=42)
        scenario = generator.generate(
            scenario_type=ScenarioType.MAINTENANCE,
            difficulty=ScenarioDifficulty(interruption_count=3),
        )
        assert scenario.type == ScenarioType.MAINTENANCE
        assert scenario.difficulty.interruption_count == 3
        assert callable(scenario.reward_function)

    def test_generate_judgment_scenario(self):
        """Should generate judgment scenario with competing objectives."""
        generator = ScenarioGenerator(seed=42)
        scenario = generator.generate(
            scenario_type=ScenarioType.JUDGMENT,
            difficulty=ScenarioDifficulty(judgment_complexity=0.8),
        )
        assert scenario.type == ScenarioType.JUDGMENT
        assert scenario.difficulty.judgment_complexity == 0.8
        assert callable(scenario.reward_function)

    def test_generate_interruption_scenario(self):
        """Should generate interruption scenario with context switches."""
        generator = ScenarioGenerator(seed=42)
        scenario = generator.generate(
            scenario_type=ScenarioType.INTERRUPTION,
            difficulty=ScenarioDifficulty(
                interruption_count=5, context_depth=8
            ),
        )
        assert scenario.type == ScenarioType.INTERRUPTION
        assert scenario.difficulty.interruption_count == 5
        assert scenario.difficulty.context_depth == 8
        assert callable(scenario.reward_function)

    def test_deterministic_generation(self):
        """Same seed should produce identical scenarios."""
        gen1 = ScenarioGenerator(seed=42)
        gen2 = ScenarioGenerator(seed=42)

        scenario1 = gen1.generate(ScenarioType.NAVIGATION)
        scenario2 = gen2.generate(ScenarioType.NAVIGATION)

        assert scenario1.type == scenario2.type
        assert scenario1.difficulty.ambiguity_level == scenario2.difficulty.ambiguity_level
        assert scenario1.target_state == scenario2.target_state

    def test_random_perturbation_with_different_seeds(self):
        """Different seeds should produce different scenarios."""
        gen1 = ScenarioGenerator(seed=42)
        gen2 = ScenarioGenerator(seed=99)

        scenario1 = gen1.generate(ScenarioType.NAVIGATION)
        scenario2 = gen2.generate(ScenarioType.NAVIGATION)

        # Same type but likely different target states due to random perturbation
        assert scenario1.type == scenario2.type
        # At least one parameter should differ
        assert (
            scenario1.target_state != scenario2.target_state
            or scenario1.difficulty.ambiguity_level != scenario2.difficulty.ambiguity_level
        )
