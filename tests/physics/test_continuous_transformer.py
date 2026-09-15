"""Unit tests for Continuous Integro-Differential Transformer (arXiv:2510.03989)."""

from __future__ import annotations

import torch
import torch.nn as nn

from cohezion.physics.continuous_transformer import (
    ContinuousFeedForwardOperator,
    ContinuousTransformerBlock,
    ContinuousTransformerEngine,
    LayerNormProjectionOperator,
    NonLocalAttentionOperator,
    OperatorSplittingScheme,
)


class TestLayerNormProjectionTheorem:
    """Validates Theorem 3.1: Layer Normalization is exact S_1 manifold projection."""

    def test_theorem_3_1_matches_pytorch_layernorm(self) -> None:
        dim = 32
        batch = 2
        tokens = 8

        op = LayerNormProjectionOperator(dim=dim, eps=1e-5, affine=False)
        pt_ln = nn.LayerNorm(dim, eps=1e-5, elementwise_affine=False)

        x = torch.randn(batch, tokens, dim)
        out_op = op(x)
        out_pt = pt_ln(x)

        # Numerical difference should be within floating-point tolerance
        assert torch.allclose(out_op, out_pt, atol=1e-6)

    def test_manifold_s1_statistical_invariants(self) -> None:
        dim = 64
        op = LayerNormProjectionOperator(dim=dim, sigma1=0.0, sigma2=1.0, eps=1e-5, affine=False)

        x = torch.randn(4, 16, dim) * 5.0 + 3.0
        projected = op(x)

        # Means along feature dimension \Omega_y must be ~ 0
        means = projected.mean(dim=-1)
        assert torch.allclose(means, torch.zeros_like(means), atol=1e-5)

        # Variance along feature dimension \Omega_y must be ~ 1
        vars_ = projected.var(dim=-1, unbiased=False)
        assert torch.allclose(vars_, torch.ones_like(vars_), atol=1e-4)


class TestSubproblemOperators:
    """Validates individual operators from the continuous integro-differential formulation."""

    def test_non_local_attention_operator(self) -> None:
        dim = 32
        tokens = 10
        batch = 2

        attn = NonLocalAttentionOperator(dim=dim, num_heads=4)
        u = torch.randn(batch, tokens, dim)
        out = attn(u)

        assert out.shape == (batch, tokens, dim)
        assert not torch.isnan(out).any()

    def test_continuous_feedforward_operator(self) -> None:
        dim = 32
        tokens = 10
        batch = 2

        ffn = ContinuousFeedForwardOperator(dim=dim, hidden_dim=64)
        u = torch.randn(batch, tokens, dim)
        out = ffn(u)

        assert out.shape == (batch, tokens, dim)
        assert not torch.isnan(out).any()


class TestOperatorSplittingBlocks:
    """Validates Lie and Strang operator splitting schemes."""

    def test_lie_splitting_block_step(self) -> None:
        dim = 32
        tokens = 8
        batch = 2

        block = ContinuousTransformerBlock(
            dim=dim,
            num_heads=4,
            scheme=OperatorSplittingScheme.LIE,
            dt=1.0,
            learnable_dt=False,
        )

        u = torch.randn(batch, tokens, dim)
        out = block(u)

        assert out.shape == (batch, tokens, dim)
        assert not torch.isnan(out).any()
        assert block.dt == 1.0

    def test_strang_splitting_block_step(self) -> None:
        dim = 32
        tokens = 8
        batch = 2

        block = ContinuousTransformerBlock(
            dim=dim,
            num_heads=4,
            scheme=OperatorSplittingScheme.STRANG,
            dt=0.5,
            learnable_dt=False,
        )

        u = torch.randn(batch, tokens, dim)
        out = block(u)

        assert out.shape == (batch, tokens, dim)
        assert not torch.isnan(out).any()
        assert block.dt == 0.5

    def test_learnable_dt_backpropagation(self) -> None:
        dim = 16
        tokens = 4
        batch = 1

        block = ContinuousTransformerBlock(
            dim=dim,
            num_heads=2,
            scheme=OperatorSplittingScheme.STRANG,
            dt=0.8,
            learnable_dt=True,
        )

        u = torch.randn(batch, tokens, dim)
        out = block(u)
        loss = out.sum()
        loss.backward()

        assert block._dt_param.grad is not None
        assert not torch.isnan(block._dt_param.grad)


class TestContinuousTransformerEngine:
    """Validates multi-layer trajectory integration and manifold invariance checks."""

    def test_trajectory_integration(self) -> None:
        dim = 32
        tokens = 6
        layers = 3
        batch = 2

        engine = ContinuousTransformerEngine(
            dim=dim,
            num_heads=4,
            num_layers=layers,
            scheme=OperatorSplittingScheme.STRANG,
            dt=0.25,
            poincare_bound=10.0,
        )

        u0 = torch.randn(batch, tokens, dim)
        trajectory = engine.integrate_trajectory(u0)

        assert len(trajectory) == layers + 1
        for state in trajectory:
            assert state.shape == (batch, tokens, dim)

    def test_manifold_invariants_verification(self) -> None:
        dim = 32
        tokens = 6
        batch = 2

        engine = ContinuousTransformerEngine(dim=dim, num_heads=4, num_layers=2)
        u0 = torch.randn(batch, tokens, dim)
        u_final = engine(u0)

        invariants = engine.verify_invariants(u_final)
        assert invariants.mean_error < 0.2
        assert invariants.is_on_manifold
        assert invariants.poincare_norm > 0.0
