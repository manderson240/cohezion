"""Tests for Phase 19: Cosmic Fire Protocol, Triune Self, R0Σ, Greek Parameters."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest


# --- GreekParameters tests ---


class TestGreekParameters:
    def test_gamma_peaks_at_hiho(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        assert gp.gamma(0.5) == pytest.approx(1.0, rel=1e-9)

    def test_gamma_zero_at_extremes(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        assert gp.gamma(0.0) == pytest.approx(0.0)
        assert gp.gamma(1.0) == pytest.approx(0.0)

    def test_update_converges_toward_omega(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters(alpha=0.05, omega=0.5, delta=0.0, beta=0.01)
        x = 0.1
        for _ in range(50):
            x = gp.update(x)
        assert 0.4 < x < 0.6, f"Expected convergence near 0.5, got {x:.3f}"

    def test_converged_returns_true_at_omega(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        assert gp.converged(0.5) is True
        assert gp.converged(0.47) is True
        assert gp.converged(0.3) is False

    def test_trajectory_length(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        path = gp.trajectory(x0=0.1, steps=20)
        assert len(path) == 21  # x(0) through x(20)

    def test_trajectory_stays_in_bounds(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        path = gp.trajectory(x0=0.01, steps=100)
        assert all(0.0 <= x <= 1.0 for x in path)

    def test_beta_capped_at_a3_invariant(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters(beta=0.5)  # should be clamped to 0.015
        assert gp.beta <= 0.015

    def test_steps_to_convergence_from_zero(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters(alpha=0.05, beta=0.01, delta=0.0)
        steps = gp.steps_to_convergence(x0=0.0, max_steps=500)
        assert steps < 500, "Should converge in finite steps from x=0"

    def test_to_dict_contains_all_keys(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        d = gp.to_dict()
        for key in ("alpha", "omega", "delta", "beta", "gamma_at_hiho"):
            assert key in d

    def test_gamma_at_hiho_is_one_in_dict(self):
        from cohezion.compound.greek_parameters import GreekParameters

        gp = GreekParameters()
        assert gp.to_dict()["gamma_at_hiho"] == pytest.approx(1.0)

    def test_adversarial_delta_slows_convergence(self):
        from cohezion.compound.greek_parameters import GreekParameters

        no_delta = GreekParameters(alpha=0.05, delta=0.0, beta=0.01)
        with_delta = GreekParameters(alpha=0.05, delta=0.05, beta=0.01)
        steps_no = no_delta.steps_to_convergence(x0=0.1, max_steps=200)
        steps_with = with_delta.steps_to_convergence(x0=0.1, max_steps=200)
        assert steps_with >= steps_no, "Delta should slow convergence"


# --- UncertaintyBand / R0Σ tests ---


class TestUncertaintyBand:
    def test_from_scores_mean(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand.from_scores([0.4, 0.5, 0.6])
        assert ub.mean_score == pytest.approx(0.5)

    def test_high_confidence_at_hiho(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand(mean_score=0.5, std_dev=0.05, sigma_n=0.0)
        assert ub.confidence == "HIGH"
        assert ub.trigger_r0() is False

    def test_low_confidence_triggers_r0(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand(mean_score=0.5, std_dev=0.12, sigma_n=1.5)
        assert ub.confidence == "LOW"
        assert ub.trigger_r0() is True

    def test_medium_confidence_band(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand(mean_score=0.4, std_dev=0.08, sigma_n=0.75)
        assert ub.confidence == "MEDIUM"
        assert ub.trigger_r0() is False

    def test_from_scores_single(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand.from_scores([0.7])
        assert ub.mean_score == pytest.approx(0.7)
        assert ub.sigma_n == 0.0

    def test_from_scores_empty(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand.from_scores([])
        assert math.isinf(ub.sigma_n)

    def test_to_dict_keys(self):
        from cohezion.compound.r0_sigma import UncertaintyBand

        ub = UncertaintyBand(0.5, 0.05, 0.2)
        d = ub.to_dict()
        assert "confidence" in d and "trigger_r0" in d and "sigma_n" in d


class TestR0Challenge:
    def test_valid_verdict(self):
        from cohezion.compound.r0_sigma import CONFIRMED, R0Challenge

        c = R0Challenge(perspective="scientific_rigor", score=0.8, verdict=CONFIRMED)
        assert c.score == pytest.approx(0.8)

    def test_invalid_verdict_raises(self):
        from cohezion.compound.r0_sigma import R0Challenge

        with pytest.raises(ValueError, match="Invalid verdict"):
            R0Challenge(perspective="test", score=0.5, verdict="MAYBE")

    def test_score_clamped(self):
        from cohezion.compound.r0_sigma import CONFIRMED, R0Challenge

        c = R0Challenge(perspective="p", score=2.5, verdict=CONFIRMED)
        assert c.score <= 1.0


class TestR0ChallengeResult:
    def test_consensus_confirmed_2_of_3(self):
        from cohezion.compound.r0_sigma import CONFIRMED, WEAK, R0Challenge, R0ChallengeResult

        result = R0ChallengeResult(
            challenges=[
                R0Challenge("scientific_rigor", 0.8, CONFIRMED),
                R0Challenge("physical_consistency", 0.7, CONFIRMED),
                R0Challenge("implementation", 0.4, WEAK),
            ]
        )
        assert result.consensus_verdict == CONFIRMED
        assert result.is_accepted() is True

    def test_consensus_rejected_majority(self):
        from cohezion.compound.r0_sigma import CONFIRMED, REJECTED, R0Challenge, R0ChallengeResult

        result = R0ChallengeResult(
            challenges=[
                R0Challenge("scientific_rigor", 0.2, REJECTED),
                R0Challenge("physical_consistency", 0.3, REJECTED),
                R0Challenge("implementation", 0.7, CONFIRMED),
            ]
        )
        assert result.consensus_verdict == REJECTED
        assert result.is_accepted() is False

    def test_sigma_band_computed(self):
        from cohezion.compound.r0_sigma import CONFIRMED, R0Challenge, R0ChallengeResult

        result = R0ChallengeResult(
            challenges=[
                R0Challenge("p1", 0.4, CONFIRMED),
                R0Challenge("p2", 0.6, CONFIRMED),
                R0Challenge("p3", 0.5, CONFIRMED),
            ]
        )
        band = result.sigma_band
        assert band.mean_score == pytest.approx(0.5, abs=0.01)

    def test_to_dict_keys(self):
        from cohezion.compound.r0_sigma import R0ChallengeResult

        result = R0ChallengeResult()
        d = result.to_dict()
        assert "consensus" in d and "sigma_n" in d and "perspectives" in d


# --- CosmicFireProtocol tests ---


class TestCosmicFireProtocol:
    def test_not_ignited_below_threshold(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(threshold=0.45, notify_telegram=False)
        assert cfp.is_ignited(0.3) is False

    def test_ignited_at_threshold(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(threshold=0.45, notify_telegram=False)
        assert cfp.is_ignited(0.45) is True
        assert cfp.is_ignited(0.8) is True

    def test_ignite_returns_event(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        event = cfp.ignite(quality_score=0.5, redshift=3.0)
        assert event is not None
        assert event.coherence == pytest.approx(0.5)
        assert event.redshift == pytest.approx(3.0)

    def test_ignite_returns_none_below_threshold(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        assert cfp.ignite(0.2) is None

    def test_ignition_count_increments(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        cfp.ignite(0.5)
        cfp.ignite(0.6)
        assert cfp.ignition_count == 2

    def test_zoom_level_doubles(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        e1 = cfp.ignite(0.5)
        e2 = cfp.ignite(0.5)
        assert e2.zoom_level == 2 * e1.zoom_level

    def test_cascade_actions_nonempty_above_threshold(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        actions = cfp.ignition_cascade(0.5)
        assert len(actions) == 5
        assert "enter_bbq_low_slow_mode" in actions

    def test_cascade_empty_below_threshold(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        assert cfp.ignition_cascade(0.2) == []

    def test_last_event_stored(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        cfp.ignite(0.5, redshift=10.0)
        assert cfp.last_event is not None
        assert cfp.last_event.redshift == pytest.approx(10.0)

    def test_hiho_temperature_analog(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(threshold=0.45, ignition_temperature=155.0, notify_telegram=False)
        assert cfp.hiho_temperature_analog() == pytest.approx(155.0)

    def test_surreal_record_has_valid_from(self):
        from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

        cfp = CosmicFireProtocol(notify_telegram=False)
        event = cfp.ignite(0.5)
        record = event.to_surreal_record()
        assert "valid_from" in record
        assert record["valid_to"] is None


# --- TriuneSelf tests ---


class TestTriuneSelf:
    def _make_doer(self, output="hello world", score=0.7):
        doer = MagicMock()
        doer.run_sync.return_value = (output, {"model": "mock"})
        return doer

    def _make_thinker(self, accept=True, score=0.7):
        thinker = MagicMock()
        verdict = MagicMock()
        verdict.accept = accept
        verdict.score = score
        result = MagicMock()
        result.verdict = verdict
        thinker.evaluate.return_value = result
        return thinker

    def test_one_cycle_returns_result(self):
        from cohezion.compound.triune_self import TriuneSelf

        ts = TriuneSelf(doer=self._make_doer(), thinker=self._make_thinker())
        result = ts.recursive_learn("test task", "test guidance")
        assert result.task == "test task"
        assert result.accepted is True

    def test_rejected_output_retries(self):
        from cohezion.compound.triune_self import TriuneSelf

        thinker = self._make_thinker(accept=False, score=0.3)
        ts = TriuneSelf(doer=self._make_doer(), thinker=thinker, max_cycles=1)
        result = ts.recursive_learn("task", "guidance")
        assert result.accepted is False

    def test_cycle_count_increments(self):
        from cohezion.compound.triune_self import TriuneSelf

        ts = TriuneSelf(doer=self._make_doer(), thinker=self._make_thinker())
        ts.recursive_learn("t1", "g1")
        ts.recursive_learn("t2", "g2")
        assert ts.cycle_count == 2

    def test_accept_rate_all_accepted(self):
        from cohezion.compound.triune_self import TriuneSelf

        ts = TriuneSelf(doer=self._make_doer(), thinker=self._make_thinker(accept=True))
        for _ in range(5):
            ts.recursive_learn("task", "guidance")
        assert ts.accept_rate == pytest.approx(1.0)

    def test_hiho_equilibrium_at_0_5(self):
        from cohezion.compound.triune_self import TriuneSelf

        ts = TriuneSelf(doer=self._make_doer(), thinker=self._make_thinker(score=0.5))
        ts.recursive_learn("task", "guidance")
        assert ts.hiho_equilibrium is True

    def test_knower_receives_coherence(self):
        from cohezion.compound.triune_self import TriuneSelf

        knower = MagicMock()
        ts = TriuneSelf(
            doer=self._make_doer(),
            thinker=self._make_thinker(accept=True, score=0.6),
            knower=knower,
        )
        ts.recursive_learn("task", "guidance")
        knower.record_coherence.assert_called_once_with(pytest.approx(0.6))

    def test_knower_not_called_on_rejection(self):
        from cohezion.compound.triune_self import TriuneSelf

        knower = MagicMock()
        ts = TriuneSelf(
            doer=self._make_doer(),
            thinker=self._make_thinker(accept=False, score=0.3),
            knower=knower,
            max_cycles=1,
        )
        ts.recursive_learn("task", "guidance")
        knower.record_coherence.assert_not_called()

    def test_summary_dict_keys(self):
        from cohezion.compound.triune_self import TriuneSelf

        ts = TriuneSelf(doer=self._make_doer(), thinker=self._make_thinker())
        ts.recursive_learn("task", "guidance")
        s = ts.summary()
        assert "accept_rate" in s and "hiho_equilibrium" in s and "cycle_count" in s
