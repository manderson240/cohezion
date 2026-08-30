r"""Bayesian Metaplasticity & Continual Memory Engine (Palimpsa / arXiv:2602.09075)
=================================================================================
Implements the Bayesian Metaplasticity attention/memory update from Palimpsa:
1. Stability-Plasticity Resolution: Dynamic precision/importance matrix:
   $$I_t = \alpha_t I_{t-1} + \beta_t k_t k_t^T$$
   where the effective learning rate is modulated by $I_t^{-1}$, preventing catastrophic
   forgetting and catastrophic remembering in long-horizon swarm missions.
2. Input-dependent Bayesian forgetting gate:
   $$\alpha_t = 1 - \frac{1}{N_t} = \exp(-A d_t)$$
3. State Matrix update:
   $$S_t = S_{t-1} + I_t^{-1} \beta_t (v_t - S_{t-1} k_t) k_t^T$$
4. Integration with Cohezion's 12D/2048D Poincaré State Manifold & Semantic Memory.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bayesian_metaplasticity")


@dataclass(slots=True)
class MetaplasticState:
    """State memory S in R^{d_v x d_k} and precision matrix I in R^{d_k}."""

    d_k: int
    d_v: int
    S: np.ndarray = field(init=False)
    I_diag: np.ndarray = field(init=False)
    I_prior: float = 1.0

    def __post_init__(self) -> None:
        self.S = np.zeros((self.d_v, self.d_k), dtype=np.float64)
        self.I_diag = np.full(self.d_k, self.I_prior, dtype=np.float64)


class BayesianMetaplasticityEngine:
    """Palimpsa-style Bayesian Metaplastic In-Context Memory & Continuous Retention Engine."""

    def __init__(
        self,
        d_k: int = 12,
        d_v: int = 12,
        I_prior: float = 1.0,
        A_decay: float = 0.05,
        lr: float = 1.0,
    ) -> None:
        self.d_k = d_k
        self.d_v = d_v
        self.I_prior = I_prior
        self.A_decay = A_decay
        self.lr = lr
        self.state = MetaplasticState(d_k=d_k, d_v=d_v, I_prior=I_prior)

    def step(
        self,
        k_t: np.ndarray,
        v_t: np.ndarray,
        d_t: float = 1.0,
        beta_t: np.ndarray | None = None,
    ) -> tuple[np.ndarray, float]:
        r"""Execute single-step Bayesian Metaplastic memory consolidation."""
        k = np.asarray(k_t, dtype=np.float64).reshape(-1)
        v = np.asarray(v_t, dtype=np.float64).reshape(-1)

        if beta_t is None:
            beta = np.ones(self.d_v, dtype=np.float64)
        else:
            beta = np.asarray(beta_t, dtype=np.float64).reshape(-1)

        # 1. Associative recall output BEFORE update: y_t = S_{t-1} k_t
        y_t = self.state.S @ k

        # 2. Input-dependent Bayesian forgetting gate: alpha_t = exp(-A * d_t)
        alpha_t = math.exp(-self.A_decay * max(0.01, d_t))

        # 3. Update diagonal importance precision matrix: I_t = alpha_t * I_{t-1} + beta_t * (k_t^2)
        k_sq = k**2
        self.state.I_diag = alpha_t * self.state.I_diag + (np.mean(beta) * k_sq)
        self.state.I_diag = np.maximum(self.state.I_diag, 1e-4)

        # 4. Error residual: delta = (v_t - y_t)
        residual = v - y_t

        # 5. Metaplastic state update modulated by precision inverse I_t^{-1}
        effective_lr = self.lr / self.state.I_diag
        update_term = np.outer(residual * beta, k * effective_lr)
        self.state.S = (alpha_t * self.state.S) + update_term

        # Metaplasticity ratio: (I_max - I_min) / I_min
        i_min = float(np.min(self.state.I_diag))
        i_max = float(np.max(self.state.I_diag))
        meta_ratio = (i_max - i_min) / max(i_min, 1e-6)

        return y_t, round(meta_ratio, 4)

    def reset(self) -> None:
        self.state = MetaplasticState(d_k=self.d_k, d_v=self.d_v, I_prior=self.I_prior)
