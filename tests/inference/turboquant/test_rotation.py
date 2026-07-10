"""Tests for cohezion.inference.turboquant.rotation."""

import pytest
import torch

from cohezion.inference.turboquant.rotation import (
    generate_qjl_matrix,
    generate_rotation_matrix,
    rotate_backward,
    rotate_forward,
)


CPU = torch.device("cpu")


def test_generate_rotation_matrix_shape_and_dtype():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    assert Pi.shape == (d, d)
    assert Pi.device.type == CPU.type
    assert Pi.dtype == torch.float32


def test_generate_rotation_matrix_is_orthogonal():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    identity = torch.eye(d)
    assert torch.allclose(Pi @ Pi.T, identity, atol=1e-5)


def test_generate_rotation_matrix_is_proper_rotation_det_plus_one():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    det = torch.linalg.det(Pi)
    assert torch.allclose(det, torch.tensor(1.0), atol=1e-5)


def test_generate_rotation_matrix_reproducible_for_same_seed():
    d = 8
    a = generate_rotation_matrix(d, CPU, seed=7)
    b = generate_rotation_matrix(d, CPU, seed=7)
    assert torch.equal(a, b)


def test_generate_rotation_matrix_differs_for_different_seed():
    d = 8
    a = generate_rotation_matrix(d, CPU, seed=1)
    b = generate_rotation_matrix(d, CPU, seed=2)
    assert not torch.equal(a, b)


def test_generate_rotation_matrix_d_one_boundary():
    Pi = generate_rotation_matrix(1, CPU)
    assert Pi.shape == (1, 1)
    # Orthogonal in 1D means the single value is +/-1.
    assert torch.allclose(Pi.abs(), torch.tensor(1.0), atol=1e-5)


def test_generate_rotation_matrix_d_zero_returns_empty():
    Pi = generate_rotation_matrix(0, CPU)
    assert Pi.shape == (0, 0)


def test_generate_rotation_matrix_negative_d_raises():
    with pytest.raises(RuntimeError):
        generate_rotation_matrix(-1, CPU)


def test_generate_rotation_matrix_float64_orthogonal_only_to_float32_precision():
    d = 8
    Pi = generate_rotation_matrix(d, CPU, dtype=torch.float64)
    assert Pi.dtype == torch.float64
    identity = torch.eye(d, dtype=torch.float64)
    product = Pi @ Pi.T
    # Internal G/QR is float32, so orthogonality holds only to float32 precision.
    assert torch.allclose(product, identity, atol=1e-5)
    assert not torch.allclose(product, identity, atol=1e-10)


def test_generate_qjl_matrix_shape_and_dtype():
    d = 8
    S = generate_qjl_matrix(d, CPU)
    assert S.shape == (d, d)
    assert S.device.type == CPU.type
    assert S.dtype == torch.float32


def test_generate_qjl_matrix_reproducible_for_same_seed():
    d = 8
    a = generate_qjl_matrix(d, CPU, seed=99)
    b = generate_qjl_matrix(d, CPU, seed=99)
    assert torch.equal(a, b)


def test_generate_qjl_matrix_differs_for_different_seed():
    d = 8
    a = generate_qjl_matrix(d, CPU, seed=1)
    b = generate_qjl_matrix(d, CPU, seed=2)
    assert not torch.equal(a, b)


def test_generate_qjl_matrix_not_orthogonalized():
    d = 8
    S = generate_qjl_matrix(d, CPU)
    identity = torch.eye(d)
    # QJL matrix is plain N(0,1) entries, not orthogonalized.
    assert not torch.allclose(S @ S.T, identity, atol=1e-5)
    # Defaults differ between the two generators so they aren't unified.
    Pi_default = generate_rotation_matrix(d, CPU)
    S_default = generate_qjl_matrix(d, CPU)
    assert not torch.equal(Pi_default, S_default)


def test_rotate_forward_backward_roundtrip():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    x = torch.randn(5, d)
    recovered = rotate_backward(rotate_forward(x, Pi), Pi)
    assert torch.allclose(recovered, x, atol=1e-5)


def test_rotate_forward_preserves_norm():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    x = torch.randn(5, d)
    y = rotate_forward(x, Pi)
    assert torch.allclose(y.norm(dim=-1), x.norm(dim=-1), atol=1e-5)


def test_rotate_forward_matches_matrix_product_for_single_vector():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    v = torch.randn(d)
    assert torch.allclose(rotate_forward(v, Pi), Pi @ v, atol=1e-5)


def test_rotate_forward_backward_batched_3d():
    B, N, d = 2, 3, 8
    Pi = generate_rotation_matrix(d, CPU)
    x = torch.randn(B, N, d)
    y = rotate_forward(x, Pi)
    assert y.shape == (B, N, d)
    recovered = rotate_backward(y, Pi)
    assert recovered.shape == (B, N, d)
    assert torch.allclose(recovered, x, atol=1e-5)


def test_rotate_forward_zero_input_returns_zero():
    d = 8
    Pi = generate_rotation_matrix(d, CPU)
    x = torch.zeros(4, d)
    y = rotate_forward(x, Pi)
    assert torch.equal(y, torch.zeros(4, d))
