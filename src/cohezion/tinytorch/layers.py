"""TinyTorch layers module.

Extracted from CS249R Module 03: Neural Network Layers.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor


class Linear:
    """Fully connected layer: y = xW + b.

    Uses Xavier/Glorot initialization for stable gradient flow.
    """

    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        self.in_features = in_features
        self.out_features = out_features
        scale = np.sqrt(2.0 / (in_features + out_features))
        self.weights = Tensor(np.random.randn(in_features, out_features) * scale)
        self.bias = Tensor(np.zeros(out_features)) if bias else None
        self.input_cache = None

    def forward(self, x: Tensor) -> Tensor:
        self.input_cache = x
        result = x @ self.weights
        if self.bias is not None:
            result = result + self.bias
        return result

    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)

    def parameters(self) -> list[Tensor]:
        params = [self.weights]
        if self.bias is not None:
            params.append(self.bias)
        return params


class BatchNorm:
    """Batch normalization: normalize activations across the batch."""

    def __init__(self, num_features: int, momentum: float = 0.1, eps: float = 1e-5):
        self.num_features = num_features
        self.momentum = momentum
        self.eps = eps
        self.gamma = Tensor(np.ones(num_features))
        self.beta = Tensor(np.zeros(num_features))
        self.running_mean = np.zeros(num_features)
        self.running_var = np.ones(num_features)
        self.training = True

    def forward(self, x: Tensor) -> Tensor:
        if self.training:
            mean = x.data.mean(axis=0)
            var = x.data.var(axis=0)
            self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * mean
            self.running_var = (1 - self.momentum) * self.running_var + self.momentum * var
        else:
            mean, var = self.running_mean, self.running_var
        x_norm = (x.data - mean) / np.sqrt(var + self.eps)
        return Tensor(self.gamma.data * x_norm + self.beta.data)

    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)

    def parameters(self) -> list[Tensor]:
        return [self.gamma, self.beta]


class Dropout:
    """Dropout: randomly zero elements during training for regularization."""

    def __init__(self, p: float = 0.5):
        self.p = p
        self.training = True

    def forward(self, x: Tensor) -> Tensor:
        if not self.training:
            return x
        mask = (np.random.rand(*x.shape) > self.p).astype(np.float32)
        return Tensor(x.data * mask / (1 - self.p))

    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)


class Sequential:
    """Container that chains layers sequentially."""

    def __init__(self, layers: list):
        self.layers = layers

    def forward(self, x: Tensor) -> Tensor:
        for layer in self.layers:
            x = layer(x)
        return x

    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)

    def parameters(self) -> list[Tensor]:
        params = []
        for layer in self.layers:
            if hasattr(layer, "parameters"):
                params.extend(layer.parameters())
        return params
