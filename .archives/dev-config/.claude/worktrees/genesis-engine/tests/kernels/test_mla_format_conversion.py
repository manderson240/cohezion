"""
AMD MLA 5D Blocked KV Format Conversion Tests

This module provides comprehensive testing for converting between:
- Standard 3D KV format: [total_kv, kv_heads, head_dim]
- 5D Blocked KV format: [num_blocks, kv_heads, head_dim/x, block_size, x]

The 5D format is used by gen_pa_ps_fwd_asm kernel for optimized paged attention.
"""

import torch
import torch.nn.functional as F
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BlockedKVConfig:
    """Configuration for 5D blocked KV format."""
    num_blocks: int
    kv_heads: int
    head_dim: int
    block_size: int
    x: int

    def __post_init__(self):
        """Validate configuration."""
        if self.head_dim % self.x != 0:
            raise ValueError(
                f"head_dim ({self.head_dim}) must be divisible by x ({self.x}). "
                f"head_dim % x = {self.head_dim % self.x}"
            )

    @property
    def total_kv(self) -> int:
        """Total number of KV tokens."""
        return self.num_blocks * self.block_size

    @property
    def shape_5d(self) -> Tuple[int, int, int, int, int]:
        """Shape of 5D blocked format."""
        return (
            self.num_blocks,
            self.kv_heads,
            self.head_dim // self.x,
            self.block_size,
            self.x,
        )

    @property
    def shape_3d(self) -> Tuple[int, int, int]:
        """Shape of standard 3D format."""
        return (self.total_kv, self.kv_heads, self.head_dim)


class KVFormatConverter:
    """Converter between 3D standard and 5D blocked KV formats."""

    @staticmethod
    def to_5d(
        kv_3d: torch.Tensor,
        block_size: int,
        x: int,
    ) -> torch.Tensor:
        """
        Convert standard 3D KV format to 5D blocked format.

        Args:
            kv_3d: Standard format [total_kv, kv_heads, head_dim]
            block_size: Tokens per block
            x: Head dimension grouping factor

        Returns:
            5D blocked format [num_blocks, kv_heads, head_dim/x, block_size, x]
        """
        total_kv, kv_heads, head_dim = kv_3d.shape

        if total_kv % block_size != 0:
            raise ValueError(
                f"total_kv ({total_kv}) must be divisible by block_size ({block_size}). "
                f"total_kv % block_size = {total_kv % block_size}"
            )

        if head_dim % x != 0:
            raise ValueError(
                f"head_dim ({head_dim}) must be divisible by x ({x}). "
                f"head_dim % x = {head_dim % x}"
            )

        num_blocks = total_kv // block_size

        # Step 1: Reshape to separate blocks
        # [total_kv, kv_heads, head_dim] -> [num_blocks, block_size, kv_heads, head_dim]
        kv_blocked = kv_3d.reshape(num_blocks, block_size, kv_heads, head_dim)

        # Step 2: Split head_dim into groups
        # [num_blocks, block_size, kv_heads, head_dim]
        # -> [num_blocks, block_size, kv_heads, head_dim/x, x]
        kv_grouped = kv_blocked.reshape(
            num_blocks, block_size, kv_heads, head_dim // x, x
        )

        # Step 3: Permute to 5D format: [num_blocks, kv_heads, head_dim/x, block_size, x]
        # Current: [num_blocks, block_size, kv_heads, head_dim/x, x]
        # Target:  [num_blocks, kv_heads, head_dim/x, block_size, x]
        kv_5d = kv_grouped.permute(0, 2, 3, 1, 4)

        return kv_5d.contiguous()

    @staticmethod
    def from_5d(kv_5d: torch.Tensor) -> torch.Tensor:
        """
        Convert 5D blocked KV format to standard 3D format.

        Args:
            kv_5d: 5D blocked format [num_blocks, kv_heads, head_dim/x, block_size, x]

        Returns:
            Standard 3D format [total_kv, kv_heads, head_dim]
        """
        num_blocks, kv_heads, head_dim_per_x, block_size, x = kv_5d.shape
        head_dim = head_dim_per_x * x
        total_kv = num_blocks * block_size

        # Step 1: Permute from 5D to intermediate
        # [num_blocks, kv_heads, head_dim/x, block_size, x]
        # -> [num_blocks, block_size, kv_heads, head_dim/x, x]
        kv_intermediate = kv_5d.permute(0, 3, 1, 2, 4)

        # Step 2: Merge head_dim groups
        # [num_blocks, block_size, kv_heads, head_dim/x, x]
        # -> [num_blocks, block_size, kv_heads, head_dim]
        kv_merged = kv_intermediate.reshape(num_blocks, block_size, kv_heads, head_dim)

        # Step 3: Merge blocks
        # [num_blocks, block_size, kv_heads, head_dim]
        # -> [num_blocks * block_size, kv_heads, head_dim]
        kv_3d = kv_merged.reshape(total_kv, kv_heads, head_dim)

        return kv_3d

    @staticmethod
    def validate_conversion(
        kv_3d_original: torch.Tensor,
        kv_3d_recovered: torch.Tensor,
        rtol: float = 1e-5,
        atol: float = 1e-6,
    ) -> bool:
        """
        Validate that conversion roundtrip preserved data.

        Args:
            kv_3d_original: Original 3D tensor
            kv_3d_recovered: Recovered 3D tensor after roundtrip
            rtol: Relative tolerance
            atol: Absolute tolerance

        Returns:
            True if tensors are equivalent
        """
        if kv_3d_original.shape != kv_3d_recovered.shape:
            raise ValueError(
                f"Shape mismatch: {kv_3d_original.shape} vs {kv_3d_recovered.shape}"
            )

        return torch.allclose(kv_3d_original, kv_3d_recovered, rtol=rtol, atol=atol)


