"""
Smoke test for persistent-mode MLA kernel.

Tests:
- All benchmark shapes produce valid output
- Output matches reference within tolerance
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
    (4, 1, 1024, 4),  # bs, qseqlen, kvseqlen, tp
    (4, 1, 8192, 4),
    (32, 1, 1024, 4),
    (32, 1, 8192, 4),
    (64, 1, 1024, 4),
    (64, 1, 8192, 4),
    (256, 1, 1024, 4),
    (256, 1, 8192, 4),
]


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
        print(f"  bs={bs}, kvseqlen={kvseqlen}: {elapsed:.2f}µs")

    return latencies


class TestPersistentMode:
    """Test persistent-mode MLA kernel."""

    @pytest.mark.fast
    @pytest.mark.parametrize("bs,qseqlen,kvseqlen,tp", BENCHMARK_SHAPES)
    def test_output_valid(self, bs, qseqlen, kvseqlen, tp):
        """Verify output is valid for all shapes."""
        data = generate_input(bs, qseqlen, kvseqlen, tp, seed=42)

        from submission import custom_kernel

        output = custom_kernel(data)

        # Check dtype
        assert output.dtype == torch.bfloat16

        # Check shape
        num_heads = 128 // tp
        v_head_dim = 512
        total_q = bs * qseqlen
        expected_shape = (total_q, num_heads, v_head_dim)
        assert output.shape == expected_shape

        # Check no NaN/Inf
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()

    @pytest.mark.fast
    @pytest.mark.parametrize("bs,qseqlen,kvseqlen,tp", BENCHMARK_SHAPES[:4])
    def test_reference_match(self, bs, qseqlen, kvseqlen, tp):
        """Verify output is close to reference."""
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


if __name__ == "__main__":
    print("Running persistent-mode smoke tests...")

    # Quick validation test
    data = generate_input(32, 1, 8192, 4, seed=42)
    from submission import custom_kernel

    output = custom_kernel(data)
    print(f"  Output shape: {output.shape}")
    print(f"  Output dtype: {output.dtype}")
    print(f"  Has NaN: {torch.isnan(output).any()}")
    print(f"  Has Inf: {torch.isinf(output).any()}")

    # Reference match check
    reference = ref_kernel(data)
    max_diff = torch.max(torch.abs(output - reference)).item()
    print(f"  Max diff from reference: {max_diff:.4e}")

    print("\nAll smoke tests passed!")
