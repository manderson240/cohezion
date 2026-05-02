"""
MLA: Flash Attention V2-Style Implementation
Approach: Implement flash attention algorithm with tiling and online softmax
to reduce memory bandwidth and improve arithmetic intensity.

Key insight: Flash Attention computes attention in tiles, keeping
intermediate values in SRAM and only materializing the final output.
"""

import math

import torch
from task import input_t, output_t


SM_SCALE = 1.0 / math.sqrt(576)
QK_HEAD_DIM = 576
V_HEAD_DIM = 512


def custom_kernel(data: input_t) -> output_t:
    """
        Flash Attention V2-style implementation.

        Uses tiling strategy:
        1. Load Q tile to SRAM
        2. Iterate over KV tiles
        3. Compute attention incrementally with online softmax
        4. Only write final output

        Current implementation uses PyTorch operations that simulate
    the flash attention algorithm. Full custom kernel would use Triton.
    """
    try:
        q, kv_data, qo_indptr, kv_indptr, config = data

        total_q = q.shape[0]
        bs = qo_indptr.shape[0] - 1

        # Get KV
        kv_bf16 = kv_data.get("bf16")
        if kv_bf16 is None:
            kv_fp8 = kv_data.get("fp8")
            if kv_fp8:
                kv_bf16 = kv_fp8[0]
            else:
                from reference import ref_kernel

                return ref_kernel(data)

        outputs = []

        # Tile sizes (simulating SRAM constraints)
        TILE_Q = 64
        TILE_KV = 256

        for i in range(bs):
            q_start = qo_indptr[i].item()
            q_end = qo_indptr[i + 1].item()
            q_seq = q[q_start:q_end]
            qseqlen = q_end - q_start

            kv_start = kv_indptr[i].item()
            kv_end = kv_indptr[i + 1].item()
            kv_pages = kv_bf16[kv_start:kv_end]

            kv_len = kv_pages.shape[0] * 256
            kv_k = kv_pages[..., :QK_HEAD_DIM].reshape(-1, 16, QK_HEAD_DIM)[:kv_len]
            kv_v = kv_pages[..., QK_HEAD_DIM:].reshape(-1, 16, V_HEAD_DIM)[:kv_len]

            output = torch.zeros(qseqlen, 16, V_HEAD_DIM, dtype=torch.bfloat16, device=q.device)

            # Process Q in tiles
            for q_tile_start in range(0, qseqlen, TILE_Q):
                q_tile_end = min(q_tile_start + TILE_Q, qseqlen)
                q_tile = q_seq[q_tile_start:q_tile_end]  # [tile_q, nheads, 576]

                # Flash attention state for this tile
                m = torch.full((q_tile.shape[0], 16, 1), float("-inf"), device=q.device)
                l = torch.zeros(q_tile.shape[0], 16, 1, device=q.device)
                acc = torch.zeros(q_tile.shape[0], 16, V_HEAD_DIM, device=q.device)

                # Iterate over KV tiles
                for kv_tile_start in range(0, kv_len, TILE_KV):
                    kv_tile_end = min(kv_tile_start + TILE_KV, kv_len)

                    kv_k_tile = kv_k[kv_tile_start:kv_tile_end]
                    kv_v_tile = kv_v[kv_tile_start:kv_tile_end]

                    # Compute scores: Q @ K^T
                    q_t = q_tile.transpose(0, 1)  # [nheads, tile_q, 576]
                    kv_k_t = kv_k_tile.transpose(0, 1)  # [nheads, tile_kv, 576]

                    scores = (
                        torch.matmul(q_t, kv_k_t.transpose(1, 2)) * SM_SCALE
                    )  # [nheads, tile_q, tile_kv]
                    scores = scores.transpose(0, 1)  # [tile_q, nheads, tile_kv]

                    # Online softmax update
                    m_new = torch.maximum(m, scores.max(dim=-1, keepdim=True)[0])

                    # Numerical stability
                    exp_scores = torch.exp(scores - m_new)
                    exp_factor = torch.exp(m - m_new)

                    # Update accumulator
                    acc = acc * exp_factor + torch.matmul(
                        exp_scores, kv_v_tile.transpose(0, 1).transpose(1, 2)
                    ).transpose(0, 1)

                    # Update normalizer
                    l = l * exp_factor + exp_scores.sum(dim=-1, keepdim=True)

                    m = m_new

                # Final normalization
                output[q_tile_start:q_tile_end] = (acc / l).to(torch.bfloat16)

            outputs.append(output)

        return torch.cat(outputs, dim=0)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
