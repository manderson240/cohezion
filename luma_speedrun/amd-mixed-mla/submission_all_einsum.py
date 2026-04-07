#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Approach C: All-einsum — pure BF16 attention for every shape.

Zero aiter dispatch overhead. No metadata computation, no page tables,
no FP8 quantization, no kernel launch latency for get_mla_metadata_v1.

For small shapes (total_kv <= 32K) the einsum is memory-bound and fast.
For large shapes (total_kv > 262K) it will be slower than the ASM kernel,
but the geomean may still benefit from zero-overhead small shapes.

The 10% tolerance means approximate attention is fine — and BF16 einsum
is exact BF16 (same precision as the BF16 reference path).

Shapes from RANKED_SHAPES.md:
  Shape 1: bs=4,   kv=1024  -> total=4K    einsum fast
  Shape 2: bs=4,   kv=8192  -> total=32K   einsum fast
  Shape 3: bs=32,  kv=1024  -> total=32K   einsum fast
  Shape 4: bs=32,  kv=8192  -> total=262K  may be borderline
  Shape 5: bs=64,  kv=1024  -> total=65K   einsum moderate
  Shape 6: bs=64,  kv=8192  -> total=524K  einsum slower
  Shape 7: bs=256, kv=1024  -> total=262K  einsum moderate
  Shape 8: bs=256, kv=8192  -> total=2M    einsum slow

Uses batched matrix multiply (bmm) instead of einsum for shapes where
batch dimension can be exploited, falling back to einsum when needed.
"""

import torch
from task import input_t, output_t

NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)


def _einsum_attention(q, kv_bf16, bs, kvseqlen):
    """BF16 attention via einsum. No aiter, no FP8, no metadata."""
    kv = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    # scores: (bs, num_heads, 1, kvseqlen)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    # output: (bs*1, num_heads, v_head_dim)
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, NUM_HEADS, V_HEAD_DIM)
        .to(torch.bfloat16)
    )


def _bmm_attention(q, kv_bf16, bs, kvseqlen):
    """BF16 attention via bmm — may be faster for large bs on MI355X.

    q:        (bs, NUM_HEADS, QK_HEAD_DIM)
    kv_bf16:  (bs*kvseqlen, 1, QK_HEAD_DIM) -> reshaped to (bs, kvseqlen, QK_HEAD_DIM)
    """
    kv = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)  # (bs, kv, dim)
    q_3d = q.view(bs, NUM_HEADS, QK_HEAD_DIM)  # (bs, heads, dim)

    # scores: (bs, heads, kv) via batched matmul
    # q_3d @ kv.transpose(-1,-2): (bs, heads, dim) @ (bs, dim, kv)
    scores = torch.bmm(
        q_3d,  # (bs, heads, dim)
        kv.transpose(1, 2),  # (bs, dim, kv)
    ).mul_(SM_SCALE)  # (bs, heads, kv)

    weights = torch.softmax(scores, dim=-1)  # (bs, heads, kv)

    v = kv[:, :, :V_HEAD_DIM]  # (bs, kv, v_dim)

    # output: (bs, heads, v_dim)
    out = torch.bmm(weights, v)  # (bs, heads, kv) @ (bs, kv, v_dim)

    # Reshape to (bs*1, heads, v_dim) to match expected output
    return out.view(bs, NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv_bf16 = kv_data["bf16"]

    # bmm is faster for larger bs (better GEMM utilization on MI355X)
    # einsum is simpler and slightly faster for bs=4
    if bs <= 4:
        return _einsum_attention(q, kv_bf16, bs, kvseqlen)
    return _bmm_attention(q, kv_bf16, bs, kvseqlen)
