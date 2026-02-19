"""TinyTorch tensor module.

Extracted from CS249R Module 01: Tensor Foundation.
NumPy-only implementation for educational purposes.
"""

from __future__ import annotations

import numpy as np

# Constants for memory calculations
BYTES_PER_FLOAT32 = 4
KB_TO_BYTES = 1024
MB_TO_BYTES = 1024 * 1024


class Tensor:
    """Educational tensor - the foundation of ML computation.

    Wraps a NumPy array with ML-oriented operations:
    arithmetic, matrix multiplication, shape manipulation.
    """

    def __init__(self, data, dtype=np.float32):
        self.data = np.array(data, dtype=dtype)
        self.shape = self.data.shape
        self.size = self.data.size
        self.dtype = self.data.dtype

    def __repr__(self):
        return f"Tensor(data={self.data}, shape={self.shape})"

    def __str__(self):
        return f"Tensor({self.data})"

    # Arithmetic operations
    def __add__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data + other_data)

    def __radd__(self, other):
        return Tensor(self.data + other)

    def __sub__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data - other_data)

    def __rsub__(self, other):
        return Tensor(other - self.data)

    def __mul__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data * other_data)

    def __rmul__(self, other):
        return Tensor(self.data * other)

    def __truediv__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data / other_data)

    def __neg__(self):
        return Tensor(-self.data)

    def __pow__(self, exponent):
        return Tensor(self.data ** exponent)

    # Matrix operations
    def __matmul__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data @ other_data)

    def transpose(self):
        return Tensor(self.data.T)

    @property
    def T(self):
        return self.transpose()

    # Shape operations
    def reshape(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            shape = tuple(shape[0])
        return Tensor(self.data.reshape(shape))

    def flatten(self):
        return Tensor(self.data.flatten())

    # Reduction operations
    def sum(self, axis=None, keepdims=False):
        return Tensor(self.data.sum(axis=axis, keepdims=keepdims))

    def mean(self, axis=None, keepdims=False):
        return Tensor(self.data.mean(axis=axis, keepdims=keepdims))

    def max(self, axis=None, keepdims=False):
        return Tensor(self.data.max(axis=axis, keepdims=keepdims))

    def min(self, axis=None, keepdims=False):
        return Tensor(self.data.min(axis=axis, keepdims=keepdims))

    # Comparison
    def __eq__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data == other_data)

    def __lt__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data < other_data)

    def __gt__(self, other):
        other_data = other.data if isinstance(other, Tensor) else other
        return Tensor(self.data > other_data)

    # Indexing
    def __getitem__(self, idx):
        result = self.data[idx]
        if isinstance(result, np.ndarray):
            return Tensor(result)
        return result

    def __len__(self):
        return len(self.data)

    # Utility
    def numpy(self):
        return self.data.copy()

    def item(self):
        return self.data.item()

    def memory_bytes(self):
        return self.size * BYTES_PER_FLOAT32

    @staticmethod
    def zeros(shape, dtype=np.float32):
        return Tensor(np.zeros(shape, dtype=dtype))

    @staticmethod
    def ones(shape, dtype=np.float32):
        return Tensor(np.ones(shape, dtype=dtype))

    @staticmethod
    def randn(*shape):
        return Tensor(np.random.randn(*shape).astype(np.float32))

    @staticmethod
    def rand(*shape):
        return Tensor(np.random.rand(*shape).astype(np.float32))
