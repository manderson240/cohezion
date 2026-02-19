"""TinyTorch optimizers module.

Extracted from CS249R Module 07: Optimizers.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor


class SGD:
    """Stochastic Gradient Descent optimizer.

    Updates parameters: w = w - lr * gradient
    With momentum: v = momentum * v - lr * gradient; w = w + v
    """

    def __init__(self, parameters: list[Tensor], lr: float = 0.01, momentum: float = 0.0):
        self.parameters = parameters
        self.lr = lr
        self.momentum = momentum
        self.velocities = [np.zeros_like(p.data) for p in parameters]

    def step(self, gradients: list[Tensor]):
        for i, (param, grad) in enumerate(zip(self.parameters, gradients)):
            if self.momentum > 0:
                self.velocities[i] = self.momentum * self.velocities[i] - self.lr * grad.data
                param.data += self.velocities[i]
            else:
                param.data -= self.lr * grad.data

    def zero_grad(self):
        pass  # Gradients managed externally in this simple implementation


class Adam:
    """Adam optimizer: adaptive learning rates with momentum.

    Combines benefits of AdaGrad (adaptive) and RMSProp (momentum).
    Default hyperparameters from the original paper (Kingma & Ba, 2015).
    """

    def __init__(
        self,
        parameters: list[Tensor],
        lr: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
    ):
        self.parameters = parameters
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.t = 0
        self.m = [np.zeros_like(p.data) for p in parameters]  # First moment
        self.v = [np.zeros_like(p.data) for p in parameters]  # Second moment

    def step(self, gradients: list[Tensor]):
        self.t += 1
        for i, (param, grad) in enumerate(zip(self.parameters, gradients)):
            self.m[i] = self.beta1 * self.m[i] + (1 - self.beta1) * grad.data
            self.v[i] = self.beta2 * self.v[i] + (1 - self.beta2) * grad.data ** 2

            # Bias correction
            m_hat = self.m[i] / (1 - self.beta1 ** self.t)
            v_hat = self.v[i] / (1 - self.beta2 ** self.t)

            param.data -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


class RMSProp:
    """RMSProp: adaptive learning rate using running average of squared gradients."""

    def __init__(
        self,
        parameters: list[Tensor],
        lr: float = 0.001,
        alpha: float = 0.99,
        eps: float = 1e-8,
    ):
        self.parameters = parameters
        self.lr = lr
        self.alpha = alpha
        self.eps = eps
        self.v = [np.zeros_like(p.data) for p in parameters]

    def step(self, gradients: list[Tensor]):
        for i, (param, grad) in enumerate(zip(self.parameters, gradients)):
            self.v[i] = self.alpha * self.v[i] + (1 - self.alpha) * grad.data ** 2
            param.data -= self.lr * grad.data / (np.sqrt(self.v[i]) + self.eps)


class LearningRateScheduler:
    """Adjusts learning rate during training."""

    @staticmethod
    def step_decay(initial_lr: float, epoch: int, drop_rate: float = 0.5, epochs_drop: int = 10):
        return initial_lr * (drop_rate ** (epoch // epochs_drop))

    @staticmethod
    def cosine_annealing(initial_lr: float, epoch: int, total_epochs: int):
        return initial_lr * 0.5 * (1 + np.cos(np.pi * epoch / total_epochs))

    @staticmethod
    def warmup_cosine(initial_lr: float, epoch: int, warmup_epochs: int, total_epochs: int):
        if epoch < warmup_epochs:
            return initial_lr * epoch / warmup_epochs
        return LearningRateScheduler.cosine_annealing(
            initial_lr, epoch - warmup_epochs, total_epochs - warmup_epochs
        )


OPTIMIZERS = {"sgd": SGD, "adam": Adam, "rmsprop": RMSProp}
