"""TinyTorch autograd module.

Extracted from CS249R Module 06: Automatic Differentiation.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np


class Value:
    """Scalar value with automatic differentiation.

    Tracks computation graph and computes gradients via backpropagation.
    Inspired by Andrej Karpathy's micrograd.
    """

    def __init__(self, data: float, children: tuple = (), op: str = ""):
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = set(children)
        self._op = op

    def __repr__(self):
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f})"

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __radd__(self, other):
        return self + other

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def __rmul__(self, other):
        return self * other

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return (-self) + other

    def __neg__(self):
        return self * -1

    def __truediv__(self, other):
        return self * other ** -1

    def __pow__(self, exponent):
        assert isinstance(exponent, (int, float))
        out = Value(self.data ** exponent, (self,), f"**{exponent}")

        def _backward():
            self.grad += exponent * (self.data ** (exponent - 1)) * out.grad
        out._backward = _backward
        return out

    def relu(self):
        out = Value(max(0, self.data), (self,), "relu")

        def _backward():
            self.grad += (out.data > 0) * out.grad
        out._backward = _backward
        return out

    def tanh(self):
        t = np.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward():
            self.grad += (1 - t ** 2) * out.grad
        out._backward = _backward
        return out

    def exp(self):
        e = np.exp(self.data)
        out = Value(e, (self,), "exp")

        def _backward():
            self.grad += e * out.grad
        out._backward = _backward
        return out

    def log(self):
        out = Value(np.log(self.data), (self,), "log")

        def _backward():
            self.grad += (1.0 / self.data) * out.grad
        out._backward = _backward
        return out

    def backward(self):
        """Compute gradients via reverse-mode autodiff (backpropagation)."""
        topo = []
        visited = set()

        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)

        build_topo(self)
        self.grad = 1.0

        for v in reversed(topo):
            v._backward()

    def zero_grad(self):
        """Reset gradient to zero."""
        self.grad = 0.0


class Neuron:
    """Single neuron with weights, bias, and optional activation."""

    def __init__(self, n_inputs: int, nonlin: bool = True):
        self.w = [Value(np.random.uniform(-1, 1)) for _ in range(n_inputs)]
        self.b = Value(0.0)
        self.nonlin = nonlin

    def __call__(self, x: list[Value]) -> Value:
        act = sum((wi * xi for wi, xi in zip(self.w, x)), self.b)
        return act.relu() if self.nonlin else act

    def parameters(self) -> list[Value]:
        return self.w + [self.b]


class Layer:
    """Layer of neurons."""

    def __init__(self, n_inputs: int, n_outputs: int, nonlin: bool = True):
        self.neurons = [Neuron(n_inputs, nonlin) for _ in range(n_outputs)]

    def __call__(self, x: list[Value]) -> list[Value]:
        out = [n(x) for n in self.neurons]
        return out[0] if len(out) == 1 else out

    def parameters(self) -> list[Value]:
        return [p for n in self.neurons for p in n.parameters()]


class MLP:
    """Multi-layer perceptron using autograd Values."""

    def __init__(self, n_inputs: int, layer_sizes: list[int]):
        sizes = [n_inputs] + layer_sizes
        self.layers = [
            Layer(sizes[i], sizes[i + 1], nonlin=(i != len(layer_sizes) - 1))
            for i in range(len(layer_sizes))
        ]

    def __call__(self, x: list[Value]) -> list[Value] | Value:
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self) -> list[Value]:
        return [p for layer in self.layers for p in layer.parameters()]

    def zero_grad(self):
        for p in self.parameters():
            p.zero_grad()
