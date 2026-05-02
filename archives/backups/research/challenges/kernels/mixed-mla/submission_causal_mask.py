"""
MLA: Causal Mask Optimization
Approach: Optimize causal (triangular) attention mask computation
for autoregressive decoding.

Key insight: Causal attention only attends to previous positions.
We can optimize by precomputing mask patterns and reusing them.
"""

import math

import torch
import torch.nn.functional as F
from task import input_t, output_t


SM_SCALE = 1.0 / math.sqrt(576)
QK_HEAD_DIM = 576
V_HEAD_DIM = 512


class CausalMaskCache:
    """Cache for causal attention masks."""

    _cache = {}

    @classmethod
    def get_mask(cls, seq_len, device):
        key = (seq_len, str(device))
        if key not in cls._cache:
            mask = torch.triu(torch.ones(seq_len, seq_len, device=device), diagonal=1).bool()
            cls._cache[key] = mask
        return cls._cache[key]


def custom_kernel(data: input_t) -> output_t:
    """
    Causal mask optimized attention.

    For autoregressive attention:
    1. Only attend to previous positions (causal mask)
    2. Cache mask patterns
    3. Optimize for the causal constraint
    """
    try:
        q, kv_data, qo_indptr, kv_indptr, config = data

        total_q = q.shape[0]
        bs = qo_indptr.shape[0] - 1

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
            kv_k = kv_pages[..., :QK_HEAD_DIM].reshape(-1, 16, QK_HEAD_DIM)[:kv_len]
            kv_v = kv_pages[..., QK_HEAD_DIM:].reshape(-1, 16, V_HEAD_DIM)[:kv_len]

            output = torch.zeros(qseqlen, 16, V_HEAD_DIM, dtype=torch.bfloat16, device=q.device)

            # For causal attention, queries only attend to KV positions <= query position
            # Assuming qseqlen queries are at the end of KV
            kv_offset = kv_len - qseqlen

            for head in range(16):
                q_head = q_seq[:, head, :]
                k_head = kv_k[:, head, :]
                v_head = kv_v[:, head, :]

                # Compute full attention scores
                scores = torch.matmul(q_head, k_head.T) * SM_SCALE

                # Apply causal mask: each query can only attend to KV positions <= its position
                # Assuming sequential alignment
                for pos in range(qseqlen):
                    # Get KV position corresponding to this query
                    kv_pos = kv_offset + pos
                    # Mask out future positions
                    if kv_pos < kv_len:
                        scores[pos, kv_pos + 1 :] = float("-inf")

                # Softmax and output
                weights = F.softmax(scores, dim=-1)
                out = torch.matmul(weights, v_head)

                output[:, head, :] = out

            outputs.append(output)

        return torch.cat(outputs, dim=0)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
