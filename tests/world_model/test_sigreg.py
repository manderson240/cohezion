"""Discriminating tests for SIGReg (Sketched Isotropic Gaussian Regularizer).

Tests the key mathematical claim: Epps-Pulley statistic is near 0 for N(0,I)
samples and HIGHER for non-Gaussian distributions. This proves the mechanism
provides the correct gradient direction for anti-collapse training.

References:
    - LeJEPA (Balestriero & LeCun, arxiv:2511.08544): optimal regularizer proof
    - LeWorldModel (Maes et al., arxiv:2603.19312): reference implementation
"""

import pytest
import torch

from cohezion.world_model.sigreg import SIGReg


@pytest.mark.unit
def test_sigreg_at_theoretical_minimum_for_gaussian() -> None:
    """Epps-Pulley converges to ~0.423 for true N(0,I) samples.

    The theoretical minimum is 1 - 1/√3 ≈ 0.423 (not 0): this is the
    expectation of the EP functional under the Gaussian null hypothesis.
    A buggy implementation returning a constant (e.g., 1.0) would fail this.
    """
    torch.manual_seed(42)
    sigreg = SIGReg(embed_dim=32, num_projections=256)
    z = torch.randn(512, 32)  # large N reduces finite-sample variance
    loss = sigreg(z)
    # Theoretical value ≈ 0.423; finite-sample variance gives ±0.1 window
    assert 0.35 < loss.item() < 0.52, (
        f"SIGReg loss on N(0,I) out of expected range: {loss.item():.4f} (expected 0.35–0.52)"
    )


@pytest.mark.unit
def test_sigreg_higher_for_collapsed() -> None:
    """Epps-Pulley is higher for near-constant (collapsed) embeddings.

    Collapsed: EP ≈ 0.586 (theoretical: 2 - √2). Gaussian: EP ≈ 0.423.
    Gap of ~0.16 is reliable — this is the primary failure mode SIGReg defends against.
    Discriminating: a bug that inverts the formula shows lower loss for collapsed.
    """
    torch.manual_seed(0)
    sigreg = SIGReg(embed_dim=32, num_projections=256)

    gaussian = torch.randn(128, 32)
    collapsed = torch.zeros(128, 32) + torch.randn(1, 32) * 0.01

    loss_gaussian = sigreg(gaussian).item()
    loss_collapsed = sigreg(collapsed).item()

    assert loss_collapsed > loss_gaussian + 0.05, (
        f"Collapsed embeddings should have measurably higher SIGReg loss: "
        f"collapsed={loss_collapsed:.4f}, gaussian={loss_gaussian:.4f} (gap < 0.05)"
    )


@pytest.mark.unit
def test_sigreg_higher_for_bimodal() -> None:
    """Epps-Pulley is substantially higher for bimodal distributions.

    Bimodal (two clusters ±3σ apart): EP ≈ 0.81 vs Gaussian ≈ 0.42.
    This verifies SIGReg responds to multi-modal representation collapse.
    """
    torch.manual_seed(1)
    sigreg = SIGReg(embed_dim=32, num_projections=256)

    gaussian = torch.randn(128, 32)
    bimodal = torch.cat([torch.randn(64, 32) - 3.0, torch.randn(64, 32) + 3.0])

    loss_gaussian = sigreg(gaussian).item()
    loss_bimodal = sigreg(bimodal).item()

    assert loss_bimodal > loss_gaussian + 0.2, (
        f"Bimodal should have much higher SIGReg loss: "
        f"bimodal={loss_bimodal:.4f}, gaussian={loss_gaussian:.4f} (gap < 0.2)"
    )


@pytest.mark.unit
def test_sigreg_small_batch_returns_zero() -> None:
    """SIGReg returns 0 for batch_size < 2 (no pairwise distances to compute)."""
    sigreg = SIGReg(embed_dim=16, num_projections=64)
    z = torch.randn(1, 16)
    loss = sigreg(z)
    assert loss.item() == pytest.approx(0.0, abs=1e-6)


@pytest.mark.unit
def test_sigreg_loss_is_differentiable() -> None:
    """SIGReg loss supports backpropagation through embeddings.

    Discriminating: a stop-gradient bug would show zero gradients.
    """
    sigreg = SIGReg(embed_dim=16, num_projections=64)
    z = torch.randn(8, 16, requires_grad=True)
    loss = sigreg(z)
    loss.backward()
    assert z.grad is not None
    assert z.grad.abs().sum().item() > 0.0, (
        "SIGReg loss produced zero gradients — stop-gradient bug"
    )


@pytest.mark.unit
def test_sigreg_projections_are_fixed() -> None:
    """Random projections must not be trainable parameters (they are buffers).

    If projections were nn.Parameters, they could degenerate to minimize the loss
    without actually regularizing the embedding distribution.
    """
    sigreg = SIGReg(embed_dim=16, num_projections=32)
    param_names = {n for n, _ in sigreg.named_parameters()}
    assert "projections" not in param_names, (
        "projections must be a buffer, not a trainable parameter"
    )


@pytest.mark.unit
def test_sigreg_wired_in_jepa_train_step() -> None:
    """SIGReg loss is non-zero in train_step and included in total_loss.

    Discriminating: if sigreg_weight=0, sigreg_loss appears but doesn't affect total.
    This verifies the CONSUMPTION path (not just declaration).
    """
    from cohezion.world_model.jepa_world_model import JEPAWorldModel

    model = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=32, sigreg_weight=0.5)
    states = torch.randn(16, 12)
    actions = torch.randn(16, 12)
    next_states = torch.randn(16, 12)

    metrics = model.train_step(states, actions, next_states)

    assert metrics["sigreg_loss"] > 0.0, "sigreg_loss is 0 — SIGReg not firing during train_step"
    # Verify contribution: total_loss includes sigreg component
    approx_total = (
        metrics["prediction_loss"]
        + 0.5 * metrics["sigreg_loss"]
        + model.regularizer_lambda * metrics["regularizer_loss"]
    )
    assert abs(metrics["total_loss"] - approx_total) < 1e-4, (
        f"sigreg not wired into total_loss: total={metrics['total_loss']:.4f}, "
        f"expected≈{approx_total:.4f}"
    )
