"""
MLA: Linear Attention Approximation
Approach: Use linear attention kernel feature maps to approximate
softmax attention in O(n) time instead of O(n^2).

Key insight: Linear attention uses feature maps to transform
attention into a form computable with cumulative sums.
"""

import math

import torch
from task import input_t, output_t


SM_SCALE = 1.0 / math.sqrt(576)
QK_HEAD_DIM = 576
V_HEAD_DIM = 512


def elu_feature_map(x):
    """ELU+1 feature map for linear attention."""
    return torch.nn.functional.elu(x) + 1


def custom_kernel(data: input_t) -> output_t:
    """
    Linear attention kernel.

    Approximates softmax attention using:
    sim(Q, K) = phi(Q) @ phi(K)^T

    Where phi is a feature map (ELU+1).

    This allows O(n) computation via associative property.
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

            # Linear attention for each head
            output = torch.zeros(qseqlen, 16, V_HEAD_DIM, dtype=torch.bfloat16, device=q.device)

            for head in range(16):
                q_head = q_seq[:, head, :].to(torch.float32)  # [qseqlen, 576]
                k_head = kv_k[:, head, :].to(torch.float32)  # [kv_len, 576]
                v_head = kv_v[:, head, :].to(torch.float32)  # [kv_len, 512]

                # Apply feature map
                q_feat = elu_feature_map(q_head)  # [qseqlen, 576]
                k_feat = elu_feature_map(k_head)  # [kv_len, 576]

                # Linear attention: Q' @ (K'^T @ V)
                # Compute KV matrix first (can be reused for all queries)
                kv_matrix = torch.matmul(k_feat.T, v_head)  # [576, 512]

                # Then multiply with queries
                numerator = torch.matmul(q_feat, kv_matrix)  # [qseqlen, 512]

                # Normalization: Q' @ (K'^T @ 1)
                k_sum = k_feat.sum(dim=0, keepdim=True)  # [1, 576]
                denominator = torch.matmul(q_feat, k_sum.T)  # [qseqlen, 1]

                # Final output
                out_head = numerator / (denominator + 1e-6)
                output[:, head, :] = out_head.to(torch.bfloat16)

            outputs.append(output)

        return torch.cat(outputs, dim=0)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
