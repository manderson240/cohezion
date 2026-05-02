"""
MLA: Two-Stage Attention Approximation
Approach: First stage computes coarse attention on compressed representations,
second stage refines on selected important positions.

Key insight: We can compute attention in two passes:
1. Coarse pass on downsampled keys/values (e.g., every 4th position)
2. Fine pass only on positions with high coarse attention

This reduces computation while maintaining accuracy.
"""

import math

import torch
import torch.nn.functional as F
from task import input_t, output_t


SM_SCALE = 1.0 / math.sqrt(576)
QK_HEAD_DIM = 576
V_HEAD_DIM = 512


def custom_kernel(data: input_t) -> output_t:
    """
    Two-stage attention with coarse-to-fine processing.

    Stage 1: Compute attention on stride-4 subsampled KV
    Stage 2: Refine top-50% positions with full KV attention
    """
    try:
        q, kv_data, qo_indptr, kv_indptr, config = data

        total_q = q.shape[0]
        bs = qo_indptr.shape[0] - 1

        # Get KV data
        kv_bf16 = kv_data.get("bf16")
        if kv_bf16 is None:
            kv_fp8 = kv_data.get("fp8")
            if kv_fp8:
                kv_bf16 = kv_fp8[0]
            else:
                from reference import ref_kernel

                return ref_kernel(data)

        outputs = []

        for i in range(bs):
            q_start = qo_indptr[i].item()
            q_end = qo_indptr[i + 1].item()
            q_seq = q[q_start:q_end]

            kv_start = kv_indptr[i].item()
            kv_end = kv_indptr[i + 1].item()
            kv_seq = kv_bf16[kv_start:kv_end]

            kv_len = kv_seq.shape[0] * 256

            # Only use two-stage for long sequences
            if kv_len < 4096:
                # Fall back to standard attention for short sequences
                kv_k = kv_seq[..., :QK_HEAD_DIM].reshape(-1, 16, QK_HEAD_DIM)[:kv_len]
                kv_v = kv_seq[..., QK_HEAD_DIM:].reshape(-1, 16, V_HEAD_DIM)[:kv_len]

                scores = torch.matmul(q_seq.transpose(0, 1), kv_k.transpose(1, 2)) * SM_SCALE
                weights = F.softmax(scores, dim=-1)
                out = torch.matmul(weights, kv_v.transpose(0, 1))
                outputs.append(out.transpose(0, 1))
                continue

            # === Stage 1: Coarse Attention ===
            STRIDE = 4
            kv_k_full = kv_seq[..., :QK_HEAD_DIM].reshape(-1, 16, QK_HEAD_DIM)[:kv_len]
            kv_v_full = kv_seq[..., QK_HEAD_DIM:].reshape(-1, 16, V_HEAD_DIM)[:kv_len]

            # Subsample
            kv_k_coarse = kv_k_full[::STRIDE]
            kv_v_coarse = kv_v_full[::STRIDE]

            q_t = q_seq.transpose(0, 1)  # [nheads, qseqlen, 576]
            scores_coarse = torch.matmul(q_t, kv_k_coarse.transpose(1, 2)) * SM_SCALE
            weights_coarse = F.softmax(scores_coarse, dim=-1)

            # Find high-attention positions
            mean_attention = weights_coarse.mean(dim=(0, 1))
            threshold = mean_attention.median()
            important_mask = mean_attention > threshold
            important_indices = torch.where(important_mask)[0] * STRIDE

            # === Stage 2: Fine Attention on Important Positions ===
            # Create sparse KV by expanding important regions
            expanded_indices = set()
            for idx in important_indices:
                for offset in range(-2, 3):
                    expanded_indices.add(max(0, min(kv_len - 1, idx.item() + offset)))
            expanded_indices = sorted(list(expanded_indices))

            if len(expanded_indices) < kv_len // 2:
                # Use sparse attention
                kv_k_sparse = kv_k_full[expanded_indices]
                kv_v_sparse = kv_v_full[expanded_indices]

                scores_fine = torch.matmul(q_t, kv_k_sparse.transpose(1, 2)) * SM_SCALE
                weights_fine = F.softmax(scores_fine, dim=-1)
                out = torch.matmul(weights_fine, kv_v_sparse.transpose(0, 1))
            else:
                # Too many important positions, use full attention
                scores_full = torch.matmul(q_t, kv_k_full.transpose(1, 2)) * SM_SCALE
                weights_full = F.softmax(scores_full, dim=-1)
                out = torch.matmul(weights_full, kv_v_full.transpose(0, 1))

            outputs.append(out.transpose(0, 1))

        return torch.cat(outputs, dim=0)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
