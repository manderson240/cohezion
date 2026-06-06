"""Tests for cohezion.inference.turboquant.quantizer (TurboQuantMSE / TurboQuantProd)."""

import pytest
import torch
import torch.nn.functional as F

from cohezion.inference.turboquant.quantizer import (
    MSEQuantized,
    ProdQuantized,
    TurboQuantMSE,
    TurboQuantProd,
)

CPU = torch.device("cpu")


def _mse(dim, bits=3, seed=42):
    return TurboQuantMSE(dim=dim, bits=bits, device=CPU, seed=seed)


def _prod(dim, bits=3, seed=42):
    return TurboQuantProd(dim=dim, bits=bits, device=CPU, seed=seed)


# --------------------------------------------------------------------------- #
# TurboQuantMSE
# --------------------------------------------------------------------------- #


def test_mse_quantize_norms_equal_input_l2_norm():
    torch.manual_seed(0)
    q = _mse(dim=8)
    x = torch.randn(4, 8)
    out = q.quantize(x)
    assert torch.allclose(out.norms, x.norm(dim=-1), atol=1e-6)


def test_mse_quantize_returns_packed_indices_and_bits_metadata():
    torch.manual_seed(1)
    bits = 3
    dim = 8
    q = _mse(dim=dim, bits=bits)
    x = torch.randn(5, dim)
    out = q.quantize(x)

    assert isinstance(out, MSEQuantized)
    assert out.bits == bits
    assert out.indices.dtype == torch.uint8
    # bits<=4 packs 2 values/byte, so last dim is smaller than dim
    assert out.indices.shape[-1] < dim
    assert out.norms.shape == x.shape[:-1]


def test_mse_forward_roundtrip_preserves_shape_and_direction():
    torch.manual_seed(2)
    q = _mse(dim=8, bits=3)
    x = torch.randn(6, 8)
    out = q.forward(x)
    assert out.shape == x.shape
    cos = F.cosine_similarity(x.flatten(), out.flatten(), dim=0)
    assert cos.item() >= 0.85


def test_mse_roundtrip_cosine_monotonic_in_bits():
    torch.manual_seed(3)
    x = torch.randn(16, 8)

    def cos_at(bits):
        q = _mse(dim=8, bits=bits, seed=42)
        out = q.forward(x)
        return F.cosine_similarity(x.flatten(), out.flatten(), dim=0).item()

    c2, c3, c4 = cos_at(2), cos_at(3), cos_at(4)
    assert c2 < c3 < c4


def test_mse_dequantize_zero_vector_is_finite_and_zero_norm():
    q = _mse(dim=8, bits=3)
    x = torch.zeros(3, 8)
    qd = q.quantize(x)
    assert torch.allclose(qd.norms, torch.zeros(3), atol=1e-12)
    out = q.dequantize(qd)
    assert torch.isfinite(out).all()
    assert torch.allclose(out.norm(dim=-1), torch.zeros(3), atol=1e-6)


def test_mse_dequantize_negative_values_roundtrip():
    torch.manual_seed(4)
    q = _mse(dim=8, bits=3)
    x = -torch.abs(torch.randn(5, 8)) - 0.5  # all negative components
    out = q.forward(x)
    assert torch.isfinite(out).all()
    cos = F.cosine_similarity(x.flatten(), out.flatten(), dim=0)
    assert cos.item() > 0.8


def test_mse_quantize_unbatched_single_vector_shape():
    torch.manual_seed(5)
    q = _mse(dim=8, bits=3)
    x = torch.randn(8)
    out = q.forward(x)
    assert out.shape == (8,)
    qd = q.quantize(x)
    assert qd.norms.shape == ()


def test_mse_quantize_empty_batch_raises():
    q = _mse(dim=8, bits=3)
    with pytest.raises(RuntimeError):
        q.quantize(torch.zeros(0, 8))


def test_mse_quantize_deterministic_for_same_seed():
    torch.manual_seed(6)
    x = torch.randn(4, 8)
    q1 = _mse(dim=8, bits=3, seed=99)
    q2 = _mse(dim=8, bits=3, seed=99)
    out1 = q1.quantize(x)
    out2 = q2.quantize(x)
    assert torch.equal(out1.indices, out2.indices)


# --------------------------------------------------------------------------- #
# TurboQuantProd
# --------------------------------------------------------------------------- #


def test_prod_requires_at_least_two_bits():
    with pytest.raises(AssertionError, match="at least 2 bits"):
        TurboQuantProd(dim=8, bits=1, device=CPU)


def test_prod_quantize_sets_mse_bits_to_bits_minus_one():
    torch.manual_seed(7)
    bits = 3
    q = _prod(dim=8, bits=bits)
    x = torch.randn(4, 8)
    out = q.quantize(x)
    assert out.mse_bits == bits - 1
    assert torch.allclose(out.norms, x.norm(dim=-1), atol=1e-6)


def test_prod_quantize_returns_expected_fields_and_shapes():
    torch.manual_seed(8)
    dim = 8
    q = _prod(dim=dim, bits=3)
    x = torch.randn(5, dim)
    out = q.quantize(x)

    assert isinstance(out, ProdQuantized)
    assert out.mse_indices.dtype == torch.uint8
    assert out.qjl_signs.dtype == torch.uint8
    # 8 signs per byte
    assert out.qjl_signs.shape[-1] == (dim + 7) // 8
    assert out.residual_norms.shape == x.shape[:-1]
    assert out.norms.shape == x.shape[:-1]


def test_prod_forward_roundtrip_preserves_shape_and_is_finite():
    torch.manual_seed(9)
    q = _prod(dim=8, bits=3)
    x = torch.randn(6, 8)
    out = q.forward(x)
    assert out.shape == x.shape
    assert torch.isfinite(out).all()


def test_prod_attention_score_equals_query_times_dequantized_key():
    torch.manual_seed(10)
    dim = 8
    q = _prod(dim=dim, bits=3)
    keys = torch.randn(7, dim)
    qk = q.quantize(keys)
    query = torch.randn(3, dim)

    scores = q.attention_score(query, qk)
    expected = query @ q.dequantize(qk).transpose(-2, -1)

    assert scores.shape == (3, 7)
    assert torch.allclose(scores, expected, atol=1e-4)


def test_prod_attention_score_zero_query_is_zero():
    torch.manual_seed(11)
    dim = 8
    q = _prod(dim=dim, bits=3)
    keys = torch.randn(5, dim)
    qk = q.quantize(keys)
    query = torch.zeros(4, dim)

    scores = q.attention_score(query, qk)
    assert scores.shape == (4, 5)
    assert torch.isfinite(scores).all()
    assert torch.allclose(scores, torch.zeros(4, 5), atol=1e-6)


def test_prod_attention_score_shape_for_batched_queries():
    torch.manual_seed(12)
    dim = 8
    q = _prod(dim=dim, bits=3)
    keys = torch.randn(2, 6, dim)  # batch=2, n_k=6
    qk = q.quantize(keys)
    query = torch.randn(2, 3, dim)  # batch=2, n_q=3

    scores = q.attention_score(query, qk)
    assert scores.shape == (2, 3, 6)
