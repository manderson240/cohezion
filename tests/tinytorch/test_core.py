"""Tests for TinyTorch core modules (01-09).

Validates that extracted code is importable and core operations work.
"""

import numpy as np
import pytest


class TestTensorModule:
    """Test the tensor module (Module 01)."""

    def test_tensor_import(self):
        """Tensor module is importable."""
        from cohezion.tinytorch import tensor
        assert hasattr(tensor, "np")

    def test_tensor_class_exists(self):
        """Tensor class exists in the module."""
        from cohezion.tinytorch.tensor import Tensor
        assert Tensor is not None

    def test_tensor_creation(self):
        """Can create a Tensor from a list."""
        from cohezion.tinytorch.tensor import Tensor
        t = Tensor([1, 2, 3])
        assert t.shape == (3,)

    def test_tensor_arithmetic(self):
        """Basic arithmetic operations work."""
        from cohezion.tinytorch.tensor import Tensor
        a = Tensor([1.0, 2.0, 3.0])
        b = Tensor([4.0, 5.0, 6.0])
        result = a + b
        np.testing.assert_array_almost_equal(result.data, [5.0, 7.0, 9.0])

    def test_tensor_matmul(self):
        """Matrix multiplication works."""
        from cohezion.tinytorch.tensor import Tensor
        a = Tensor([[1, 2], [3, 4]])
        b = Tensor([[5, 6], [7, 8]])
        result = a @ b
        np.testing.assert_array_almost_equal(result.data, [[19, 22], [43, 50]])


class TestActivationsModule:
    """Test the activations module (Module 02)."""

    def test_activations_import(self):
        """Activations module is importable."""
        from cohezion.tinytorch import activations
        assert activations is not None


class TestLayersModule:
    """Test the layers module (Module 03)."""

    def test_layers_import(self):
        """Layers module is importable."""
        from cohezion.tinytorch import layers
        assert layers is not None


class TestLossesModule:
    """Test the losses module (Module 04)."""

    def test_losses_import(self):
        """Losses module is importable."""
        from cohezion.tinytorch import losses
        assert losses is not None


class TestDataloaderModule:
    """Test the dataloader module (Module 05)."""

    def test_dataloader_import(self):
        """Dataloader module is importable."""
        from cohezion.tinytorch import dataloader
        assert dataloader is not None


class TestAutogradModule:
    """Test the autograd module (Module 06)."""

    def test_autograd_import(self):
        """Autograd module is importable."""
        from cohezion.tinytorch import autograd
        assert autograd is not None


class TestOptimizersModule:
    """Test the optimizers module (Module 07)."""

    def test_optimizers_import(self):
        """Optimizers module is importable."""
        from cohezion.tinytorch import optimizers
        assert optimizers is not None


class TestTrainingModule:
    """Test the training module (Module 08)."""

    def test_training_import(self):
        """Training module is importable."""
        from cohezion.tinytorch import training
        assert training is not None


class TestConvolutionsModule:
    """Test the convolutions module (Module 09)."""

    def test_convolutions_import(self):
        """Convolutions module is importable."""
        from cohezion.tinytorch import convolutions
        assert convolutions is not None
