"""TinyTorch activations module.

Extracted from CS249R Module 02: Activation Functions.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor


def relu(x: Tensor) -> Tensor:
    """ReLU: f(x) = max(0, x). Most common activation for hidden layers."""
    return Tensor(np.maximum(0, x.data))


def relu_derivative(x: Tensor) -> Tensor:
    """ReLU gradient: 1 if x > 0, else 0."""
    return Tensor((x.data > 0).astype(np.float32))


def sigmoid(x: Tensor) -> Tensor:
    """Sigmoid: f(x) = 1/(1+exp(-x)). Maps to (0,1) for binary classification."""
    clipped = np.clip(x.data, -500, 500)
    return Tensor(1.0 / (1.0 + np.exp(-clipped)))


def sigmoid_derivative(x: Tensor) -> Tensor:
    """Sigmoid gradient: s(x) * (1 - s(x))."""
    s = sigmoid(x)
    return Tensor(s.data * (1 - s.data))


def tanh(x: Tensor) -> Tensor:
    """Tanh: maps to (-1,1)."""
    return Tensor(np.tanh(x.data))


def tanh_derivative(x: Tensor) -> Tensor:
    """Tanh gradient: 1 - tanh(x)^2."""
    t = np.tanh(x.data)
    return Tensor(1.0 - t ** 2)


def leaky_relu(x: Tensor, alpha: float = 0.01) -> Tensor:
    """Leaky ReLU: allows small gradient for negative values."""
    return Tensor(np.where(x.data > 0, x.data, alpha * x.data))


def softmax(x: Tensor, axis: int = -1) -> Tensor:
    """Softmax: converts logits to probabilities that sum to 1."""
    shifted = x.data - x.data.max(axis=axis, keepdims=True)
    exp_x = np.exp(shifted)
    return Tensor(exp_x / exp_x.sum(axis=axis, keepdims=True))


def gelu(x: Tensor) -> Tensor:
    """GELU: Gaussian Error Linear Unit. Used in Transformers."""
    return Tensor(0.5 * x.data * (1 + np.tanh(
        np.sqrt(2 / np.pi) * (x.data + 0.044715 * x.data ** 3)
    )))


def swish(x: Tensor, beta: float = 1.0) -> Tensor:
    """Swish: f(x) = x * sigmoid(beta*x). Self-gated activation."""
    sig = 1.0 / (1.0 + np.exp(-beta * np.clip(x.data, -500, 500)))
    return Tensor(x.data * sig)


ACTIVATIONS = {
    "relu": relu, "sigmoid": sigmoid, "tanh": tanh,
    "leaky_relu": leaky_relu, "softmax": softmax,
    "gelu": gelu, "swish": swish,
}
