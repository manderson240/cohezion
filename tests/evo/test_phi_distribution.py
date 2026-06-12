"""Tests for PhiDistribution — Z-Reward-style distributional phi scoring."""

import pytest


class TestPhiDistributionFromSeries:
    def test_empty_series_returns_uniform_with_laplace(self):
        from cohezion.evo import PhiDistribution

        d = PhiDistribution.from_phi_series([])
        assert len(d.probs) == len(PhiDistribution._DEFAULT_BINS) - 1
        assert abs(sum(d.probs) - 1.0) < 1e-9
        assert d.point_estimate == 0.0

    def test_single_value_concentrates_in_correct_bin(self):
        from cohezion.evo import PhiDistribution

        # phi=0.35 falls in [0.3, 0.5) — bin index 3
        d = PhiDistribution.from_phi_series([0.35])
        # bin 3 ([0.3,0.5)) should have highest probability after smoothing
        assert d.probs[3] > d.probs[0]
        assert d.probs[3] > d.probs[1]
        assert d.probs[3] > d.probs[2]

    def test_probs_sum_to_one(self):
        from cohezion.evo import PhiDistribution

        d = PhiDistribution.from_phi_series([0.1, 0.25, 0.32, 0.28, 0.33])
        assert abs(sum(d.probs) - 1.0) < 1e-9

    def test_point_estimate_is_last_value(self):
        from cohezion.evo import PhiDistribution

        d = PhiDistribution.from_phi_series([0.1, 0.3, 0.42])
        assert d.point_estimate == pytest.approx(0.42)

    def test_clamps_phi_values_to_unit_interval(self):
        from cohezion.evo import PhiDistribution

        d = PhiDistribution.from_phi_series([-0.5, 1.5, 0.5])
        assert abs(sum(d.probs) - 1.0) < 1e-9  # must not crash, must be valid


class TestGateProbability:
    def test_all_above_gate_returns_high_probability(self):
        from cohezion.evo import PhiDistribution

        # Series entirely above 0.3 — gate_prob should be substantially > 0.5
        d = PhiDistribution.from_phi_series([0.35, 0.40, 0.38, 0.36, 0.42])
        assert d.gate_probability(0.3) > 0.5

    def test_all_below_gate_returns_low_probability(self):
        from cohezion.evo import PhiDistribution

        # Series entirely below 0.3 — gate_prob approaches Laplace floor
        d = PhiDistribution.from_phi_series([0.05, 0.08, 0.07, 0.09, 0.06])
        assert d.gate_probability(0.3) < 0.3

    def test_borderline_series_differs_from_monotone_decay(self):
        """Two voyages at same final phi can have different gate probabilities."""
        from cohezion.evo import PhiDistribution

        # High-variance: sometimes above gate
        d_volatile = PhiDistribution.from_phi_series([0.35, 0.32, 0.28, 0.22, 0.24])
        # Monotone decay: always below gate
        d_monotone = PhiDistribution.from_phi_series([0.22, 0.21, 0.20, 0.19, 0.24])

        assert d_volatile.gate_probability(0.3) > d_monotone.gate_probability(0.3)

    def test_gate_probability_in_unit_interval(self):
        from cohezion.evo import PhiDistribution

        for vals in [[0.5, 0.6, 0.7], [0.1, 0.2, 0.3], [0.0], [1.0]]:
            d = PhiDistribution.from_phi_series(vals)
            gp = d.gate_probability()
            assert 0.0 <= gp <= 1.0


class TestExpectedPhi:
    def test_expected_phi_near_midpoint_for_concentrated_series(self):
        from cohezion.evo import PhiDistribution

        # All values in [0.3, 0.5) — midpoint is 0.4
        d = PhiDistribution.from_phi_series([0.35, 0.38, 0.40, 0.37])
        # Expected phi should be close to 0.4 (smoothing pulls slightly toward other bins)
        assert 0.2 <= d.expected_phi() <= 0.6

    def test_expected_phi_positive_for_any_input(self):
        from cohezion.evo import PhiDistribution

        assert PhiDistribution.from_phi_series([]).expected_phi() >= 0.0
        assert PhiDistribution.from_phi_series([0.0]).expected_phi() >= 0.0


class TestAsDict:
    def test_as_dict_has_required_keys(self):
        from cohezion.evo import PhiDistribution

        d = PhiDistribution.from_phi_series([0.3, 0.35])
        result = d.as_dict()
        assert "bins" in result
        assert "probs" in result
        assert "point_estimate" in result
        assert "gate_prob" in result
        assert "expected_phi" in result

    def test_as_dict_is_json_serializable(self):
        import json
        from cohezion.evo import PhiDistribution

        d = PhiDistribution.from_phi_series([0.2, 0.31, 0.28])
        json.dumps(d.as_dict())  # must not raise


class TestVoyageCarriesDistribution:
    def test_complete_journey_attaches_phi_distribution(self):
        """complete_journey() populates voyage.phi_distribution."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.evo import PhiDistribution
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.universe.agentic_evo_swift import AgenticEVO

        agent = AgenticEVO(agent_id="dist-test-001")
        tracer = RecursiveTracer(agent, JourneyTracker())
        tracer.trace_step("distribution test step")
        voyage = tracer.complete_journey(journey_id="dist-j")

        assert voyage.phi_distribution is not None
        assert isinstance(voyage.phi_distribution, PhiDistribution)

    def test_distribution_point_estimate_matches_phi_score(self):
        """PhiDistribution.point_estimate == voyage.phi_score (within float precision)."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.universe.agentic_evo_swift import AgenticEVO

        agent = AgenticEVO(agent_id="dist-test-002")
        tracer = RecursiveTracer(agent, JourneyTracker())
        tracer.trace_step("phi consistency")
        voyage = tracer.complete_journey(journey_id="dist-j2")

        assert abs(voyage.phi_distribution.point_estimate - voyage.phi_score) < 1e-9

    def test_multistep_distribution_reflects_all_steps(self):
        """With 4 steps, distribution is built from all 4 phi values."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.universe.agentic_evo_swift import AgenticEVO

        agent = AgenticEVO(agent_id="dist-test-003")
        tracer = RecursiveTracer(agent, JourneyTracker())
        for _ in range(4):
            tracer.trace_step("step")
        voyage = tracer.complete_journey(journey_id="dist-j3")

        # 4 steps observed → distribution is non-degenerate (not just prior)
        d = voyage.phi_distribution
        assert d is not None
        assert abs(sum(d.probs) - 1.0) < 1e-9
        # With 4 real observations the dominant bin has > Laplace-only weight
        assert max(d.probs) > min(d.probs)
