"""TinyTorch losses module.

Extracted from CS249R Module 04: Loss Functions.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor


def mse_loss(predictions: Tensor, targets: Tensor) -> Tensor:
    """Mean Squared Error loss for regression."""
    diff = predictions.data - targets.data
    return Tensor(np.mean(diff ** 2))


def mse_loss_gradient(predictions: Tensor, targets: Tensor) -> Tensor:
    """Gradient of MSE loss w.r.t. predictions."""
    n = predictions.data.size
    return Tensor(2.0 * (predictions.data - targets.data) / n)


def cross_entropy_loss(logits: Tensor, targets: Tensor) -> Tensor:
    """Cross-entropy loss for multi-class classification."""
    shifted = logits.data - logits.data.max(axis=-1, keepdims=True)
    exp_logits = np.exp(shifted)
    probs = exp_logits / exp_logits.sum(axis=-1, keepdims=True)
    probs = np.clip(probs, 1e-7, 1 - 1e-7)

    if targets.data.ndim == 1:
        batch_size = logits.data.shape[0]
        log_probs = -np.log(probs[np.arange(batch_size), targets.data.astype(int)])
        return Tensor(np.mean(log_probs))
    return Tensor(-np.mean(np.sum(targets.data * np.log(probs), axis=-1)))


def binary_cross_entropy_loss(predictions: Tensor, targets: Tensor) -> Tensor:
    """Binary cross-entropy for binary classification."""
    p = np.clip(predictions.data, 1e-7, 1 - 1e-7)
    loss = -(targets.data * np.log(p) + (1 - targets.data) * np.log(1 - p))
    return Tensor(np.mean(loss))


def huber_loss(predictions: Tensor, targets: Tensor, delta: float = 1.0) -> Tensor:
    """Huber loss: MSE for small errors, MAE for large. Robust to outliers."""
    diff = np.abs(predictions.data - targets.data)
    loss = np.where(diff <= delta, 0.5 * diff ** 2, delta * (diff - 0.5 * delta))
    return Tensor(np.mean(loss))


def l1_loss(predictions: Tensor, targets: Tensor) -> Tensor:
    """L1 (Mean Absolute Error) loss."""
    return Tensor(np.mean(np.abs(predictions.data - targets.data)))


LOSSES = {
    "mse": mse_loss, "cross_entropy": cross_entropy_loss,
    "binary_cross_entropy": binary_cross_entropy_loss,
    "huber": huber_loss, "l1": l1_loss,
}
