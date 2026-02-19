"""Tests for RL Capability Evaluator."""

from cohezion.universe.capability_evaluator import (
    CapabilityEvaluator,
    CapabilityProfile,
    CapabilityScore,
)
from cohezion.universe.scenarios import Scenario, ScenarioDifficulty, ScenarioType


class TestCapabilityScore:
    """Test capability score dataclass."""

    def test_score_creation(self):
        """Should create capability score with all dimensions."""
        score = CapabilityScore(
            task_completion=0.8,
            coherence_maintenance=0.7,
            context_retention=0.9,
            ambiguity_handling=0.6,
            interruption_recovery=0.75,
            judgment_quality=0.85,
        )
        assert score.task_completion == 0.8
        assert score.coherence_maintenance == 0.7
        assert score.context_retention == 0.9
        assert score.ambiguity_handling == 0.6
        assert score.interruption_recovery == 0.75
        assert score.judgment_quality == 0.85

    def test_composite_score(self):
        """Should compute weighted average composite score."""
        score = CapabilityScore(
            task_completion=1.0,
            coherence_maintenance=0.8,
            context_retention=0.6,
            ambiguity_handling=0.4,
            interruption_recovery=0.2,
            judgment_quality=0.0,
        )
        composite = score.composite()
        # Should be weighted average
        assert 0.0 <= composite <= 1.0
        # With equal weights, should be mean: (1.0+0.8+0.6+0.4+0.2+0.0)/6 = 0.5
        assert abs(composite - 0.5) < 0.01


