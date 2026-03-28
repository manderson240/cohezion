"""MLA decode — torch.compile probe (Phase 8, Task 0 Probe B).

Wrap the existing torch.einsum approach in torch.compile to fuse the 3
operations (score GEMM -> softmax -> value GEMM) into a single Triton kernel.
Uses dynamic=True to avoid per-shape recompilation (8 shapes x 30-60s each).

Falls back to ref_kernel for prefill and large workloads.
"""
import torch
import torch.nn.functional as F
from reference import ref_kernel
from task import input_t, output_t

SM_SCALE = 1.0 / (576 ** 0.5)
TORCH_NATIVE_THRESHOLD = 400_000


@torch.compile(mode="max-autotune-no-cudagraphs", dynamic=True)
def _mla_sdpa_compiled(q, k, v, sm_scale):
    """SDPA with torch.compile fusion."""
    return F.scaled_dot_product_attention(q, k, v, scale=sm_scale, enable_gqa=True)


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    nq = config["num_heads"]
    kvseqlen = config["kv_seq_len"]

    total_q = q.shape[0]
    qseqlen = total_q // bs

    if qseqlen != 1:
        return ref_kernel(data)

    if bs * kvseqlen > TORCH_NATIVE_THRESHOLD:
        return ref_kernel(data)

    kv = kv_data["bf16"].view(bs, kvseqlen, 576)
    q_sdpa = q.view(bs, nq, 1, 576)
    k_sdpa = kv.unsqueeze(1)
    v_sdpa = kv[:, :, :512].unsqueeze(1)

    out = _mla_sdpa_compiled(q_sdpa, k_sdpa, v_sdpa, SM_SCALE)
    return out.squeeze(2)
