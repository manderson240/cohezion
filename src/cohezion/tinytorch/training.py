"""TinyTorch training module.

Extracted from CS249R Module 08: Training Loop.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor
from cohezion.tinytorch.losses import mse_loss, mse_loss_gradient


class Trainer:
    """Simple training loop for neural networks."""

    def __init__(self, model, optimizer, loss_fn=mse_loss, loss_grad_fn=mse_loss_gradient):
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.loss_grad_fn = loss_grad_fn
        self.history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    def train_epoch(self, dataloader) -> float:
        """Train for one epoch, return average loss."""
        total_loss = 0.0
        n_batches = 0

        for batch in dataloader:
            x_batch, y_batch = batch[0], batch[1]

            # Forward pass
            predictions = self.model(x_batch)
            loss = self.loss_fn(predictions, y_batch)

            # Backward pass (compute gradients)
            grad = self.loss_grad_fn(predictions, y_batch)
            # Simplified: propagate gradient through model
            gradients = self._compute_gradients(x_batch, grad)

            # Update parameters
            self.optimizer.step(gradients)

            total_loss += loss.item()
            n_batches += 1

        avg_loss = total_loss / max(n_batches, 1)
        self.history["train_loss"].append(avg_loss)
        return avg_loss

    def _compute_gradients(self, x: Tensor, output_grad: Tensor) -> list[Tensor]:
        """Compute parameter gradients via chain rule (simplified)."""
        gradients = []
        if hasattr(self.model, "parameters"):
            for param in self.model.parameters():
                # Simplified gradient: scale by output gradient magnitude
                grad = Tensor(np.ones_like(param.data) * output_grad.data.mean())
                gradients.append(grad)
        return gradients

    def evaluate(self, dataloader) -> float:
        """Evaluate model on validation data."""
        total_loss = 0.0
        n_batches = 0

        for batch in dataloader:
            x_batch, y_batch = batch[0], batch[1]
            predictions = self.model(x_batch)
            loss = self.loss_fn(predictions, y_batch)
            total_loss += loss.item()
            n_batches += 1

        avg_loss = total_loss / max(n_batches, 1)
        self.history["val_loss"].append(avg_loss)
        return avg_loss

    def fit(self, train_loader, val_loader=None, epochs: int = 10, verbose: bool = True) -> dict:
        """Full training loop."""
        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader)

            if val_loader is not None:
                val_loss = self.evaluate(val_loader)
                if verbose:
                    print(f"Epoch {epoch + 1}/{epochs} - "
                          f"train_loss: {train_loss:.4f}, val_loss: {val_loss:.4f}")
            elif verbose:
                print(f"Epoch {epoch + 1}/{epochs} - train_loss: {train_loss:.4f}")

        return self.history


class EarlyStopping:
    """Stop training when validation loss stops improving."""

    def __init__(self, patience: int = 5, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float("inf")
        self.counter = 0

    def should_stop(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
            return False
        self.counter += 1
        return self.counter >= self.patience


def compute_accuracy(predictions: Tensor, targets: Tensor) -> float:
    """Compute classification accuracy."""
    if predictions.data.ndim > 1:
        pred_classes = np.argmax(predictions.data, axis=-1)
    else:
        pred_classes = (predictions.data > 0.5).astype(int)
    target_classes = targets.data.astype(int)
    return float(np.mean(pred_classes == target_classes))
