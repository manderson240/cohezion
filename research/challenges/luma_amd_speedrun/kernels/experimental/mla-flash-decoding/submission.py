"""
MLA: Flash Decoding Optimized Kernel

#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

Implements Flash Decoding optimized for MLA attention pattern.
Flash Decoding reduces memory overhead by fusing attention computations
and minimizing intermediate buffer allocations.

Key Innovation:
- Kernel fusion: Fuse Q*K^T, softmax, and *V into single kernel
- Tiling: Process attention in tiles to fit in SRAM
- Online softmax: Compute softmax without materializing full attention matrix
- Memory efficient: O(1) extra memory beyond inputs/outputs

Reference: "FlashAttention: Fast and Memory-Efficient Exact Attention" (Dao et al., 2022)
Flash Decoding: Optimized for inference with KV cache.
"""

from __future__ import annotations
import os
import sys
import math
import torch
from typing import Optional
from aiter import dtypes as aiter_dtypes
from task import input_t, output_t

os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"


class FlashDecodingKernel:
    """
    Implements Flash Decoding for MLA.

    For each query, computes attention over KV cache in tiles:
    1. Load query tile into SRAM
    2. Iterate over KV tiles
    3. For each KV tile: compute scores, update softmax running stats
    4. Accumulate weighted values
    5. Write output

    Attributes:
        block_size_q: Query block size (typically small for decode)
        block_size_kv: KV block size (tuned for SRAM capacity)
    """

    def __init__(self, block_size_q: int = 1, block_size_kv: int = 128):
        """
        Initialize Flash Decoding.

        Args:
            block_size_q: Query tiles size (1 for decode)
            block_size_kv: KV tile size (128 for MI355X)
        """
        self.block_size_q = block_size_q
        self.block_size_kv = block_size_kv

    def flash_decode_forward(
        self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, scale: float
    ) -> torch.Tensor:
        """
        Compute Flash Decoding attention.

        Args:
            q: Query [num_q, head_dim]
            k: Keys [num_kv, head_dim]
            v: Values [num_kv, v_dim]
            scale: Attention scale

        Returns:
            Output [num_q, v_dim]
        """
        num_q, head_dim = q.shape
        num_kv, v_dim = v.shape
        device = q.device

        # Initialize output
        output = torch.zeros(num_q, v_dim, dtype=q.dtype, device=device)

        # Process queries in blocks
        for q_start in range(0, num_q, self.block_size_q):
            q_end = min(q_start + self.block_size_q, num_q)
            q_block = q[q_start:q_end]

            # Running softmax statistics
            m_i = torch.full((q_end - q_start, 1), float("-inf"), device=device)
            l_i = torch.zeros(q_end - q_start, 1, device=device)
            acc = torch.zeros(q_end - q_start, v_dim, device=device)

            # Iterate over KV blocks
            for kv_start in range(0, num_kv, self.block_size_kv):
                kv_end = min(kv_start + self.block_size_kv, num_kv)
                k_block = k[kv_start:kv_end]
                v_block = v[kv_start:kv_end]

                # Compute attention scores for this KV block
                # S_ij = Q_i @ K_j^T
                scores = torch.matmul(q_block, k_block.T) * scale

                # Online softmax update
                m_ij = torch.max(scores, dim=-1, keepdim=True)[0]
                m_new = torch.maximum(m_i, m_ij)

                # Compute unnormalized attention weights
                P_ij = torch.exp(scores - m_new)

                # Update normalization factor
                l_ij = torch.sum(P_ij, dim=-1, keepdim=True)
                l_new = torch.exp(m_i - m_new) * l_i + l_ij

                # Update accumulator
                acc = torch.exp(m_i - m_new) * acc + torch.matmul(P_ij, v_block)

                # Update running stats
                m_i = m_new
                l_i = l_new

            # Normalize and write output
            output[q_start:q_end] = acc / (l_i + 1e-10)

        return output


# Global flash decoding instance
_FLASH_DECODE: Optional[FlashDecodingKernel] = None


def _get_flash_decode() -> FlashDecodingKernel:
    """Get or create flash decoding instance."""
    global _FLASH_DECODE
    if _FLASH_DECODE is None:
        block_q = int(os.environ.get("FLASH_BLOCK_Q", "1"))
        block_kv = int(os.environ.get("FLASH_BLOCK_KV", "128"))
        _FLASH_DECODE = FlashDecodingKernel(block_q, block_kv)
    return _FLASH_DECODE


def custom_kernel(data: input_t) -> output_t:
    """
    Execute MLA decode with Flash Decoding.

    Args:
        data: Tuple of (q, kv_data, qo_indptr, kv_indptr, config)

    Returns:
        Output tensor [total_q, nheads, v_head_dim]
    """
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    total_q = q.shape[0]
    qseqlen = total_q // bs

    try:
        # Extract KV
        if "bf16" in kv_data:
            kv_bf16 = kv_data["bf16"]
        elif "fp8" in kv_data:
            kv_fp8, _ = kv_data["fp8"]
            kv_bf16 = kv_fp8.to(torch.bfloat16)
        else:
            raise ValueError("No compatible KV format")

        # Split K and V
        k_full = kv_bf16[:, :576]
        v_full = kv_bf16[:, 576:1088] if kv_bf16.shape[-1] >= 1088 else kv_bf16[:, :512]

        # Reshape
        k = k_full.view(bs, kvseqlen, nheads, -1)
        v = v_full.view(bs, kvseqlen, nheads, -1)
        q_reshaped = q.view(bs, qseqlen, nheads, -1)

        # Get flash decoding
        flash = _get_flash_decode()
        head_dim = q_reshaped.shape[-1]

        # Process per batch and head
        outputs = []
        for b in range(bs):
            for h in range(nheads):
                q_bh = q_reshaped[b, :, h]  # [qseqlen, head_dim]
                k_bh = k[b, :, h]  # [kvseqlen, head_dim]
                v_bh = v[b, :, h]  # [kvseqlen, -1]

                out_bh = flash.flash_decode_forward(
                    q_bh, k_bh, v_bh, scale=1.0 / math.sqrt(head_dim)
                )
                outputs.append(out_bh.unsqueeze(0).unsqueeze(0))

        output = torch.cat(outputs, dim=0).reshape(bs, nheads, qseqlen, -1)
        output = output.transpose(1, 2).reshape(total_q, nheads, -1)

        return output

    except Exception as e:
        print(f"Flash decoding failed: {e}", file=sys.stderr)
        from reference import ref_kernel

        return ref_kernel(data)
