"""TinyTorch convolutions module.

Extracted from CS249R Module 09: Convolutional Neural Networks.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

from cohezion.tinytorch.tensor import Tensor


def conv2d(
    input_tensor: Tensor,
    kernel: Tensor,
    stride: int = 1,
    padding: int = 0,
) -> Tensor:
    """2D convolution operation.

    input_tensor: shape (H, W) or (C_in, H, W)
    kernel: shape (K_h, K_w) or (C_out, C_in, K_h, K_w)
    """
    data = input_tensor.data
    k = kernel.data

    # Handle simple 2D case
    if data.ndim == 2 and k.ndim == 2:
        return _conv2d_single(data, k, stride, padding)

    # Handle multi-channel case
    if data.ndim == 3 and k.ndim == 4:
        return _conv2d_multi(data, k, stride, padding)

    raise ValueError(f"Unsupported shapes: input {data.shape}, kernel {k.shape}")


def _conv2d_single(data: np.ndarray, kernel: np.ndarray, stride: int, padding: int) -> Tensor:
    """Single-channel 2D convolution."""
    if padding > 0:
        data = np.pad(data, padding, mode="constant")

    h, w = data.shape
    kh, kw = kernel.shape
    out_h = (h - kh) // stride + 1
    out_w = (w - kw) // stride + 1

    output = np.zeros((out_h, out_w), dtype=np.float32)
    for i in range(out_h):
        for j in range(out_w):
            region = data[i * stride:i * stride + kh, j * stride:j * stride + kw]
            output[i, j] = np.sum(region * kernel)

    return Tensor(output)


def _conv2d_multi(data: np.ndarray, kernels: np.ndarray, stride: int, padding: int) -> Tensor:
    """Multi-channel 2D convolution."""
    c_out, c_in, kh, kw = kernels.shape

    if padding > 0:
        data = np.pad(data, ((0, 0), (padding, padding), (padding, padding)), mode="constant")

    _, h, w = data.shape
    out_h = (h - kh) // stride + 1
    out_w = (w - kw) // stride + 1

    output = np.zeros((c_out, out_h, out_w), dtype=np.float32)
    for oc in range(c_out):
        for i in range(out_h):
            for j in range(out_w):
                region = data[:, i * stride:i * stride + kh, j * stride:j * stride + kw]
                output[oc, i, j] = np.sum(region * kernels[oc])

    return Tensor(output)


def max_pool2d(input_tensor: Tensor, kernel_size: int = 2, stride: int | None = None) -> Tensor:
    """2D max pooling."""
    if stride is None:
        stride = kernel_size

    data = input_tensor.data
    if data.ndim == 2:
        h, w = data.shape
        out_h = (h - kernel_size) // stride + 1
        out_w = (w - kernel_size) // stride + 1
        output = np.zeros((out_h, out_w), dtype=np.float32)
        for i in range(out_h):
            for j in range(out_w):
                region = data[i * stride:i * stride + kernel_size,
                              j * stride:j * stride + kernel_size]
                output[i, j] = np.max(region)
        return Tensor(output)

    if data.ndim == 3:
        c, h, w = data.shape
        out_h = (h - kernel_size) // stride + 1
        out_w = (w - kernel_size) // stride + 1
        output = np.zeros((c, out_h, out_w), dtype=np.float32)
        for ch in range(c):
            for i in range(out_h):
                for j in range(out_w):
                    region = data[ch, i * stride:i * stride + kernel_size,
                                  j * stride:j * stride + kernel_size]
                    output[ch, i, j] = np.max(region)
        return Tensor(output)

    raise ValueError(f"Expected 2D or 3D input, got {data.ndim}D")


def avg_pool2d(input_tensor: Tensor, kernel_size: int = 2, stride: int | None = None) -> Tensor:
    """2D average pooling."""
    if stride is None:
        stride = kernel_size

    data = input_tensor.data
    h, w = data.shape[-2], data.shape[-1]
    out_h = (h - kernel_size) // stride + 1
    out_w = (w - kernel_size) // stride + 1

    if data.ndim == 2:
        output = np.zeros((out_h, out_w), dtype=np.float32)
        for i in range(out_h):
            for j in range(out_w):
                region = data[i * stride:i * stride + kernel_size,
                              j * stride:j * stride + kernel_size]
                output[i, j] = np.mean(region)
        return Tensor(output)

    raise ValueError(f"Expected 2D input, got {data.ndim}D")


class Conv2d:
    """Convolutional layer with learnable kernels."""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int,
                 stride: int = 1, padding: int = 0):
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = padding

        scale = np.sqrt(2.0 / (in_channels * kernel_size * kernel_size))
        self.weights = Tensor(
            np.random.randn(out_channels, in_channels, kernel_size, kernel_size) * scale
        )
        self.bias = Tensor(np.zeros(out_channels))

    def forward(self, x: Tensor) -> Tensor:
        result = conv2d(x, self.weights, self.stride, self.padding)
        # Add bias per channel
        for c in range(self.out_channels):
            result.data[c] += self.bias.data[c]
        return result

    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)

    def parameters(self) -> list[Tensor]:
        return [self.weights, self.bias]


class MaxPool2d:
    """Max pooling layer."""

    def __init__(self, kernel_size: int = 2, stride: int | None = None):
        self.kernel_size = kernel_size
        self.stride = stride

    def forward(self, x: Tensor) -> Tensor:
        return max_pool2d(x, self.kernel_size, self.stride)

    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)
