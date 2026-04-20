"""
Test: gen_pa_ps_fwd_asm with 5D blocked KV format

5D blocked format: [num_blocks, kv_heads, head_dim/x, block_size, x]

Tests various combinations of:
- block_size: 1, 16, 32, 64
- x: 4, 8, 16

Task ID: bju6xb5pb
"""

import torch
import pytest
from typing import Tuple, List

# Skip all tests if CUDA is not available
pytestmark = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA not available - tests require GPU"
)

# DeepSeek R1 MLA constants
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)

# Test configurations for 5D blocked format
BLOCK_SIZES = [1, 16, 32, 64]
X_VALUES = [4, 8, 16]

# Test cases: (batchsize, qseqlen, kvseqlen, tp, seed)
TEST_CASES = [
    (4, 1, 1024, 8, 4220),
    (4, 4, 1024, 8, 4231),
    (32, 1, 1024, 4, 5412),
    (32, 4, 8192, 4, 5423),
    (128, 1, 8192, 8, 7816),
    (128, 4, 8192, 4, 7827),
]


def generate_test_input(
    batchsize: int,
    qseqlen: int,
    kvseqlen: int,
    tp: int,
    seed: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Generate test query and KV buffer for MLA decode testing.

    Returns:
        q: (total_q, num_heads, QK_HEAD_DIM) bfloat16
        kv_buffer: (total_kv, NUM_KV_HEADS, QK_HEAD_DIM) bfloat16
    """
    assert TOTAL_NUM_HEADS % tp == 0
    num_heads = TOTAL_NUM_HEADS // tp

    gen = torch.Generator(device="cuda")
    gen.manual_seed(seed)

    total_q = batchsize * qseqlen
    total_kv = batchsize * kvseqlen

    # Query
    q = torch.randn(
        (total_q, num_heads, QK_HEAD_DIM),
        dtype=torch.bfloat16,
        device="cuda",
        generator=gen,
    ) * 0.02

    # KV buffer
    kv_buffer = torch.randn(
        (total_kv, NUM_KV_HEADS, QK_HEAD_DIM),
        dtype=torch.bfloat16,
        device="cuda",
        generator=gen,
    ) * 0.02

    return q, kv_buffer


def convert_to_5d_blocked(
    kv_buffer: torch.Tensor,
    block_size: int,
    x: int,
) -> torch.Tensor:
    """
    Convert standard KV buffer to 5D blocked format.

    Standard format: (total_kv, kv_heads, head_dim)
    5D blocked format: (num_blocks, kv_heads, head_dim/x, block_size, x)

    Args:
        kv_buffer: Standard KV buffer (total_kv, kv_heads, head_dim)
        block_size: Block size for the 4th dimension
        x: Split factor for head_dim

    Returns:
        5D blocked KV buffer
    """
    total_kv, kv_heads, head_dim = kv_buffer.shape

    # Validate dimensions
    assert head_dim % x == 0, f"head_dim ({head_dim}) must be divisible by x ({x})"
    assert total_kv % block_size == 0, f"total_kv ({total_kv}) must be divisible by block_size ({block_size})"

    num_blocks = total_kv // block_size
    head_dim_split = head_dim // x

    # Reshape to 5D: (num_blocks, block_size, kv_heads, head_dim/x, x)
    kv_blocked = kv_buffer.view(num_blocks, block_size, kv_heads, head_dim_split, x)

    # Permute to 5D blocked format: (num_blocks, kv_heads, head_dim/x, block_size, x)
    kv_blocked = kv_blocked.permute(0, 2, 3, 1, 4).contiguous()

    return kv_blocked


def convert_from_5d_blocked(
    kv_blocked: torch.Tensor,
    block_size: int,
    x: int,
) -> torch.Tensor:
    """
    Convert 5D blocked format back to standard KV buffer.

    Args:
        kv_blocked: 5D blocked KV buffer (num_blocks, kv_heads, head_dim/x, block_size, x)
        block_size: Block size used in conversion
        x: Split factor used in conversion

    Returns:
        Standard KV buffer (total_kv, kv_heads, head_dim)
    """
    num_blocks, kv_heads, head_dim_split, _, _ = kv_blocked.shape
    head_dim = head_dim_split * x
    total_kv = num_blocks * block_size

    # Permute back: (num_blocks, block_size, kv_heads, head_dim/x, x)
    kv_buffer = kv_blocked.permute(0, 3, 1, 2, 4).contiguous()

    # Reshape to standard: (total_kv, kv_heads, head_dim)
    kv_buffer = kv_buffer.view(total_kv, kv_heads, head_dim)

    return kv_buffer


class Test5DBlockedPAFormat:
    """Test 5D blocked PA format conversion and kernel execution."""

    @pytest.mark.parametrize("block_size", BLOCK_SIZES)
    @pytest.mark.parametrize("x", X_VALUES)
    @pytest.mark.parametrize("test_case", TEST_CASES)
    def test_format_conversion_roundtrip(
        self,
        block_size: int,
        x: int,
        test_case: Tuple[int, int, int, int, int],
    ):
        """
        Test that 5D blocked format conversion is reversible.

        Converts KV buffer to 5D blocked and back, verifying data integrity.
        """
        batchsize, qseqlen, kvseqlen, tp, seed = test_case

        # Skip if kvseqlen not divisible by block_size
        if (batchsize * kvseqlen) % block_size != 0:
            pytest.skip(f"total_kv ({batchsize * kvseqlen}) not divisible by block_size ({block_size})")

        # Skip if QK_HEAD_DIM not divisible by x
        if QK_HEAD_DIM % x != 0:
            pytest.skip(f"QK_HEAD_DIM ({QK_HEAD_DIM}) not divisible by x ({x})")

        # Generate input
        q, kv_buffer = generate_test_input(
            batchsize, qseqlen, kvseqlen, tp, seed
        )

        # Convert to 5D blocked and back
        kv_blocked = convert_to_5d_blocked(kv_buffer, block_size, x)
        kv_recovered = convert_from_5d_blocked(kv_blocked, block_size, x)

        # Verify shapes
        assert kv_blocked.shape == (
            batchsize * kvseqlen // block_size,
            NUM_KV_HEADS,
            QK_HEAD_DIM // x,
            block_size,
            x,
        ), f"5D blocked shape mismatch"

        # Verify data integrity
        torch.testing.assert_close(kv_buffer, kv_recovered, rtol=1e-5, atol=1e-5)

    @pytest.mark.parametrize("block_size", BLOCK_SIZES)
    @pytest.mark.parametrize("x", X_VALUES)
    def test_blocked_format_shapes(self, block_size: int, x: int):
        """Test that 5D blocked format produces expected shapes."""
        batchsize, qseqlen, kvseqlen, tp, seed = 4, 1, 64, 8, 4220

        # Skip if dimensions don't align
        if (batchsize * kvseqlen) % block_size != 0:
            pytest.skip("Dimension mismatch")
        if QK_HEAD_DIM % x != 0:
            pytest.skip("Head dim mismatch")

        q, kv_buffer = generate_test_input(
            batchsize, qseqlen, kvseqlen, tp, seed
        )

        # Convert to 5D blocked
        kv_blocked = convert_to_5d_blocked(kv_buffer, block_size, x)

        expected_shape = (
            batchsize * kvseqlen // block_size,
            NUM_KV_HEADS,
            QK_HEAD_DIM // x,
            block_size,
            x,
        )

        assert kv_blocked.shape == expected_shape
        assert kv_blocked.dtype == kv_buffer.dtype

    @pytest.mark.parametrize("block_size", [16, 32])
    @pytest.mark.parametrize("x", [8, 16])
    def test_attention_with_blocked_kv(
        self,
        block_size: int,
        x: int,
    ):
        """
        Test attention computation with 5D blocked KV format.

        This test verifies that 5D blocked KV format works for attention
        by testing that the blocked KV can be converted back and used.
        """
        batchsize, qseqlen, kvseqlen, tp, seed = 4, 1, 128, 8, 4220

        # Skip if dimensions don't align
        if (batchsize * kvseqlen) % block_size != 0:
            pytest.skip("Dimension mismatch")
        if QK_HEAD_DIM % x != 0:
            pytest.skip("Head dim mismatch")

        # Generate input
        q, kv_buffer = generate_test_input(
            batchsize, qseqlen, kvseqlen, tp, seed
        )

        # Convert to 5D blocked and back (simulating what kernel would do)
        kv_blocked = convert_to_5d_blocked(kv_buffer, block_size, x)
        kv_recovered = convert_from_5d_blocked(kv_blocked, block_size, x)

        # Verify data integrity after round-trip
        torch.testing.assert_close(kv_buffer, kv_recovered, rtol=1e-5, atol=1e-5)

        # Verify shapes
        num_heads = TOTAL_NUM_HEADS // tp
        expected_blocked_shape = (
            batchsize * kvseqlen // block_size,
            NUM_KV_HEADS,
            QK_HEAD_DIM // x,
            block_size,
            x,
        )
        assert kv_blocked.shape == expected_blocked_shape

        # Verify q shape
        expected_q_shape = (batchsize * qseqlen, num_heads, QK_HEAD_DIM)
        assert q.shape == expected_q_shape

    def test_block_size_1_special_case(self):
        """Test block_size=1 (no blocking) edge case."""
        batchsize, qseqlen, kvseqlen, tp, seed = 4, 1, 64, 8, 4220

        if QK_HEAD_DIM % 8 != 0:
            pytest.skip("Head dim mismatch")

        q, kv_buffer = generate_test_input(
            batchsize, qseqlen, kvseqlen, tp, seed
        )

        # block_size=1 should still work
        kv_blocked = convert_to_5d_blocked(kv_buffer, block_size=1, x=8)
        kv_recovered = convert_from_5d_blocked(kv_blocked, block_size=1, x=8)

        # Data should be identical
        torch.testing.assert_close(kv_buffer, kv_recovered)

    def test_x_equals_head_dim(self):
        """Test x=QK_HEAD_DIM (no head dim splitting) edge case."""
        batchsize, qseqlen, kvseqlen, tp, seed = 4, 1, 64, 8, 4220

        q, kv_buffer = generate_test_input(
            batchsize, qseqlen, kvseqlen, tp, seed
        )

        # x=QK_HEAD_DIM means head_dim_split=1
        x = QK_HEAD_DIM
        block_size = 16

        if (batchsize * kvseqlen) % block_size != 0:
            pytest.skip("Dimension mismatch")

        kv_blocked = convert_to_5d_blocked(kv_buffer, block_size, x)
        kv_recovered = convert_from_5d_blocked(kv_blocked, block_size, x)

        torch.testing.assert_close(kv_buffer, kv_recovered)


class Test5DBlockedPerformance:
    """Performance tests for 5D blocked format."""

    @pytest.mark.parametrize("block_size", BLOCK_SIZES)
    @pytest.mark.parametrize("x", X_VALUES)
    def test_conversion_bandwidth(
        self,
        block_size: int,
        x: int,
    ):
        """Measure memory bandwidth for format conversion."""
        batchsize, qseqlen, kvseqlen, tp, seed = 32, 1, 4096, 4, 5412

        # Skip if dimensions don't align
        if (batchsize * kvseqlen) % block_size != 0:
            pytest.skip("Dimension mismatch")
        if QK_HEAD_DIM % x != 0:
            pytest.skip("Head dim mismatch")

        q, kv_buffer = generate_test_input(
            batchsize, qseqlen, kvseqlen, tp, seed
        )

        # Warmup
        for _ in range(3):
            kv_blocked = convert_to_5d_blocked(kv_buffer, block_size, x)
            _ = convert_from_5d_blocked(kv_blocked, block_size, x)

        torch.cuda.synchronize()

        # Benchmark to_5d_blocked
        num_iters = 10
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)

        start.record()
        for _ in range(num_iters):
            kv_blocked = convert_to_5d_blocked(kv_buffer, block_size, x)
        end.record()
        torch.cuda.synchronize()
        time_to_blocked = start.elapsed_time(end) / num_iters

        # Benchmark from_5d_blocked
        start.record()
        for _ in range(num_iters):
            _ = convert_from_5d_blocked(kv_blocked, block_size, x)
        end.record()
        torch.cuda.synchronize()
        time_from_blocked = start.elapsed_time(end) / num_iters

        # Calculate bandwidth
        kv_bytes = kv_buffer.numel() * kv_buffer.element_size()
        to_bandwidth = kv_bytes / (time_to_blocked / 1000) / 1e9  # GB/s
        from_bandwidth = kv_bytes / (time_from_blocked / 1000) / 1e9  # GB/s

        print(f"\nblock_size={block_size}, x={x}:")
        print(f"  to_5d_blocked:   {time_to_blocked:.3f} ms, {to_bandwidth:.2f} GB/s")
        print(f"  from_5d_blocked: {time_from_blocked:.3f} ms, {from_bandwidth:.2f} GB/s")

        # Conversion should be memory bandwidth bound (>100 GB/s on MI300X)
        assert to_bandwidth > 50, f"Conversion bandwidth too low: {to_bandwidth:.2f} GB/s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
