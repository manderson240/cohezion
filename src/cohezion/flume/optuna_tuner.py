"""Optuna hyperparameter tuning for the FLUME VAE — a real local optimizer ($0, no CUDA)
replacing manual / LLM-heuristic search over the empirically-validated safe envelope.

Today the FLUME-VAE numerics are hand-tuned (harness A3–A5) and `hyperparameter_debate.py`
is an LLM heuristic, not an optimizer. This wires Optuna's TPE/Bayesian search over the
A3/A4-SAFE region so the search can never leave the known-good envelope:

  - ``kl_weight`` ∈ [0.001, 0.015]  — A3: β > 0.015 causes posterior collapse. HARD cap.
  - ``coherence_weight`` ∈ [0.0, 0.1]
  - ``hidden_dim`` ∈ {2048, 4096, 8192} — A4: 4096 is the known optimum; search around it.
  - decoder layers FIXED at 2 — A4: a 3-layer decoder collapses KL. NOT searched.

The objective is INJECTED (``config -> validated_metric``) so the FLUME train+eval loop is
the caller's concern and the tuner is unit-testable with a cheap surrogate (no VAE training).
The A4 hand-tuned config is the baseline; a tuned config is only reported as a win when it
BEATS that baseline (never regress the 4-seed 0.8815 mean).

Reference: vault research/2026-07-11-friction-metric... (map-don't-rebuild); harness A3–A5.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # optuna is an optional (dev/tune) dependency — lazy-imported at call time.
    import optuna

# --- A3/A4 invariant bounds (harness.md). The search MUST NOT leave this envelope. ---
KL_WEIGHT_MIN = 0.001
KL_WEIGHT_MAX = 0.015  # A3 posterior-collapse boundary — hard cap
DECODER_LAYERS = 2  # A4 — fixed, never searched (3-layer collapses KL)
HIDDEN_DIM_CHOICES = (2048, 4096, 8192)  # A4 optimum 4096 is in the set


@dataclass
class FlumeTuneConfig:
    """A point in the A3/A4-safe FLUME-VAE hyperparameter space."""

    kl_weight: float
    coherence_weight: float
    hidden_dim: int
    decoder_layers: int = DECODER_LAYERS  # A4-fixed


# The A4 hand-tuned baseline (4-seed mean 0.8815) — the config a tuned result must beat.
BASELINE = FlumeTuneConfig(kl_weight=0.01, coherence_weight=0.05, hidden_dim=4096)


def assert_safe(cfg: FlumeTuneConfig) -> None:
    """Guard the A3/A4 invariants. Raises ValueError if a config leaves the safe envelope."""
    if not (KL_WEIGHT_MIN <= cfg.kl_weight <= KL_WEIGHT_MAX):
        raise ValueError(
            f"A3 violated: kl_weight={cfg.kl_weight} outside [{KL_WEIGHT_MIN}, {KL_WEIGHT_MAX}]"
        )
    if cfg.decoder_layers != DECODER_LAYERS:
        raise ValueError(
            f"A4 violated: decoder_layers={cfg.decoder_layers} (must be {DECODER_LAYERS})"
        )


def sample_config(trial: optuna.Trial) -> FlumeTuneConfig:
    """Sample an A3/A4-safe config from an Optuna trial. The suggested ranges cannot leave
    the safe envelope; assert_safe is a belt-and-braces check."""
    cfg = FlumeTuneConfig(
        kl_weight=trial.suggest_float("kl_weight", KL_WEIGHT_MIN, KL_WEIGHT_MAX, log=True),
        coherence_weight=trial.suggest_float("coherence_weight", 0.0, 0.1),
        hidden_dim=trial.suggest_categorical("hidden_dim", list(HIDDEN_DIM_CHOICES)),
    )
    assert_safe(cfg)
    return cfg


@dataclass
class StudyResult:
    best_config: FlumeTuneConfig
    best_value: float
    baseline_value: float
    beats_baseline: bool
    n_trials: int


def run_flume_study(
    objective_fn: Callable[[FlumeTuneConfig], float],
    *,
    n_trials: int = 25,
    baseline_value: float | None = None,
    direction: str = "maximize",
    seed: int = 42,
) -> StudyResult:
    """Run a bounded Optuna study over the A3/A4-safe FLUME-VAE space.

    ``objective_fn``: config -> validated metric. The caller wires the real FLUME train+eval;
    tests inject a cheap surrogate. ``baseline_value``: the A4 hand-tuned metric to beat
    (computed via ``objective_fn(BASELINE)`` when None). The result flags ``beats_baseline``
    so a tuned config is only adopted when it genuinely improves on the hand-tuned config.
    """
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    base = baseline_value if baseline_value is not None else objective_fn(BASELINE)
    study = optuna.create_study(direction=direction, sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(lambda t: objective_fn(sample_config(t)), n_trials=n_trials)

    p = study.best_params
    best_cfg = FlumeTuneConfig(
        kl_weight=p["kl_weight"],
        coherence_weight=p["coherence_weight"],
        hidden_dim=p["hidden_dim"],
    )
    assert_safe(best_cfg)  # the winner must still be in-envelope
    beats = study.best_value > base if direction == "maximize" else study.best_value < base
    return StudyResult(
        best_config=best_cfg,
        best_value=study.best_value,
        baseline_value=base,
        beats_baseline=beats,
        n_trials=n_trials,
    )
