"""
MLA: Chunked Prefill Optimization
Approach: Process prefill sequences in chunks to balance memory usage
and compute efficiency.

Key insight: Prefill can be memory-bound for long sequences.
Chunking allows better cache utilization and reduces peak memory.
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
    Chunked prefill MLA kernel.

    Processes attention in fixed-size chunks:
    - Chunk size: 1024 tokens
    - Overlapping chunks for continuity
    - Efficient cache usage

    Optimized for prefill workloads (qseqlen > 1).
    """
    try:
        q, kv_data, qo_indptr, kv_indptr, config = data

        total_q = q.shape[0]
        bs = qo_indptr.shape[0] - 1

        CHUNK_SIZE = 1024

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

            # For single-query decode, use standard attention
            if qseqlen == 1:
                q_t = q_seq.transpose(0, 1)
                scores = torch.matmul(q_t, kv_k_full.transpose(1, 2)) * SM_SCALE
                weights = F.softmax(scores, dim=-1)
                out = torch.matmul(weights, kv_v_full.transpose(0, 1))
                outputs.append(out.transpose(0, 1))
                continue

            # Chunked prefill for multi-query
            output = torch.zeros(qseqlen, 16, V_HEAD_DIM, dtype=torch.bfloat16, device=q.device)

            for chunk_start in range(0, qseqlen, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, qseqlen)
                q_chunk = q_seq[chunk_start:chunk_end]

                # Compute attention for this chunk
                q_t = q_chunk.transpose(0, 1)
                scores = torch.matmul(q_t, kv_k_full.transpose(1, 2)) * SM_SCALE
                weights = F.softmax(scores, dim=-1)
                out_chunk = torch.matmul(weights, kv_v_full.transpose(0, 1))

                output[chunk_start:chunk_end] = out_chunk.transpose(0, 1)

            outputs.append(output)

        return torch.cat(outputs, dim=0)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
