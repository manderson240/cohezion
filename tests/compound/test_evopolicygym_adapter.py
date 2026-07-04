"""Tests for EvoPolicyGym adapter — SkillRefinerEvoPolicyAgent structural invariants.

EV1: evolve_policy always returns str (current_policy or modified version)
EV2: evaluate_structural_edit_rate returns 0.0 before any episodes
EV3: failed episode (success=False) never produces a policy change
EV4: edit rate = changed_count / total_episodes
EV5: EvoPolicyGymBenchmark.run() returns required keys
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.compound.evopolicygym_adapter import (
    EvoPolicyFeedback,
    EvoPolicyGymBenchmark,
    SkillRefinerEvoPolicyAgent,
    _append_recommendation,
)


POLICY_STUB = "---\nname: test\n---\n# Test Policy\n"


class TestEV1EvolvePolicyReturnsStr:
    """EV1: evolve_policy always returns a str."""

    def test_returns_str_when_no_recommendation(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value=None):
            result = agent.evolve_policy(POLICY_STUB, "synthesis", EvoPolicyFeedback(success=True))
        assert isinstance(result, str)

    def test_returns_str_when_recommendation_given(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value="Use tier X for latency"):
            result = agent.evolve_policy(POLICY_STUB, "synthesis", EvoPolicyFeedback(success=True))
        assert isinstance(result, str)
        assert len(result) > len(POLICY_STUB)  # policy grew

    def test_returns_current_policy_on_none_recommendation(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value=None):
            result = agent.evolve_policy(POLICY_STUB, "synthesis", EvoPolicyFeedback(success=True))
        assert result == POLICY_STUB


class TestEV2InitialEditRate:
    """EV2: evaluate_structural_edit_rate returns 0.0 before any episodes."""

    def test_zero_before_episodes(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        assert agent.evaluate_structural_edit_rate() == 0.0


class TestEV3FailedEpisodeNoChange:
    """EV3: failed episode (success=False) never changes the policy.

    This tests the contract, not the SkillRefiner internals — evolve_policy
    should return current_policy unchanged when the refiner returns None
    (which it always does for failures, per refine()'s success gate).
    """

    def test_failed_episode_returns_current_policy(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value=None):
            result = agent.evolve_policy(
                POLICY_STUB,
                "synthesis",
                EvoPolicyFeedback(success=False, quality_score=0.2),
            )
        assert result == POLICY_STUB

    def test_failed_episode_not_counted_as_changed(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value=None):
            agent.evolve_policy(POLICY_STUB, "synthesis", EvoPolicyFeedback(success=False))
        assert not agent._episode_history[-1]["policy_changed"]


class TestEV4EditRateAccounting:
    """EV4: edit rate = changed / total episodes."""

    def test_rate_counts_changed_episodes_only(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        recommendations = [None, "update A", None, "update B", None]
        for rec in recommendations:
            with patch.object(agent.refiner, "refine", return_value=rec):
                agent.evolve_policy(POLICY_STUB, "synthesis", EvoPolicyFeedback(success=True))
        # 2 out of 5 changed
        assert abs(agent.evaluate_structural_edit_rate() - 2 / 5) < 1e-9

    def test_reset_clears_history(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value="rec"):
            agent.evolve_policy(POLICY_STUB, "synthesis", EvoPolicyFeedback(success=True))
        assert len(agent._episode_history) == 1
        agent.reset()
        assert len(agent._episode_history) == 0
        assert agent.evaluate_structural_edit_rate() == 0.0


class TestEV5BenchmarkKeys:
    """EV5: EvoPolicyGymBenchmark.run() returns required keys."""

    def test_required_keys_present(self) -> None:
        benchmark = EvoPolicyGymBenchmark()
        with patch.object(SkillRefinerEvoPolicyAgent, "evolve_policy", return_value=POLICY_STUB):
            result = benchmark.run(n_episodes=5, skill_name="COMPOUND_ENGINEERING")
        required = {
            "n_episodes",
            "skill_name",
            "structural_edit_rate",
            "opus_47_baseline",
            "outperforms_baseline",
            "episodes",
            "final_policy_length",
        }
        assert required <= set(result.keys())

    def test_opus_baseline_is_48_pct(self) -> None:
        benchmark = EvoPolicyGymBenchmark()
        with patch.object(SkillRefinerEvoPolicyAgent, "evolve_policy", return_value=POLICY_STUB):
            result = benchmark.run(n_episodes=2, skill_name="COMPOUND_ENGINEERING")
        assert result["opus_47_baseline"] == 0.48


class TestAppendRecommendation:
    """_append_recommendation increments version correctly."""

    def test_first_evolution_is_v1(self) -> None:
        policy = POLICY_STUB
        result = _append_recommendation(policy, "do X")
        assert "## Evolution v1" in result

    def test_second_evolution_is_v2(self) -> None:
        policy = _append_recommendation(POLICY_STUB, "do X")
        result = _append_recommendation(policy, "do Y")
        assert "## Evolution v2" in result

    def test_content_is_appended(self) -> None:
        result = _append_recommendation(POLICY_STUB, "Use natural gradient for JEPA")
        assert "Use natural gradient for JEPA" in result


class TestEvoPolicyFeedback:
    """EvoPolicyFeedback accepts dict conversion."""

    def test_dict_conversion_in_evolve_policy(self) -> None:
        agent = SkillRefinerEvoPolicyAgent("test-skill")
        with patch.object(agent.refiner, "refine", return_value=None):
            result = agent.evolve_policy(
                POLICY_STUB,
                "synthesis",
                {"success": True, "quality_score": 0.8},  # dict form
            )
        assert isinstance(result, str)
