#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""BF16 decode v3: non-persistent mode routes to mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co

Root cause of dispatch bug (from probe data):
  - Persistent mode sets ps=1 in asm_mla.cu: `bool persistent = (num_kv_splits_indptr == nullptr)`
  - ps=1 + gqa_ratio=16 + bf16/bf16 dispatches the PREFILL kernel (m16x4 config), not decode
  - Non-persistent (ps=0) + max_seqlen_q=1 + gqa_ratio=16 + bf16/bf16 -> DECODE kernel

Fix: call mla_decode_fwd WITHOUT work_meta_data (non-persistent), pass num_kv_splits_indptr
explicitly. This forces ps=0 in the C++ kernel selection table, which dispatches:
  mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co

Advantages vs submission_a16w16.py (which got 100µs via wrong kernel):
  - No FP8 quantization overhead (skips _quantize_fp8 entirely)
  - Uses BF16 decode kernel (not prefill)
  - Direct kv_data["bf16"] — no dtype conversion

vs submission_best_67us.py (which uses fp8 KV + persistent mode):
  - BF16 has 2x the memory bandwidth pressure vs fp8
  - But eliminates Q quantization and kv_scale overhead for medium shapes
  - May be faster for shapes where memory bandwidth is not the bottleneck

Threshold logic (proven from submission_best_67us.py):
  - bs<=4 OR total_kv<=32768: einsum is faster (avoids all dispatch overhead)
  - Otherwise: non-persistent BF16 decode ASM kernel
"""

import torch
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1

# Einsum is proven faster than any aiter kernel for small batch/kv sizes.
# Uses OR: captures low-bs shapes (bs=4) AND low-total_kv shapes independently.
EINSUM_MAX_BS = 4
EINSUM_MAX_TOTAL_KV = 32768

_cache: dict = {}


def _choose_num_kv_splits(total_kv: int) -> int:
    """Adaptive split schedule for non-persistent BF16 decode.

    Tuned to match the schedule from submission_best_67us.py which achieved
    the best aiter-level result at ~67.8µs geomean.
    """
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _einsum_attention(data: input_t) -> output_t:
    """Batched einsum attention for small shapes — fastest path, no dispatch overhead."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, nheads, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, nheads, V_HEAD_DIM)
        .to(torch.bfloat16)
    )


def _build_decode_cache(
    bs: int,
    qseqlen: int,
    kvseqlen: int,
    kv_indptr: torch.Tensor,
    num_kv_splits: int,
) -> dict:
    """Pre-allocate all tensors needed for non-persistent BF16 decode.

    Non-persistent path: work_meta_data/work_indptr/work_info_set are all None.
    num_kv_splits_indptr is passed explicitly, making persistent=False in C++.
    This forces ps=0 -> decode kernel selection in asm_mla.cu.
    """
    key = ("dec_bf16_v3", bs, qseqlen, kvseqlen, num_kv_splits)
    if key in _cache:
        return _cache[key]

    total_q = bs * qseqlen
    total_kv_len = int(kv_indptr[-1].item())

    # Uniform split assignment: [0, N, 2N, ..., bs*N]
    num_kv_splits_indptr = torch.arange(
        0,
        (bs + 1) * num_kv_splits,
        num_kv_splits,
        dtype=torch.int32,
        device="cuda",
    )

    meta = {
        "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last_page_len": (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32),
        "num_kv_splits_indptr": num_kv_splits_indptr,
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }
    _cache[key] = meta
    return meta


def _dec_bf16_attention(data: input_t) -> output_t:
    """Non-persistent BF16 decode: routes to mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co.

    Critical: work_meta_data is NOT passed (defaults to None), keeping persistent=False
    in asm_mla.cu. With ps=0 + max_seqlen_q=1 + gqa_ratio=16 + bf16/bf16, the kernel
    selection table picks the decode kernel (not the prefill/m16x4 kernel).
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen

    kv_bf16 = kv_data["bf16"]
    num_kv_splits = _choose_num_kv_splits(total_kv)

    # 4D view: (total_kv, page_size=1, nhead_kv=1, dim=576)
    kv_4d = kv_bf16.view(kv_bf16.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _build_decode_cache(bs, qseqlen, kvseqlen, kv_indptr, num_kv_splits)
    output = meta["output"]

    # Non-persistent mla_decode_fwd: omit work_meta_data/work_indptr/work_info_set.
    # Pass num_kv_splits and num_kv_splits_indptr to skip get_meta_param and go
    # directly to mla_decode_stage1_asm_fwd with ps=0.
    # q_scale=None and kv_scale=None: pure BF16, no FP8 quantization.
    mla_decode_fwd(
        q.view(-1, nheads, QK_HEAD_DIM),
        kv_4d,
        output,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_kv_splits,
        num_kv_splits_indptr=meta["num_kv_splits_indptr"],
        # work_meta_data defaults to None — non-persistent mode, ps=0 -> decode kernel
        q_scale=None,
        kv_scale=None,
        intra_batch_mode=False,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Einsum is proven fastest for small batch sizes and small KV sequences.
    if bs <= EINSUM_MAX_BS or total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    return _dec_bf16_attention(data)
