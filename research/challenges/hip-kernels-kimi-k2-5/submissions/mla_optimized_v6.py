"""MLA v6: Research-based optimizations."""

import torch
from aiter import get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1


def custom_kernel(data: input_t) -> output_t:
    """Optimized based on AITER MLA research.

    Key findings from /tmp/aiter/csrc/kernels/mla/:
    - Two-stage: stage1 (ASM) + stage2 (reduction)
    - Metadata generation is critical for performance
    - fast_mode=True uses v1_2_device (faster)
    - intra_batch_mode=True uses v1_0_device (more flexible)

    From /tmp/aiter/hsa/gfx950/mla/:
    - Kernels: MLA_A16W16, MLA_A8W8 variants
    - Tile sizes: 32x4, 64x4 for different head counts
    - QH16, QH128 variants for different query heads

    Key insight: num_kv_splits should be calculated based on:
    - batch_size
    - total_kv_tokens
    - num_heads
    - GPU compute units (304 on MI355X)
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen

    # Use FP8 for maximum speed (2x bandwidth)
    kv_fp8 = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    # Calculate optimal num_kv_splits based on AITER formula
    # From mla.py: num_kv_splits balances parallelism vs overhead
    # Formula: minimize (bs * i) / ((bs * i + cu_num - 1) // cu_num * cu_num) * avg_kv / (avg_kv + overhead * i)

    avg_kv = total_kv / bs
    overhead = 84.1  # From AITER code

    # Test different num_kv_splits (1-16) and pick optimal
    # For now, use adaptive based on total_kv
    if total_kv <= 4096:
        num_splits = 4
    elif total_kv <= 16384:
        num_splits = 8
    elif total_kv <= 65536:
        num_splits = 16
    elif total_kv <= 262144:
        num_splits = 32
    else:
        num_splits = 64

    o = torch.empty((q.shape[0], nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    meta = get_mla_metadata_v1(
        bs,
        qseqlen,
        nheads,
        q.dtype,
        kv_fp8.dtype,
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        num_kv_splits=num_splits,
    )

    mla_decode_fwd(
        q.view(-1, nheads, QK_HEAD_DIM),
        kv_4d,
        o,
        qo_indptr,
        kv_indptr,
        kv_indices,
        kv_last_page_len,
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_splits,
        intra_batch_mode=True,
        **meta,
    )
    return o
