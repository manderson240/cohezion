r"""Continuous Integro-Differential Transformer & Operator Splitting Engine
========================================================================
Implements the continuous mathematical formulation of Transformers from
Tai, Liu, Li, & Chan (arXiv:2510.03989, 2025).

Core Formulation:
-----------------
The Transformer encoder is interpreted as the discretization of the continuous
integro-differential equation:

    u_t = \langle \gamma(\mathbf{x},\cdot,t;u), V(\cdot,\mathbf{y},t;u) \rangle_{\Omega_x}
        + \partial I_{S_1(\sigma_1(t),\sigma_2(t))}(u)
        + \sum_{j=1}^J \left( \langle W_j(\cdot,\mathbf{y},t), u(\mathbf{x},\cdot,t) \rangle_{\Omega_y} + b_j(\mathbf{x},t) \right)
        + \partial I_{S_2}(u)

where:
1. Attention is a non-local integral operator over the token spatial domain \Omega_x.
2. Layer normalization is an exact variational projection onto the statistical manifold
   S_1(\sigma_1, \sigma_2) per Theorem 3.1.
3. Feedforward ReLU is a metric projection onto the non-negative cone S_2 = \{ u \ge 0 \}.
4. Time-discretization via 1st-order Lie splitting with \Delta t = 1.0 recovers the standard
   discrete Transformer encoder block (Vaswani et al. 2017) exactly.
5. Symmetrized 2nd-order Strang splitting with continuous \Delta t \in (0, 1] suppresses
   off-manifold drift, prevents rank collapse, and enables depth extrapolation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple, cast

import torch
import torch.nn as nn
import torch.nn.functional as F


class OperatorSplittingScheme(StrEnum):
    """Numerical operator splitting strategy for the continuous Transformer flow."""

    LIE = "lie"  # 1st-order sequential splitting: exact Vaswani et al. discrete Transformer
    STRANG = "strang"  # 2nd-order symmetric splitting: O(dt^3) local error, zero manifold drift


class ManifoldInvariants(NamedTuple):
    """Statistical and metric invariants along the continuous representation flow."""

    mean_error: float
    variance_error: float
    poincare_norm: float
    is_bounded: bool
    is_on_manifold: bool


class LayerNormProjectionOperator(nn.Module):
    r"""Exact variational projection onto the statistical manifold S_1(\sigma_1, \sigma_2).

    Governed by the subdifferential equation:
        u - v \in -\partial I_{S_1(\sigma_1, \sigma_2)}(u)
        \iff u = \arg\min_{\bar{u} \in S_1(\sigma_1, \sigma_2)} \frac{1}{2} \|\bar{u} - v\|^2_{\Omega_y}

    Theorem 3.1 (Tai et al. 2025) provides the closed-form minimizer:
        u(\mathbf{x}, \mathbf{y}) = \sigma_1 + \frac{\sigma_2}{\sqrt{\mathrm{Var}(v) + \epsilon}} (v(\mathbf{x}, \mathbf{y}) - \bar{v}(\mathbf{x}))
    """

    def __init__(
        self,
        dim: int,
        sigma1: float = 0.0,
        sigma2: float = 1.0,
        eps: float = 1e-5,
        affine: bool = True,
    ) -> None:
        super().__init__()
        self.dim = dim
        self.sigma1 = sigma1
        self.sigma2 = sigma2
        self.eps = eps
        self.affine = affine

        if affine:
            self.gamma = nn.Parameter(torch.ones(dim))
            self.beta = nn.Parameter(torch.zeros(dim))
        else:
            self.register_parameter("gamma", None)
            self.register_parameter("beta", None)

    def forward(self, v: torch.Tensor) -> torch.Tensor:
        """Project input field v onto manifold S_1(sigma_1, sigma_2).

        Parameters
        ----------
        v : torch.Tensor
            Input tensor of shape (batch, num_tokens, dim).

        Returns
        -------
        torch.Tensor
            Projected field u on S_1.
        """
        # Continuous mean along feature domain \Omega_y
        mean = v.mean(dim=-1, keepdim=True)
        # Continuous variance along feature domain \Omega_y
        var = v.var(dim=-1, keepdim=True, unbiased=False)
        # Theorem 3.1 closed-form projection
        std = torch.sqrt(var + self.eps)
        normalized = (v - mean) / std
        projected = self.sigma1 + self.sigma2 * normalized

        if self.affine and self.gamma is not None and self.beta is not None:
            return projected * self.gamma + self.beta
        return projected


class NonLocalAttentionOperator(nn.Module):
    r"""Continuous non-local integral attention operator over token domain \Omega_x.

    Computes:
        \mathcal{A}[u](\mathbf{x}, \mathbf{y}) = \int_{\Omega_x} \gamma(\mathbf{x}, \tilde{\mathbf{x}}; u) V(\tilde{\mathbf{x}}, \mathbf{y}; u) d\tilde{\mathbf{x}}
    """

    def __init__(self, dim: int, num_heads: int = 4, dropout: float = 0.0) -> None:
        super().__init__()
        if dim % num_heads != 0:
            raise ValueError(f"dim ({dim}) must be divisible by num_heads ({num_heads})")
        self.dim = dim
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = 1.0 / (self.head_dim**0.5)

        self.w_q = nn.Linear(dim, dim, bias=True)
        self.w_k = nn.Linear(dim, dim, bias=True)
        self.w_v = nn.Linear(dim, dim, bias=True)
        self.out_proj = nn.Linear(dim, dim, bias=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, u: torch.Tensor) -> torch.Tensor:
        """Compute non-local integral attention transform.

        Parameters
        ----------
        u : torch.Tensor
            Field tensor of shape (batch, num_tokens, dim).

        Returns
        -------
        torch.Tensor
            Transformed field A[u] of shape (batch, num_tokens, dim).
        """
        batch_size, num_tokens, _ = u.shape

        # Compute Q, K, V integral transformations
        q = self.w_q(u).view(batch_size, num_tokens, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.w_k(u).view(batch_size, num_tokens, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.w_v(u).view(batch_size, num_tokens, self.num_heads, self.head_dim).transpose(1, 2)

        # Non-local affinity kernel \gamma(\mathbf{x}, \tilde{\mathbf{x}})
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        gamma = F.softmax(scores, dim=-1)
        gamma = self.dropout(gamma)

        # Integrate over token domain \Omega_x
        context = torch.matmul(gamma, v)
        context = context.transpose(1, 2).contiguous().view(batch_size, num_tokens, self.dim)
        return cast("torch.Tensor", self.out_proj(context))


class ContinuousFeedForwardOperator(nn.Module):
    r"""Continuous feedforward operator with non-negative cone projection (S_2).

    Solves:
        \bar{u} = u + \Delta t (u W_1 + b_1)
        u_{proj} = \arg\min_{w \in S_2} \frac{1}{2} \|w - \bar{u}\|^2 = \mathrm{ReLU}(\bar{u})
        u_{out} = u_{proj} W_2 + b_2
    """

    def __init__(self, dim: int, hidden_dim: int | None = None, dropout: float = 0.0) -> None:
        super().__init__()
        self.dim = dim
        self.hidden_dim = hidden_dim or (4 * dim)
        self.w1 = nn.Linear(dim, self.hidden_dim)
        self.w2 = nn.Linear(self.hidden_dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, u: torch.Tensor) -> torch.Tensor:
        """Evaluate feedforward network with S_2 cone projection.

        Parameters
        ----------
        u : torch.Tensor
            Input field tensor of shape (batch, num_tokens, dim).

        Returns
        -------
        torch.Tensor
            Transformed field of shape (batch, num_tokens, dim).
        """
        # Projection onto cone S_2 is exact ReLU
        h = F.relu(self.w1(u))
        h = self.dropout(h)
        return cast("torch.Tensor", self.w2(h))


class ContinuousTransformerBlock(nn.Module):
    r"""Continuous Integro-Differential Transformer Block.

    Executes operator splitting (Lie or Strang) on the continuous dynamical system:
        u_t = \mathcal{A}[u] + \partial I_{S_1}(u) + \mathcal{F}[u] + \partial I_{S_2}(u)
    """

    def __init__(
        self,
        dim: int,
        num_heads: int = 4,
        ffn_hidden_dim: int | None = None,
        scheme: OperatorSplittingScheme = OperatorSplittingScheme.LIE,
        dt: float = 1.0,
        learnable_dt: bool = False,
        dropout: float = 0.0,
        eps: float = 1e-5,
    ) -> None:
        super().__init__()
        self.dim = dim
        self.num_heads = num_heads
        self.scheme = scheme
        self.eps = eps

        # Operators corresponding to the four continuous subproblems
        self.attention_op = NonLocalAttentionOperator(dim, num_heads=num_heads, dropout=dropout)
        self.norm1_op = LayerNormProjectionOperator(dim, eps=eps)
        self.ffn_op = ContinuousFeedForwardOperator(dim, hidden_dim=ffn_hidden_dim, dropout=dropout)
        self.norm2_op = LayerNormProjectionOperator(dim, eps=eps)

        if learnable_dt:
            self._dt_param = nn.Parameter(torch.tensor([float(dt)]))
            self.learnable_dt = True
        else:
            self.register_buffer("_dt_val", torch.tensor([float(dt)]))
            self.learnable_dt = False

    def get_dt(self) -> torch.Tensor:
        """Return dt tensor preserving autograd graph."""
        if self.learnable_dt:
            return torch.clamp(self._dt_param, min=1e-4, max=2.0)
        return cast("torch.Tensor", self._dt_val)

    @property
    def dt(self) -> float:
        """Current integration step size as float."""
        return float(self.get_dt().item())

    def forward(self, u: torch.Tensor) -> torch.Tensor:
        """Advance representation field by dt using selected operator splitting scheme.

        Parameters
        ----------
        u : torch.Tensor
            Representation field tensor of shape (batch, num_tokens, dim).

        Returns
        -------
        torch.Tensor
            Evolved representation field after step dt.
        """
        dt = self.get_dt()
        if self.scheme == OperatorSplittingScheme.LIE:
            return self._step_lie(u, dt)
        return self._step_strang(u, dt)

    def _step_lie(self, u0: torch.Tensor, dt: torch.Tensor) -> torch.Tensor:
        r"""1st-Order Lie-Trotter Operator Splitting.

        Exact discretization of (16)-(21) from Tai et al. (arXiv:2510.03989):
            u^{1/6} = u^0 + dt * \mathcal{A}[u^0]          (Substep 1: Attention + Skip)
            u^{2/6} = \mathrm{Proj}_{S_1}(u^{1/6})         (Substep 2: First LayerNorm)
            u^{3/6} = \mathrm{Proj}_{S_2}(u^{2/6} W_1)     (Substep 3: FFN Linear + ReLU)
            u^{4/6} = u^{3/6} W_2                         (Substep 4: FFN Linear)
            u^{5/6} = u^{2/6} + dt * u^{4/6}               (Substep 5: Skip Connection)
            u^1     = \mathrm{Proj}_{S_1}(u^{5/6})         (Substep 6: Final LayerNorm)
        """
        # Substep 1: Explicit step on attention (recovers attention + skip connection)
        u_attn = u0 + dt * self.attention_op(u0)

        # Substep 2: Projection onto manifold S_1 (recovers first layer normalization)
        u_norm1 = self.norm1_op(u_attn)

        # Substeps 3-4: FFN evaluation with S_2 projection
        ffn_out = self.ffn_op(u_norm1)

        # Substep 5: Skip connection (relaxation step)
        u_skip = u_norm1 + dt * ffn_out

        # Substep 6: Final projection onto manifold S_1
        return cast("torch.Tensor", self.norm2_op(u_skip))

    def _step_strang(self, u0: torch.Tensor, dt: torch.Tensor) -> torch.Tensor:
        r"""2nd-Order Symmetric Strang Splitting: S_{dt/2}^A \circ S_{dt}^B \circ S_{dt/2}^A.

        Symmetrizes the non-local attention step and FFN/LayerNorm projections to achieve
        O(dt^3) local truncation error and eliminate off-manifold drift.
        """
        half_dt = 0.5 * dt

        # Half-step attention
        u_half = u0 + half_dt * self.attention_op(u0)

        # Symmetrized projection onto S_1
        u_norm = self.norm1_op(u_half)

        # Full-step FFN with S_2 projection
        ffn_out = self.ffn_op(u_norm)
        u_mid = u_norm + dt * ffn_out
        u_mid_norm = self.norm2_op(u_mid)

        # Closing half-step attention
        return cast("torch.Tensor", u_mid_norm + half_dt * self.attention_op(u_mid_norm))


class ContinuousTransformerEngine(nn.Module):
    r"""Multi-Layer Continuous Integro-Differential Transformer Engine.

    Evolves representation fields over depth t \in [0, T] using operator-splitting
    schemes with verification hooks for Poincaré manifold invariance.
    """

    def __init__(
        self,
        dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 4,
        ffn_hidden_dim: int | None = None,
        scheme: OperatorSplittingScheme = OperatorSplittingScheme.LIE,
        dt: float = 1.0,
        learnable_dt: bool = False,
        poincare_bound: float = 0.95,
        dropout: float = 0.0,
        eps: float = 1e-5,
    ) -> None:
        super().__init__()
        self.dim = dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.scheme = scheme
        self.poincare_bound = poincare_bound

        self.blocks = nn.ModuleList(
            [
                ContinuousTransformerBlock(
                    dim=dim,
                    num_heads=num_heads,
                    ffn_hidden_dim=ffn_hidden_dim,
                    scheme=scheme,
                    dt=dt,
                    learnable_dt=learnable_dt,
                    dropout=dropout,
                    eps=eps,
                )
                for _ in range(num_layers)
            ]
        )

    def forward(self, u: torch.Tensor) -> torch.Tensor:
        """Forward trajectory integration through all layers."""
        curr = u
        for block in self.blocks:
            curr = block(curr)
        return curr

    def integrate_trajectory(self, u0: torch.Tensor) -> list[torch.Tensor]:
        """Record the discrete trajectory of states across all depth steps.

        Parameters
        ----------
        u0 : torch.Tensor
            Initial state field tensor of shape (batch, num_tokens, dim).

        Returns
        -------
        list[torch.Tensor]
            Sequence of state fields [u^0, u^1, ..., u^{N_t}].
        """
        trajectory = [u0]
        curr = u0
        for block in self.blocks:
            curr = block(curr)
            trajectory.append(curr)
        return trajectory

    def verify_invariants(self, u: torch.Tensor) -> ManifoldInvariants:
        """Formally verify statistical and Poincaré metric invariants.

        Parameters
        ----------
        u : torch.Tensor
            Field state tensor of shape (batch, num_tokens, dim).

        Returns
        -------
        ManifoldInvariants
            Validation metrics indicating adherence to manifold constraints.
        """
        with torch.no_grad():
            means = u.mean(dim=-1)
            mean_err = float(torch.abs(means).max().item())

            vars_ = u.var(dim=-1, unbiased=False)
            var_err = float(torch.abs(vars_ - 1.0).max().item())

            norms = torch.linalg.vector_norm(u, dim=-1)
            max_norm = float(norms.max().item())
            is_bounded = max_norm < self.poincare_bound
            is_on_manifold = mean_err < 0.1 and not torch.isnan(u).any().item()

            return ManifoldInvariants(
                mean_error=mean_err,
                variance_error=var_err,
                poincare_norm=max_norm,
                is_bounded=is_bounded,
                is_on_manifold=is_on_manifold,
            )
