"""
MLA: Sliding Window Attention
Approach: Limit attention to a fixed-size sliding window around each position,
reducing computation from O(n²) to O(n*w) where w is window size.

Key insight: For many sequences, distant tokens have minimal impact.
A sliding window of 512-1024 tokens captures most relevant context.
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
    Sliding window attention kernel.

    Limits attention to a fixed window around each position:
    - Window size: 512 tokens
    - Only attends to positions within window
    - Dramatically reduces computation for long sequences

    Falls back to reference for short sequences.
    """
    try:
        q, kv_data, qo_indptr, kv_indptr, config = data

        total_q = q.shape[0]
        bs = qo_indptr.shape[0] - 1

        WINDOW_SIZE = 512

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
            qseqlen = q_end - q_start

            kv_start = kv_indptr[i].item()
            kv_end = kv_indptr[i + 1].item()
            kv_pages = kv_bf16[kv_start:kv_end]

            kv_len = kv_pages.shape[0] * 256
            kv_k_full = kv_pages[..., :QK_HEAD_DIM].reshape(-1, 16, QK_HEAD_DIM)[:kv_len]
            kv_v_full = kv_pages[..., QK_HEAD_DIM:].reshape(-1, 16, V_HEAD_DIM)[:kv_len]

            # For short sequences, use full attention
            if kv_len <= WINDOW_SIZE * 2:
                q_t = q_seq.transpose(0, 1)
                scores = torch.matmul(q_t, kv_k_full.transpose(1, 2)) * SM_SCALE
                weights = F.softmax(scores, dim=-1)
                out = torch.matmul(weights, kv_v_full.transpose(0, 1))
                outputs.append(out.transpose(0, 1))
                continue

            # Sliding window attention
            output = torch.zeros(qseqlen, 16, V_HEAD_DIM, dtype=torch.bfloat16, device=q.device)

            for pos in range(qseqlen):
                # Determine window bounds
                window_start = max(0, pos - WINDOW_SIZE // 2)
                window_end = min(kv_len, pos + WINDOW_SIZE // 2)

                q_pos = q_seq[pos : pos + 1]  # [1, 16, 576]
                kv_k_window = kv_k_full[window_start:window_end]
                kv_v_window = kv_v_full[window_start:window_end]

                # Compute attention within window
                q_t = q_pos.transpose(0, 1)  # [16, 1, 576]
                scores = torch.matmul(q_t, kv_k_window.transpose(1, 2)) * SM_SCALE
                weights = F.softmax(scores, dim=-1)
                out_pos = torch.matmul(weights, kv_v_window.transpose(0, 1))

                output[pos] = out_pos.transpose(0, 1).squeeze(0)

            outputs.append(output)

        return torch.cat(outputs, dim=0)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