class TestCapabilityEvaluator:
    """Test capability evaluator."""

    def test_evaluator_creation(self):
        """Should create evaluator."""
        evaluator = CapabilityEvaluator()
        assert evaluator is not None

    def test_evaluate_navigation_scenario(self):
        """Should evaluate navigation scenario with task_completion dimension."""
        evaluator = CapabilityEvaluator()

        # Create navigation scenario
        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Navigate to target",
            target_state={"x": 1.0, "y": 0.5},
            reward_function=lambda traj: 1.0 if traj else 0.0,
        )

        # Simulated journey (reached target)
        journey = [
            {"x": 0.0, "y": 0.0, "coherence": 0.5},
            {"x": 0.5, "y": 0.25, "coherence": 0.52},
            {"x": 1.0, "y": 0.5, "coherence": 0.48},  # At target
        ]

        score = evaluator.evaluate(scenario, journey)
        assert isinstance(score, CapabilityScore)
        # Should have high task completion (reached target)
        assert score.task_completion > 0.5
        # Should have coherence score (maintained HIHO)
        assert score.coherence_maintenance > 0.0

    def test_evaluate_maintenance_scenario(self):
        """Should evaluate maintenance scenario with coherence_maintenance dimension."""
        evaluator = CapabilityEvaluator()

        scenario = Scenario(
            type=ScenarioType.MAINTENANCE,
            difficulty=ScenarioDifficulty(),
            description="Maintain coherence",
            target_state={"coherence": 0.5},
            reward_function=lambda traj: 1.0,
            interruptions=[{"step": 5, "strength": 0.2}],
        )

        # Maintained coherence near 0.5
        journey = [
            {"coherence": 0.5, "x": 0.0},
            {"coherence": 0.52, "x": 0.0},
            {"coherence": 0.48, "x": 0.0},
            {"coherence": 0.51, "x": 0.0},
        ]

        score = evaluator.evaluate(scenario, journey)
        # High coherence maintenance
        assert score.coherence_maintenance > 0.7

    def test_evaluate_judgment_scenario(self):
        """Should evaluate judgment scenario with judgment_quality dimension."""
        evaluator = CapabilityEvaluator()

        scenario = Scenario(
            type=ScenarioType.JUDGMENT,
            difficulty=ScenarioDifficulty(judgment_complexity=0.8),
            description="Choose optimal objective",
            target_state={"x": 1.0, "y": 1.0, "quality": 0.9},
            reward_function=lambda traj: 0.9 if traj else 0.0,
            competing_objectives=[
                {"x": 1.0, "y": 1.0, "quality": 0.9},
                {"x": 0.0, "y": 0.0, "quality": 0.3},
            ],
        )

        # Chose high-quality objective
        journey = [
            {"x": 0.0, "y": 0.0},
            {"x": 0.5, "y": 0.5},
            {"x": 1.0, "y": 1.0},  # Optimal choice
        ]

        score = evaluator.evaluate(scenario, journey)
        # High judgment quality
        assert score.judgment_quality > 0.5

    def test_evaluate_interruption_scenario(self):
        """Should evaluate interruption scenario with interruption_recovery dimension."""
        evaluator = CapabilityEvaluator()

        scenario = Scenario(
            type=ScenarioType.INTERRUPTION,
            difficulty=ScenarioDifficulty(interruption_count=2, context_depth=5),
            description="Resume after interruptions",
            target_state={"x": 1.0, "y": 0.0},
            reward_function=lambda traj: 1.0,
            interruptions=[{"step": 2, "context_reset": True}, {"step": 5, "context_reset": True}],
        )

        # Recovered quickly after interruptions
        journey = [
            {"x": 0.0, "y": 0.0},
            {"x": 0.2, "y": 0.0},
            # Interrupt at step 2
            {"x": -0.5, "y": 0.5},  # Forced reset
            {"x": 0.0, "y": 0.3},  # Recovery
            {"x": 0.3, "y": 0.1},  # Back on track
            # Interrupt at step 5
            {"x": -0.3, "y": -0.2},  # Forced reset
            {"x": 0.5, "y": 0.0},  # Recovery
            {"x": 1.0, "y": 0.0},  # Target
        ]

        score = evaluator.evaluate(scenario, journey)
        # Should have interruption recovery score
        assert score.interruption_recovery > 0.0

    def test_deterministic_evaluation(self):
        """Same journey should produce same score."""
        evaluator = CapabilityEvaluator()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Test",
            target_state={"x": 1.0},
            reward_function=lambda traj: 1.0,
        )

        journey = [{"x": 0.0, "coherence": 0.5}, {"x": 1.0, "coherence": 0.5}]

        score1 = evaluator.evaluate(scenario, journey)
        score2 = evaluator.evaluate(scenario, journey)

        assert score1.task_completion == score2.task_completion
        assert score1.coherence_maintenance == score2.coherence_maintenance

    def test_anti_gaming_constant_action(self):
        """Should detect degenerate strategy: constant action."""
        evaluator = CapabilityEvaluator()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Navigate",
            target_state={"x": 1.0},
            reward_function=lambda traj: 0.0,  # Failed
        )

        # Agent didn't move (constant state)
        journey = [
            {"x": 0.0, "y": 0.0, "coherence": 0.5},
            {"x": 0.0, "y": 0.0, "coherence": 0.5},
            {"x": 0.0, "y": 0.0, "coherence": 0.5},
        ]

        score = evaluator.evaluate(scenario, journey)
        # Should penalize zero exploration
        assert score.task_completion < 0.5

    def test_anti_gaming_zero_exploration(self):
        """Should detect lack of exploration (gaming)."""
        evaluator = CapabilityEvaluator()

        scenario = Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=ScenarioDifficulty(),
            description="Navigate",
            target_state={"x": 1.0},
            reward_function=lambda traj: 0.0,
        )

        # Very small movements (no real exploration)
        journey = [
            {"x": 0.0, "coherence": 0.5},
            {"x": 0.001, "coherence": 0.5},
            {"x": 0.002, "coherence": 0.5},
        ]

        score = evaluator.evaluate(scenario, journey)
        # Should have low scores due to lack of exploration
        assert score.task_completion < 0.3


class TestCapabilityProfile:
    """Test capability profile aggregation."""

    def test_profile_creation(self):
        """Should create profile from scores."""
        scores = [
            CapabilityScore(
                task_completion=0.8,
                coherence_maintenance=0.7,
                context_retention=0.6,
                ambiguity_handling=0.5,
                interruption_recovery=0.4,
                judgment_quality=0.3,
            ),
            CapabilityScore(
                task_completion=0.9,
                coherence_maintenance=0.8,
                context_retention=0.7,
                ambiguity_handling=0.6,
                interruption_recovery=0.5,
                judgment_quality=0.4,
            ),
        ]

        profile = CapabilityProfile.from_scores(scores)
        assert profile is not None
        # Should have mean scores
        assert abs(profile.task_completion - 0.85) < 0.01  # (0.8+0.9)/2

    def test_profile_aggregation(self):
        """Should aggregate scores across scenarios."""
        scores = [
            CapabilityScore(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            CapabilityScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        ]

        profile = CapabilityProfile.from_scores(scores)
        # Mean of 1.0 and 0.0 = 0.5
        assert abs(profile.task_completion - 0.5) < 0.01
        assert abs(profile.coherence_maintenance - 0.5) < 0.01
