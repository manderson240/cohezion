"""Tests for the FLUME-VAE Optuna tuner. Fast: a cheap surrogate objective, no VAE training.

Locks the A3/A4 invariants into the search: the tuner must NEVER propose a kl_weight above the
posterior-collapse boundary (A3=0.015) or a non-2-layer decoder (A4).
"""

from __future__ import annotations

import pytest

from cohezion.flume.optuna_tuner import (
    BASELINE,
    HIDDEN_DIM_CHOICES,
    KL_WEIGHT_MAX,
    FlumeTuneConfig,
    assert_safe,
)


class TestSafetyEnvelope:
    def test_baseline_is_safe(self):
        assert_safe(BASELINE)  # the A4 hand-tuned config must be in-envelope

    def test_rejects_a3_kl_weight_violation(self):
        """kl_weight above the A3 collapse boundary (0.015) must be rejected."""
        with pytest.raises(ValueError, match="A3 violated"):
            assert_safe(FlumeTuneConfig(kl_weight=0.02, coherence_weight=0.05, hidden_dim=4096))

    def test_rejects_a4_decoder_violation(self):
        """A non-2-layer decoder (A4) must be rejected."""
        with pytest.raises(ValueError, match="A4 violated"):
            assert_safe(
                FlumeTuneConfig(
                    kl_weight=0.01, coherence_weight=0.05, hidden_dim=4096, decoder_layers=3
                )
            )


class TestStudy:
    def test_search_never_leaves_a3_a4_envelope(self):
        """Every trial the tuner samples must stay kl_weight<=0.015 and hidden_dim in the set."""
        optuna = pytest.importorskip("optuna")
        from cohezion.flume.optuna_tuner import sample_config

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=1))
        study.optimize(lambda t: sample_config(t).kl_weight, n_trials=30)
        for tr in study.trials:
            assert tr.params["kl_weight"] <= KL_WEIGHT_MAX
            assert tr.params["hidden_dim"] in HIDDEN_DIM_CHOICES

    def test_run_study_reports_beats_baseline_and_safe_winner(self):
        """A surrogate peaking inside the envelope beats a low baseline; winner stays safe."""
        pytest.importorskip("optuna")
        from cohezion.flume.optuna_tuner import run_flume_study

        # Cheap surrogate: peaks near kl_weight=0.008, hidden_dim=4096; always positive.
        def surrogate(cfg: FlumeTuneConfig) -> float:
            return 1.0 - 50.0 * (cfg.kl_weight - 0.008) ** 2 - abs(cfg.hidden_dim - 4096) / 1e5

        res = run_flume_study(surrogate, n_trials=25, baseline_value=0.0, seed=7)
        assert res.n_trials == 25
        assert res.beats_baseline is True  # best_value > 0.0 baseline
        assert_safe(res.best_config)  # winner is A3/A4-safe (raises if not)
        assert res.best_value > res.baseline_value
