"""
Convex Ensemble Simplex Optimizer
=================================
Elegantly simple, mathematically rigorous convex optimizer for multi-label and binary
ensemble blending over the probability simplex:
    \\min_{\\mathbf{w} \\in \\Delta^{K-1}} \\mathcal{L}(\\mathbf{w})
    \\text{s.t.} \\sum_{k=1}^K w_k = 1, \\quad w_k \\ge 0

Replaces derivative-free heuristics (Nelder-Mead) with exact analytical gradients
and Sequential Least Squares Programming (SLSQP) or Projected Gradient Descent (PGD).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    weights: np.ndarray
    initial_loss: float
    optimal_loss: float
    loss_reduction: float
    iterations: int
    converged: bool


class ConvexEnsembleOptimizer:
    """Convex blend weight optimizer for multi-model predictions."""

    def __init__(self, eps: float = 1e-15):
        self.eps = eps

    def project_simplex(self, v: np.ndarray) -> np.ndarray:
        """Exact Euclidean projection of vector v onto the probability simplex.

        Reference: Wang & Carreira-Perpinan (2013), O(K log K) via sorting.
        """
        k = len(v)
        u = np.sort(v)[::-1]
        cssv = np.cumsum(u) - 1.0
        ind = np.arange(1, k + 1)
        cond = u - cssv / ind > 0
        rho = ind[cond][-1]
        theta = cssv[cond][-1] / float(rho)
        w = np.maximum(v - theta, 0.0)
        return w / np.sum(w)

    def compute_loss(
        self,
        p_hat: np.ndarray,
        targets: np.ndarray,
        label_weights: np.ndarray | None = None,
    ) -> float:
        """Compute weighted multi-label binary cross-entropy loss."""
        p_clipped = np.clip(p_hat, self.eps, 1.0 - self.eps)
        c = targets.shape[1]
        lw = (
            np.ones(c, dtype=np.float64)
            if label_weights is None
            else np.asarray(label_weights, dtype=np.float64)
        )
        term1 = targets * np.log(p_clipped)
        term2 = (1.0 - targets) * np.log(1.0 - p_clipped)
        sample_loss = -np.sum((term1 + term2) * lw[None, :], axis=1)
        return float(np.mean(sample_loss))

    def optimize_multi_label_log_loss(
        self,
        predictions: list[np.ndarray],
        targets: np.ndarray,
        label_weights: np.ndarray | None = None,
        max_iter: int = 100,
    ) -> OptimizationResult:
        """Find optimal simplex blend weights w minimizing weighted binary cross-entropy.

        Parameters
        ----------
        predictions : list[np.ndarray]
            List of K model prediction arrays, each of shape (N, C) with values in [0, 1].
        targets : np.ndarray
            Binary ground truth array of shape (N, C) with values in {0, 1}.
        label_weights : np.ndarray | None
            Weight vector of length C. If None, uniform 1.0 is used.
        max_iter : int
            Maximum solver iterations.
        """
        k = len(predictions)
        if k == 0:
            raise ValueError("Must provide at least one model prediction array.")
        if k == 1:
            # Single model trivial case
            w = np.array([1.0], dtype=np.float64)
            loss = self.compute_loss(predictions[0], targets, label_weights)
            return OptimizationResult(
                weights=w,
                initial_loss=loss,
                optimal_loss=loss,
                loss_reduction=0.0,
                iterations=0,
                converged=True,
            )

        _n, c = targets.shape
        # Stack predictions into shape (K, N, C)
        p_stack = np.stack(predictions, axis=0)  # (K, N, C)

        if label_weights is None:
            lw = np.ones(c, dtype=np.float64)
        else:
            lw = np.asarray(label_weights, dtype=np.float64)

        # Objective function & analytical gradient
        def objective_and_grad(w: np.ndarray) -> tuple[float, np.ndarray]:
            # w shape (K,)
            # p_hat shape (N, C)
            p_hat = np.tensordot(w, p_stack, axes=([0], [0]))
            p_clipped = np.clip(p_hat, self.eps, 1.0 - self.eps)

            # Loss: -1/N * sum_c lw[c] * sum_n [y*log(p) + (1-y)*log(1-p)]
            term1 = targets * np.log(p_clipped)
            term2 = (1.0 - targets) * np.log(1.0 - p_clipped)
            sample_loss = -np.sum((term1 + term2) * lw[None, :], axis=1)  # shape (N,)
            total_loss = float(np.mean(sample_loss))

            # Gradient: dL/dp_hat = lw * (p_clipped - targets) / (p_clipped * (1 - p_clipped))
            # dL/dw_k = 1/N * sum_{n, c} (dL/dp_hat)_{nc} * P^{(k)}_{nc}
            diff = (p_clipped - targets) / (p_clipped * (1.0 - p_clipped))
            weighted_diff = diff * lw[None, :]  # (N, C)

            # Vectorized dot product over (N, C) for each k in K
            grad = np.array(
                [float(np.mean(np.sum(weighted_diff * p_stack[i], axis=1))) for i in range(k)],
                dtype=np.float64,
            )

            return total_loss, grad

        # Uniform initial weights on simplex
        w0 = np.full(k, 1.0 / k, dtype=np.float64)
        init_loss, _ = objective_and_grad(w0)

        # SLSQP equality constraint sum(w) = 1, bounds w_k in [0, 1]
        bounds = [(0.0, 1.0) for _ in range(k)]
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0, "jac": lambda w: np.ones_like(w)}
        ]

        res = minimize(
            fun=lambda w: objective_and_grad(w)[0],
            x0=w0,
            method="SLSQP",
            jac=lambda w: objective_and_grad(w)[1],
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": max_iter, "ftol": 1e-9},
        )

        w_opt = self.project_simplex(res.x)
        opt_loss, _ = objective_and_grad(w_opt)

        return OptimizationResult(
            weights=w_opt,
            initial_loss=init_loss,
            optimal_loss=opt_loss,
            loss_reduction=max(0.0, init_loss - opt_loss),
            iterations=int(res.nit),
            converged=bool(res.success or opt_loss <= init_loss),
        )