class TestMLAFormatConversion:
    """Test suite for MLA format conversion."""

    # DeepSeek R1 MLA constants
    KV_LORA_RANK = 512
    QK_ROPE_HEAD_DIM = 64
    QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
    V_HEAD_DIM = KV_LORA_RANK  # 512

    def setup_method(self):
        """Setup for each test method."""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        self.device = "cuda"
        self.converter = KVFormatConverter()
        torch.manual_seed(42)

    def test_basic_conversion_roundtrip(self):
        """Test basic 3D -> 5D -> 3D conversion preserves data."""
        config = BlockedKVConfig(
            num_blocks=8,
            kv_heads=1,
            head_dim=self.QK_HEAD_DIM,
            block_size=32,
            x=8,
        )

        # Create original 3D tensor
        kv_3d = torch.randn(
            config.shape_3d, dtype=torch.bfloat16, device=self.device
        )

        # Convert to 5D
        kv_5d = self.converter.to_5d(kv_3d, config.block_size, config.x)
        assert kv_5d.shape == config.shape_5d

        # Convert back to 3D
        kv_3d_recovered = self.converter.from_5d(kv_5d)
        assert kv_3d_recovered.shape == config.shape_3d

        # Validate data integrity
        assert self.converter.validate_conversion(kv_3d, kv_3d_recovered)

    def test_conversion_all_block_sizes(self):
        """Test conversion with all supported block sizes."""
        block_sizes = [1, 16, 32, 64]
        x = 8
        num_blocks = 16

        for block_size in block_sizes:
            kv_3d = torch.randn(
                num_blocks * block_size, 1, self.QK_HEAD_DIM,
                dtype=torch.bfloat16, device=self.device
            )

            kv_5d = self.converter.to_5d(kv_3d, block_size, x)
            kv_3d_recovered = self.converter.from_5d(kv_5d)

            assert self.converter.validate_conversion(kv_3d, kv_3d_recovered), \
                f"Failed for block_size={block_size}"

    def test_conversion_all_x_values(self):
        """Test conversion with all supported x values."""
        x_values = [4, 8, 16]
        block_size = 32
        num_blocks = 16

        for x in x_values:
            kv_3d = torch.randn(
                num_blocks * block_size, 1, self.QK_HEAD_DIM,
                dtype=torch.bfloat16, device=self.device
            )

            kv_5d = self.converter.to_5d(kv_3d, block_size, x)
            kv_3d_recovered = self.converter.from_5d(kv_5d)

            assert self.converter.validate_conversion(kv_3d, kv_3d_recovered), \
                f"Failed for x={x}"

    def test_conversion_full_matrix(self):
        """Test all combinations of block_size × x."""
        block_sizes = [1, 16, 32, 64]
        x_values = [4, 8, 16]
        num_blocks = 8

        for block_size in block_sizes:
            for x in x_values:
                kv_3d = torch.randn(
                    num_blocks * block_size, 1, self.QK_HEAD_DIM,
                    dtype=torch.bfloat16, device=self.device
                )

                kv_5d = self.converter.to_5d(kv_3d, block_size, x)
                kv_3d_recovered = self.converter.from_5d(kv_5d)

                assert kv_5d.shape == (num_blocks, 1, self.QK_HEAD_DIM // x, block_size, x)
                assert self.converter.validate_conversion(kv_3d, kv_3d_recovered), \
                    f"Failed for block_size={block_size}, x={x}"

    def test_5d_memory_layout(self):
        """Test that 5D tensor has expected memory layout for kernel access."""
        config = BlockedKVConfig(
            num_blocks=4,
            kv_heads=1,
            head_dim=self.QK_HEAD_DIM,
            block_size=32,
            x=8,
        )

        kv_3d = torch.randn(
            config.shape_3d, dtype=torch.bfloat16, device=self.device
        )
        kv_5d = self.converter.to_5d(kv_3d, config.block_size, config.x)

        # Expected strides for [num_blocks, kv_heads, head_dim/x, block_size, x]
        # Last dimension (x) should be contiguous
        assert kv_5d.stride(4) == 1, "Last dimension not contiguous"

        # block_size dimension stride should be x
        assert kv_5d.stride(3) == config.x, \
            f"Expected stride[3]={config.x}, got {kv_5d.stride(3)}"

        # head_dim/x dimension stride should be block_size * x
        expected_stride = config.block_size * config.x
        assert kv_5d.stride(2) == expected_stride, \
            f"Expected stride[2]={expected_stride}, got {kv_5d.stride(2)}"

    def test_invalid_block_size(self):
        """Test that invalid block_size raises appropriate error."""
        total_kv = 100  # Not divisible by block_size=32
        block_size = 32
        x = 8

        kv_3d = torch.randn(total_kv, 1, self.QK_HEAD_DIM, device=self.device)

        with pytest.raises(ValueError, match="must be divisible by block_size"):
            self.converter.to_5d(kv_3d, block_size, x)

    def test_invalid_x_value(self):
        """Test that invalid x raises appropriate error."""
        total_kv = 64
        block_size = 32
        x = 7  # 576 % 7 != 0

        kv_3d = torch.randn(total_kv, 1, self.QK_HEAD_DIM, device=self.device)

        with pytest.raises(ValueError, match="must be divisible by x"):
            self.converter.to_5d(kv_3d, block_size, x)

    def test_block_size_1_edge_case(self):
        """Test block_size=1 edge case (no actual blocking)."""
        config = BlockedKVConfig(
            num_blocks=32,
            kv_heads=1,
            head_dim=self.QK_HEAD_DIM,
            block_size=1,
            x=16,
        )

        kv_3d = torch.randn(
            config.shape_3d, dtype=torch.bfloat16, device=self.device
        )

        kv_5d = self.converter.to_5d(kv_3d, config.block_size, config.x)
        assert kv_5d.shape == (32, 1, 36, 1, 16)  # 576/16=36

        kv_3d_recovered = self.converter.from_5d(kv_5d)
        assert self.converter.validate_conversion(kv_3d, kv_3d_recovered)

    def test_large_scale_conversion(self):
        """Test conversion with larger, realistic dimensions."""
        config = BlockedKVConfig(
            num_blocks=256,  # 256 blocks
            kv_heads=1,
            head_dim=self.QK_HEAD_DIM,
            block_size=64,  # 64 tokens per block
            x=8,
        )

        kv_3d = torch.randn(
            config.shape_3d, dtype=torch.bfloat16, device=self.device
        )

        kv_5d = self.converter.to_5d(kv_3d, config.block_size, config.x)
        assert kv_5d.shape == config.shape_5d

        kv_3d_recovered = self.converter.from_5d(kv_5d)
        assert self.converter.validate_conversion(kv_3d, kv_3d_recovered)

    def test_attention_with_converted_format(self):
        """Test that attention produces same results after format conversion."""
        batch_size = 2
        num_heads = 16
        q_seq_len = 1
        kv_seq_len = 64
        block_size = 32
        x = 8

        # Create query and KV
        q = torch.randn(
            batch_size * q_seq_len, num_heads, self.QK_HEAD_DIM,
            dtype=torch.bfloat16, device=self.device
        )
        kv_3d = torch.randn(
            batch_size * kv_seq_len, 1, self.QK_HEAD_DIM,
            dtype=torch.bfloat16, device=self.device
        )

        # Compute attention with original 3D format
        outputs_3d = []
        for b in range(batch_size):
            q_b = q[b * q_seq_len:(b + 1) * q_seq_len]
            kv_b = kv_3d[b * kv_seq_len:(b + 1) * kv_seq_len, 0]

            scores = torch.matmul(
                q_b.float().permute(1, 0, 2),
                kv_b.float().T
            ) * (1.0 / (self.QK_HEAD_DIM ** 0.5))

            attn_weights = F.softmax(scores, dim=-1)
            v_b = kv_b[:, :self.V_HEAD_DIM]
            output = torch.matmul(attn_weights, v_b)
            outputs_3d.append(output.permute(1, 0, 2).to(torch.bfloat16))

        output_3d = torch.cat(outputs_3d, dim=0)

        # Convert to 5D and back, then compute attention
        kv_5d = self.converter.to_5d(kv_3d, block_size, x)
        kv_3d_converted = self.converter.from_5d(kv_5d)

        outputs_converted = []
        for b in range(batch_size):
            q_b = q[b * q_seq_len:(b + 1) * q_seq_len]
            kv_b = kv_3d_converted[b * kv_seq_len:(b + 1) * kv_seq_len, 0]

            scores = torch.matmul(
                q_b.float().permute(1, 0, 2),
                kv_b.float().T
            ) * (1.0 / (self.QK_HEAD_DIM ** 0.5))

            attn_weights = F.softmax(scores, dim=-1)
            v_b = kv_b[:, :self.V_HEAD_DIM]
            output = torch.matmul(attn_weights, v_b)
            outputs_converted.append(output.permute(1, 0, 2).to(torch.bfloat16))

        output_converted = torch.cat(outputs_converted, dim=0)

        # Results should match
        torch.testing.assert_close(output_3d, output_converted)

    def test_various_dtypes(self):
        """Test conversion with different data types."""
        dtypes = [torch.float32, torch.float16, torch.bfloat16]
        config = BlockedKVConfig(
            num_blocks=4,
            kv_heads=1,
            head_dim=self.QK_HEAD_DIM,
            block_size=32,
            x=8,
        )

        for dtype in dtypes:
            kv_3d = torch.randn(
                config.shape_3d, dtype=dtype, device=self.device
            )

            kv_5d = self.converter.to_5d(kv_3d, config.block_size, config.x)
            kv_3d_recovered = self.converter.from_5d(kv_5d)

            # For fp16/bf16, use relaxed tolerance
            rtol = 1e-3 if dtype in (torch.float16, torch.bfloat16) else 1e-5
            assert self.converter.validate_conversion(
                kv_3d, kv_3d_recovered, rtol=rtol
            ), f"Failed for dtype={dtype}"


class TestBlockedKVConfig:
    """Test BlockedKVConfig dataclass."""

    def test_valid_config(self):
        """Test valid configuration creation."""
        config = BlockedKVConfig(
            num_blocks=8,
            kv_heads=1,
            head_dim=576,
            block_size=32,
            x=8,
        )
        assert config.total_kv == 256
        assert config.shape_5d == (8, 1, 72, 32, 8)
        assert config.shape_3d == (256, 1, 576)

    def test_invalid_config(self):
        """Test that invalid config raises error."""
        with pytest.raises(ValueError, match="must be divisible by x"):
            BlockedKVConfig(
                num_blocks=8,
                kv_heads=1,
                head_dim=577,  # Not divisible by 8
                block_size=32,
                x=8,
            )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
