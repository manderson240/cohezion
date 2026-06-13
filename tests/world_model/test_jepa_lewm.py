"""Tests for LeWM dual-loss training in the JEPA world model (Sprint 6).

Verifies the Gaussian KL regularizer (regularizer_lambda) and dual-loss training
objective work correctly.

References:
    - LeWorldModel (Maes et al., arxiv 2603.19312)
"""

import numpy as np
import pytest
import torch

from cohezion.world_model.jepa_world_model import JEPAWorldModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _small_dataset(n: int = 50, state_dim: int = 12, seed: int = 42) -> list:
    rng = np.random.default_rng(seed)
    return [
        (
            rng.normal(0.5, 0.2, state_dim).astype(np.float32),
            rng.normal(0, 0.05, state_dim).astype(np.float32),
            rng.normal(0.5, 0.2, state_dim).astype(np.float32),
        )
        for _ in range(n)
    ]


def _make_batch(
    n: int = 16, state_dim: int = 12, seed: int = 0
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    rng = np.random.default_rng(seed)
    states = rng.normal(0.5, 0.1, (n, state_dim)).astype(np.float32)
    actions = rng.normal(0, 0.05, (n, state_dim)).astype(np.float32)
    next_states = states + actions
    return (
        torch.from_numpy(states),
        torch.from_numpy(actions),
        torch.from_numpy(next_states),
    )


# ---------------------------------------------------------------------------
# Required Sprint 6 tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_training_step_returns_metrics() -> None:
    """train_step returns a dict containing both loss components."""
    model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=32, regularizer_lambda=0.1)
    states, actions, next_states = _make_batch()

    metrics = model.train_step(states, actions, next_states)

    assert "prediction_loss" in metrics
    assert "regularizer_loss" in metrics
    assert "total_loss" in metrics
    assert all(isinstance(v, float) for v in metrics.values())
    assert metrics["prediction_loss"] >= 0.0
    assert metrics["regularizer_loss"] >= 0.0
    assert metrics["total_loss"] >= 0.0


@pytest.mark.unit
def test_regularizer_lambda_zero_disables() -> None:
    """With regularizer_lambda=0, regularizer_loss must be 0 and not affect total_loss."""
    model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=32, regularizer_lambda=0.0)
    states, actions, next_states = _make_batch()

    metrics = model.train_step(states, actions, next_states)

    assert metrics["regularizer_loss"] == pytest.approx(0.0, abs=1e-6)
    # total = prediction + sigreg_weight * sigreg (no KL term)
    expected = metrics["prediction_loss"] + model.sigreg_weight * metrics["sigreg_loss"]
    assert metrics["total_loss"] == pytest.approx(expected, abs=1e-4)


@pytest.mark.unit
def test_dual_loss_components() -> None:
    """total_loss == prediction_loss + sigreg_weight*sigreg_loss + lambda*regularizer_loss."""
    lam = 0.5
    model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=32, regularizer_lambda=lam)
    states, actions, next_states = _make_batch()

    metrics = model.train_step(states, actions, next_states)

    expected = (
        metrics["prediction_loss"]
        + model.sigreg_weight * metrics["sigreg_loss"]
        + lam * metrics["regularizer_loss"]
    )
    assert metrics["total_loss"] == pytest.approx(expected, abs=1e-4)


@pytest.mark.unit
def test_regularizer_prevents_collapse() -> None:
    """After training with regularizer, embedding std must exceed collapse threshold."""
    model = JEPAWorldModel(
        state_dim=12,
        action_dim=12,
        embed_dim=32,
        regularizer_lambda=0.5,
        sigreg_weight=0.1,
        lr=1e-3,
    )
    dataset = _small_dataset(n=100)
    for _ in range(5):
        model.train_epoch(dataset, batch_size=16)

    model.encoder.eval()
    states_t = torch.from_numpy(np.array([d[0] for d in dataset], dtype=np.float32))
    with torch.no_grad():
        z, _, _ = model.encoder(states_t)

    embedding_std = z.std(dim=0).mean().item()
    assert embedding_std > 0.01, (
        f"Embeddings collapsed: mean per-dim std = {embedding_std:.4f} (threshold 0.01)"
    )


@pytest.mark.unit
def test_regularizer_reduces_embedding_variance() -> None:
    """Encoder mu with regularizer should be closer to N(0,1) than without.

    Metric: mean(|E[mu]|) + mean(|Var[mu] - 1|) — lower is better alignment with N(0,1).
    """
    dataset = _small_dataset(n=200, seed=7)

    def _dist_from_standard_normal(lam: float) -> float:
        torch.manual_seed(0)
        m = JEPAWorldModel(
            state_dim=12,
            action_dim=12,
            embed_dim=32,
            regularizer_lambda=lam,
            sigreg_weight=0.0,  # isolate KL effect
            lr=1e-3,
        )
        for _ in range(10):
            m.train_epoch(dataset, batch_size=32)
        m.encoder.eval()
        states_t = torch.from_numpy(np.array([d[0] for d in dataset], dtype=np.float32))
        with torch.no_grad():
            _, mu, _ = m.encoder(states_t)
        return (mu.mean(dim=0).abs().mean() + (mu.var(dim=0) - 1.0).abs().mean()).item()

    dist_with = _dist_from_standard_normal(lam=1.0)
    dist_without = _dist_from_standard_normal(lam=0.0)

    assert dist_with < dist_without, (
        f"Regularizer did not improve Gaussian alignment: with={dist_with:.4f}, without={dist_without:.4f}"
    )


# ---------------------------------------------------------------------------
# Additional correctness tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_regularizer_loss_nonnegative() -> None:
    """KL divergence regularizer must always be non-negative."""
    model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=32, regularizer_lambda=0.1)
    states, actions, next_states = _make_batch()
    metrics = model.train_step(states, actions, next_states)
    assert metrics["regularizer_loss"] >= -1e-6


@pytest.mark.unit
def test_all_loss_components_finite() -> None:
    """No NaN or Inf in any loss component."""
    model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=32, regularizer_lambda=0.1)
    states, actions, next_states = _make_batch()
    metrics = model.train_step(states, actions, next_states)
    for key, val in metrics.items():
        assert np.isfinite(val), f"{key} = {val} is not finite"


@pytest.mark.unit
def test_encoder_returns_mu_logvar() -> None:
    """Encoder must return (z, mu, logvar) for KL computation."""
    model = JEPAWorldModel(state_dim=12, embed_dim=32)
    x = torch.randn(4, 12)
    result = model.encoder(x)
    assert len(result) == 3
    z, mu, logvar = result
    assert z.shape == (4, 32)
    assert mu.shape == (4, 32)
    assert logvar.shape == (4, 32)


@pytest.mark.unit
def test_compute_regularizer_loss_matches_kl_formula() -> None:
    """_compute_regularizer_loss output matches the closed-form KL formula."""
    model = JEPAWorldModel(state_dim=12, embed_dim=32, regularizer_lambda=1.0)
    torch.manual_seed(3)
    mu = torch.randn(8, 32)
    logvar = torch.randn(8, 32) * 0.5

    result = model._compute_regularizer_loss(mu, logvar)

    expected = (-0.5 * torch.sum(1.0 + logvar - mu.pow(2) - logvar.exp())) / mu.size(0)
    assert result.item() == pytest.approx(expected.item(), rel=1e-4)
