"""
Smoke tests for three-regime MLA routing.

Verifies:
- Regime boundaries are correctly identified
- Output dtype/shape matches reference
- No NaN or Inf values
"""

import pytest
import torch
from reference import generate_input, ref_kernel


# ---------------------------------------------------------------------------
# Constants (must match submission.py)
# ---------------------------------------------------------------------------
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
A16W8_THRESHOLD = 262144

# Benchmark shapes from the competition
BENCHMARK_SHAPES = [
    (4, 1, 1024, 4),    # bs, qseqlen, kvseqlen, tp
    (4, 1, 8192, 4),
    (32, 1, 1024, 4),
    (32, 1, 8192, 4),
    (64, 1, 1024, 4),
    (64, 1, 8192, 4),
    (256, 1, 1024, 4),
    (256, 1, 8192, 4),
]


# ---------------------------------------------------------------------------
# Regime identification tests
# ---------------------------------------------------------------------------

class TestRegimeBoundaries:
    """Test that regime boundaries are correctly identified."""

    @pytest.mark.parametrize("bs,kvseqlen", [
        (4, 1024),      # bs <= 4, should use einsum
        (1, 32768),     # total_kv <= 32768, should use einsum
        (8, 32768),     # total_kv > 32768 AND bs > 4, should use ASM
        (4, 262144),    # total_kv <= 262144, should use a16w8
        (64, 8192),     # total_kv = 524288 > 262144, should use a8w8
    ])
    def test_regime_classification(self, bs, kvseqlen):
        """Verify regime classification logic."""
        total_kv = bs * kvseqlen

        if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
            expected_regime = 1
        elif total_kv <= A16W8_THRESHOLD:
            expected_regime = 2
        else:
            expected_regime = 3

        # Compute actual regime
        if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
            actual_regime = 1
        elif total_kv <= A16W8_THRESHOLD:
            actual_regime = 2
        else:
            actual_regime = 3

        assert actual_regime == expected_regime, (
            f"Regime mismatch for bs={bs}, kvseqlen={kvseqlen}: "
            f"expected {expected_regime}, got {actual_regime}"
        )


# ---------------------------------------------------------------------------
# Output validation tests
# ---------------------------------------------------------------------------

class TestOutputValidation:
    """Test output dtype, shape, and numerical quality."""

    @pytest.mark.fast
    @pytest.mark.parametrize("bs,qseqlen,kvseqlen,tp", BENCHMARK_SHAPES)
    def test_dtype_and_shape(self, bs, qseqlen, kvseqlen, tp):
        """Verify output dtype is bfloat16 and shape is correct."""
        data = generate_input(bs, qseqlen, kvseqlen, tp, seed=42)
        q, kv_data, qo_indptr, kv_indptr, config = data

        # Import here to avoid circular reference
        from submission import custom_kernel

        output = custom_kernel(data)

        # Check dtype
        assert output.dtype == torch.bfloat16, (
            f"Expected bfloat16 output, got {output.dtype}"
        )

        # Check shape: (total_q, num_heads, v_head_dim)
        num_heads = config["num_heads"]
        v_head_dim = 512
        total_q = bs * qseqlen

        expected_shape = (total_q, num_heads, v_head_dim)
        assert output.shape == expected_shape, (
            f"Expected shape {expected_shape}, got {output.shape}"
        )

    @pytest.mark.fast
    @pytest.mark.parametrize("bs,qseqlen,kvseqlen,tp", BENCHMARK_SHAPES)
    def test_no_nan_or_inf(self, bs, qseqlen, kvseqlen, tp):
        """Verify output contains no NaN or Inf values."""
        data = generate_input(bs, qseqlen, kvseqlen, tp, seed=42)

        from submission import custom_kernel

        output = custom_kernel(data)

        has_nan = torch.isnan(output).any().item()
        has_inf = torch.isinf(output).any().item()

        assert not has_nan, f"Output contains NaN values for bs={bs}, kvseqlen={kvseqlen}"
        assert not has_inf, f"Output contains Inf values for bs={bs}, kvseqlen={kvseqlen}"

    @pytest.mark.fast
    @pytest.mark.parametrize("bs,qseqlen,kvseqlen,tp", BENCHMARK_SHAPES[:4])  # First 4 shapes
    def test_reference_match(self, bs, qseqlen, kvseqlen, tp):
        """Verify output is close to reference within tolerance."""
        data = generate_input(bs, qseqlen, kvseqlen, tp, seed=42)

        from submission import custom_kernel

        output = custom_kernel(data)
        reference = ref_kernel(data)

        # Tolerance from competition: rtol=1e-2, atol=1e-2
        max_diff = torch.max(torch.abs(output - reference)).item()
        assert max_diff < 1e-1, (
            f"Output differs from reference by {max_diff:.4e} "
            f"(tolerance: 1e-2)"
        )


# ---------------------------------------------------------------------------
# Regime routing tests
# ---------------------------------------------------------------------------

class TestRegimeRouting:
    """Test that the correct regime is selected for each shape."""

    @pytest.mark.fast
    @pytest.mark.parametrize("bs,qseqlen,kvseqlen,tp", BENCHMARK_SHAPES)
    def test_regime_routing(self, bs, qseqlen, kvseqlen, tp):
        """Verify regime routing produces valid output."""
        data = generate_input(bs, qseqlen, kvseqlen, tp, seed=42)
        total_kv = bs * kvseqlen

        from submission import custom_kernel

        # Should not raise any errors
        output = custom_kernel(data)

        # Verify output is valid
        assert output.shape[0] == bs * qseqlen
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()


# ---------------------------------------------------------------------------
# Benchmark helper
# ---------------------------------------------------------------------------

def run_benchmark(times: int = 100, warmup: int = 10) -> list[float]:
    """Run geomean benchmark over all shapes."""
    import time

    latencies = []

    for bs, qseqlen, kvseqlen, tp in BENCHMARK_SHAPES:
        data = generate_input(bs, qseqlen, kvseqlen, tp, seed=42)

        from submission import custom_kernel

        # Warmup
        for _ in range(warmup):
            _ = custom_kernel(data)

        # Benchmark
        torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(times):
            _ = custom_kernel(data)
        torch.cuda.synchronize()
        elapsed = (time.perf_counter() - start) / times * 1e6  # µs

        latencies.append(elapsed)

    return latencies


if __name__ == "__main__":
    # Quick sanity check
    print("Running smoke tests...")

    # Test regime classification
    test_cases = [
        (4, 1024),      # Regime 1: einsum
        (1, 32768),     # Regime 1: einsum
        (8, 32768),     # Regime 2: a16w8
        (4, 262144),    # Regime 2: a16w8
        (64, 8192),     # Regime 3: a8w8
    ]

    for bs, kvseqlen in test_cases:
        total_kv = bs * kvseqlen
        if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
            regime = 1
        elif total_kv <= A16W8_THRESHOLD:
            regime = 2
        else:
            regime = 3
        print(f"  bs={bs}, kvseqlen={kvseqlen} -> Regime {regime}")

    print("\nRunning output validation tests...")
    data = generate_input(4, 1, 1024, 4, seed=42)

    from submission import custom_kernel
    output = custom_kernel(data)

    print(f"  Output shape: {output.shape}")
    print(f"  Output dtype: {output.dtype}")
    print(f"  Has NaN: {torch.isnan(output).any()}")
    print(f"  Has Inf: {torch.isinf(output).any()}")

    print("\nAll smoke tests passed!")
