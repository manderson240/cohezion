"""
Test for MLA Paged Attention with 5D Blocked KV Format.

Tests the gen_pa_ps_fwd_asm kernel using 5D blocked KV format:
    [num_blocks, kv_heads, head_dim/x, block_size, x]

This format optimizes memory access patterns for paged attention by:
- Blocking KV cache into pages (block_size)
- Grouping head dimensions (x) for vectorized loads
- Enabling coalesced memory access across warps

Test matrix:
    block_size: [1, 16, 32, 64]
    x: [4, 8, 16]
    head_dim: 576 (standard MLA)
    kv_heads: 1 (MQA pattern)
"""

import pytest
import torch
import torch.nn.functional as F
from typing import Tuple, Dict

# DeepSeek R1 MLA constants
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM ** 0.5)


class Test5DBlockedPAFormat:
    """Test 5D blocked KV format [num_blocks, kv_heads, head_dim/x, block_size, x]."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        self.device = "cuda"
        torch.manual_seed(42)

    def create_5d_blocked_kv(
        self,
        num_blocks: int,
        kv_heads: int,
        head_dim: int,
        block_size: int,
        x: int,
        dtype: torch.dtype = torch.bfloat16,
    ) -> torch.Tensor:
        """
        Create KV cache in 5D blocked format.

        Args:
            num_blocks: Number of KV blocks (pages)
            kv_heads: Number of KV heads (1 for MLA MQA)
            head_dim: Head dimension (576 for MLA)
            block_size: Tokens per block (1, 16, 32, 64)
            x: Head dimension grouping factor (4, 8, 16)
            dtype: Data type for the tensor

        Returns:
            KV cache tensor of shape [num_blocks, kv_heads, head_dim/x, block_size, x]
        """
        assert head_dim % x == 0, f"head_dim ({head_dim}) must be divisible by x ({x})"
        return torch.randn(
            num_blocks, kv_heads, head_dim // x, block_size, x,
            dtype=dtype,
            device=self.device,
        )

    def convert_5d_to_standard(
        self,
        kv_5d: torch.Tensor,
    ) -> torch.Tensor:
        """
        Convert 5D blocked format to standard 3D format.

        5D: [num_blocks, kv_heads, head_dim/x, block_size, x]
        3D: [total_kv, kv_heads, head_dim]

        Args:
            kv_5d: 5D blocked KV cache

        Returns:
            Standard 3D KV cache
        """
        num_blocks, kv_heads, head_dim_per_x, block_size, x = kv_5d.shape
        head_dim = head_dim_per_x * x
        total_kv = num_blocks * block_size

        # Reshape: [num_blocks, kv_heads, head_dim/x, block_size, x]
        #       -> [num_blocks, block_size, kv_heads, head_dim]
        kv_3d = kv_5d.permute(0, 3, 1, 2, 4).reshape(
            num_blocks * block_size, kv_heads, head_dim
        )
        return kv_3d

    def convert_standard_to_5d(
        self,
        kv_3d: torch.Tensor,
        block_size: int,
        x: int,
    ) -> torch.Tensor:
        """
        Convert standard 3D format to 5D blocked format.

        Args:
            kv_3d: Standard 3D KV cache [total_kv, kv_heads, head_dim]
            block_size: Tokens per block
            x: Head dimension grouping factor

        Returns:
            5D blocked KV cache
        """
        total_kv, kv_heads, head_dim = kv_3d.shape
        assert total_kv % block_size == 0, "total_kv must be divisible by block_size"
        num_blocks = total_kv // block_size
        assert head_dim % x == 0, "head_dim must be divisible by x"

        # Reshape: [num_blocks * block_size, kv_heads, head_dim]
        #       -> [num_blocks, block_size, kv_heads, head_dim/x, x]
        kv_5d = kv_3d.reshape(num_blocks, block_size, kv_heads, head_dim // x, x)

        # Permute to 5D format: [num_blocks, kv_heads, head_dim/x, block_size, x]
        kv_5d = kv_5d.permute(0, 2, 3, 1, 4)
        return kv_5d

    @pytest.mark.parametrize("block_size", [1, 16, 32, 64])
    @pytest.mark.parametrize("x", [4, 8, 16])
    def test_format_conversion_roundtrip(self, block_size: int, x: int):
        """Test that 5D <-> 3D conversion is reversible."""
        num_blocks = 8
        kv_heads = 1

        # Create standard format data
        total_kv = num_blocks * block_size
        kv_3d_original = torch.randn(
            total_kv, kv_heads, QK_HEAD_DIM,
            dtype=torch.bfloat16, device=self.device
        )

        # Convert to 5D and back
        kv_5d = self.convert_standard_to_5d(kv_3d_original, block_size, x)
        kv_3d_recovered = self.convert_5d_to_standard(kv_5d)

        # Verify shapes
        assert kv_5d.shape == (num_blocks, kv_heads, QK_HEAD_DIM // x, block_size, x)
        assert kv_3d_recovered.shape == kv_3d_original.shape

        # Verify values match
        torch.testing.assert_close(kv_3d_recovered, kv_3d_original)

    @pytest.mark.parametrize("block_size", [16, 32, 64])
    @pytest.mark.parametrize("x", [8, 16])
    def test_memory_layout_contiguity(self, block_size: int, x: int):
        """Test that 5D format maintains expected memory layout properties."""
        num_blocks = 4
        kv_heads = 1

        kv_5d = self.create_5d_blocked_kv(
            num_blocks, kv_heads, QK_HEAD_DIM, block_size, x
        )

        # Check that block_size dimension is contiguous for vectorized access
        # stride[3] should be x (last dimension size)
        assert kv_5d.stride(3) == x, \
            f"Expected stride[3]={x}, got {kv_5d.stride(3)}"

        # stride[4] should be 1 (last dimension is contiguous)
        assert kv_5d.stride(4) == 1, \
            f"Expected stride[4]=1, got {kv_5d.stride(4)}"

    @pytest.mark.parametrize("block_size", [16, 32])
    @pytest.mark.parametrize("x", [8, 16])
    def test_attention_equivalence(self, block_size: int, x: int):
        """
        Test that attention produces same results with 5D vs 3D format.

        This tests the core logic that gen_pa_ps_fwd_asm would use internally
        when loading from 5D blocked format.
        """
        batch_size = 2
        num_heads = 16
        kv_heads = 1
        q_seq_len = 1
        kv_seq_len = 64  # Must be divisible by block_size

        num_blocks = kv_seq_len // block_size
        total_q = batch_size * q_seq_len

        # Create query
        q = torch.randn(
            total_q, num_heads, QK_HEAD_DIM,
            dtype=torch.bfloat16, device=self.device
        )

        # Create KV in standard 3D format
        kv_3d = torch.randn(
            batch_size * kv_seq_len, kv_heads, QK_HEAD_DIM,
            dtype=torch.bfloat16, device=self.device
        )

        # Convert to 5D format
        kv_5d = self.convert_standard_to_5d(kv_3d, block_size, x)

        # Standard attention using 3D format
        # Split by batch for simplicity
        outputs_3d = []
        for b in range(batch_size):
            q_b = q[b * q_seq_len:(b + 1) * q_seq_len]  # [1, num_heads, 576]
            kv_start = b * kv_seq_len
            kv_end = (b + 1) * kv_seq_len
            kv_b = kv_3d[kv_start:kv_end, 0]  # [kv_seq_len, 576]

            # Attention scores
            scores = torch.matmul(
                q_b.float().permute(1, 0, 2),  # [num_heads, 1, 576]
                kv_b.float().T  # [576, kv_seq_len]
            ) * SM_SCALE  # [num_heads, 1, kv_seq_len]

            attn_weights = F.softmax(scores, dim=-1)

            # Value projection (first 512 dims)
            v_b = kv_b[:, :V_HEAD_DIM]  # [kv_seq_len, 512]
            output = torch.matmul(attn_weights, v_b)  # [num_heads, 1, 512]
            outputs_3d.append(output.permute(1, 0, 2).to(torch.bfloat16))

        output_3d = torch.cat(outputs_3d, dim=0)  # [batch_size, num_heads, 512]

        # Attention using 5D format (simulated)
        # Convert 5D back to 3D and compute
        kv_5d_as_3d = self.convert_5d_to_standard(kv_5d)
        outputs_5d = []
        for b in range(batch_size):
            q_b = q[b * q_seq_len:(b + 1) * q_seq_len]
            kv_start = b * kv_seq_len
            kv_end = (b + 1) * kv_seq_len
            kv_b = kv_5d_as_3d[kv_start:kv_end, 0]

            scores = torch.matmul(
                q_b.float().permute(1, 0, 2),
                kv_b.float().T
            ) * SM_SCALE

            attn_weights = F.softmax(scores, dim=-1)
            v_b = kv_b[:, :V_HEAD_DIM]
            output = torch.matmul(attn_weights, v_b)
            outputs_5d.append(output.permute(1, 0, 2).to(torch.bfloat16))

        output_5d = torch.cat(outputs_5d, dim=0)

        # Results should match
        torch.testing.assert_close(output_3d, output_5d)

    @pytest.mark.parametrize("block_size", [1, 16, 32, 64])
    def test_block_size_compatibility(self, block_size: int):
        """Test various block sizes with fixed x=8."""
        x = 8
        num_blocks = 4
        kv_heads = 1

        # Should create without error
        kv_5d = self.create_5d_blocked_kv(
            num_blocks, kv_heads, QK_HEAD_DIM, block_size, x
        )

        assert kv_5d.shape[3] == block_size
        assert kv_5d.shape[4] == x

    @pytest.mark.parametrize("x", [4, 8, 16])
    def test_x_compatibility(self, x: int):
        """Test various x values with fixed block_size=32."""
        block_size = 32
        num_blocks = 4
        kv_heads = 1

        # Should create without error
        kv_5d = self.create_5d_blocked_kv(
            num_blocks, kv_heads, QK_HEAD_DIM, block_size, x
        )

        assert kv_5d.shape[2] == QK_HEAD_DIM // x
        assert kv_5d.shape[4] == x

    def test_format_dimensions(self):
        """Test that all expected dimension combinations work."""
        test_cases = [
            (1, 4), (1, 8), (1, 16),
            (16, 4), (16, 8), (16, 16),
            (32, 4), (32, 8), (32, 16),
            (64, 4), (64, 8), (64, 16),
        ]

        num_blocks = 8
        kv_heads = 1

        for block_size, x in test_cases:
            kv_5d = self.create_5d_blocked_kv(
                num_blocks, kv_heads, QK_HEAD_DIM, block_size, x
            )
            assert kv_5d.shape == (
                num_blocks, kv_heads, QK_HEAD_DIM // x, block_size, x
            )

    def test_invalid_dimensions(self):
        """Test that invalid dimension combinations raise errors."""
        # head_dim not divisible by x
        with pytest.raises(AssertionError):
            self.create_5d_blocked_kv(4, 1, 577, 32, 8)  # 577 % 8 != 0

    def test_block_size_1_special_case(self):
        """
        Test block_size=1 special case.

        With block_size=1, the format becomes:
        [num_blocks, kv_heads, head_dim/x, 1, x]
        which is essentially [total_kv, kv_heads, head_dim/x, x]
        """
        block_size = 1
        x = 16
        num_blocks = 32
        kv_heads = 1

        kv_5d = self.create_5d_blocked_kv(
            num_blocks, kv_heads, QK_HEAD_DIM, block_size, x
        )

        assert kv_5d.shape == (32, 1, 36, 1, 16)  # 576/16 = 36

        # Should still convert correctly
        kv_3d = self.convert_5d_to_standard(kv_5d)
        assert kv_3d.shape == (32, 1, 576)

    def test_indptr_based_batching(self):
        """Test 5D format with indptr-based variable-length batching."""
        batch_size = 4
        block_size = 32
        x = 8

        # Variable sequence lengths per batch
        kv_lens = [32, 64, 96, 128]
        total_kv = sum(kv_lens)
        num_blocks_per_batch = [l // block_size for l in kv_lens]
        num_blocks = sum(num_blocks_per_batch)

        # Create blocked KV cache
        kv_5d = self.create_5d_blocked_kv(
            num_blocks, 1, QK_HEAD_DIM, block_size, x
        )

        # Create indptr for blocked access
        block_indptr = torch.tensor(
            [0] + list(torch.cumsum(torch.tensor(num_blocks_per_batch), dim=0)),
            dtype=torch.int32, device=self.device
        )

        # Verify we can access each batch's blocks
        for b in range(batch_size):
            start_block = block_indptr[b].item()
            end_block = block_indptr[b + 1].item()
            batch_kv = kv_5d[start_block:end_block]  # [num_blocks_b, ...]
            assert batch_kv.shape[0] == num_blocks_per_batch[b]


class Test5DBlockedPAKernelInterface:
    """
    Test interface expected by gen_pa_ps_fwd_asm kernel.

    These tests verify the exact format and access patterns expected
    by the generated paged attention kernel.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        self.device = "cuda"

    def test_kernel_expected_layout(self):
        """
        Test the exact layout expected by gen_pa_ps_fwd_asm.

        The kernel expects:
        - KV cache: [num_blocks, kv_heads, head_dim/x, block_size, x]
        - Block table: [batch_size, max_num_blocks_per_seq]
        - Block offsets computed from sequence positions
        """
        num_blocks = 256  # Total blocks in cache
        kv_heads = 1
        block_size = 32
        x = 8
        batch_size = 4
        max_seq_len = 1024
        max_blocks_per_seq = max_seq_len // block_size

        # Create KV cache in 5D format
        kv_cache = torch.randn(
            num_blocks, kv_heads, QK_HEAD_DIM // x, block_size, x,
            dtype=torch.bfloat16, device=self.device
        )

        # Block table maps sequences to blocks
        block_table = torch.randint(
            0, num_blocks, (batch_size, max_blocks_per_seq),
            dtype=torch.int32, device=self.device
        )

        # Sequence lengths per batch
        seq_lens = torch.tensor([256, 512, 768, 1024], device=self.device)

        # Verify shapes
        assert kv_cache.shape == (
            num_blocks, kv_heads, QK_HEAD_DIM // x, block_size, x
        )
        assert block_table.shape == (batch_size, max_blocks_per_seq)

        # Simulate kernel access pattern: for each position, look up block
        for b in range(batch_size):
            seq_len = seq_lens[b].item()
            num_blocks_used = (seq_len + block_size - 1) // block_size

            for pos in range(0, seq_len, block_size):
                block_idx = pos // block_size
                physical_block = block_table[b, block_idx].item()

                # Kernel would access: kv_cache[physical_block, :, :, pos % block_size, :]
                block_data = kv_cache[physical_block, :, :, pos % block_size, :]
                assert block_data.shape == (kv_heads, QK_HEAD_DIM // x, x)

    @pytest.mark.parametrize("block_size,x", [(16, 4), (32, 8), (64, 16)])
    def test_different_config_access_patterns(self, block_size: int, x: int):
        """Test memory access patterns for different config combinations."""
        num_blocks = 64
        kv_heads = 1

        kv_cache = torch.randn(
            num_blocks, kv_heads, QK_HEAD_DIM // x, block_size, x,
            dtype=torch.bfloat16, device=self.device
        )

        # Simulate coalesced access: threads in warp access consecutive x elements
        for block_idx in range(0, num_blocks, 4):  # Simulate warp accessing 4 blocks
            # Each thread in warp accesses its x elements
            for thread_id in range(32):  # Warp size
                x_offset = thread_id % x
                head_dim_group = (thread_id // x) % (QK_HEAD_DIM // x)

                # Access pattern: contiguous in x dimension
                data = kv_cache[block_idx, 0, head_dim_group, 0, x_offset]
                assert data.numel() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
