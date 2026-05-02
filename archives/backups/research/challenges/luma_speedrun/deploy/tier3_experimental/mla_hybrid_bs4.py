#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Hybrid: einsum for bs<=4 (all KV), FP8 ASM for bs>4.

Key finding from benchmarking:
  - einsum at bs=4/kv=8192 = 35.8µs
  - BF16 ASM at bs=4/kv=8192 = 138µs (3.9x SLOWER than einsum)
  - FP8 ASM at bs=4/kv=8192 is likely 80-120µs (faster than BF16 but not einsum)

A8 uses einsum only for total_kv<=4096, which means bs=4/kv=8192 (total=32768)
goes through FP8 ASM and is a major drag on the geomean.

This submission extends the einsum path to cover ALL bs<=4 shapes:
  - bs=4/kv=1024  (total=4K)   -> einsum: ~23µs
  - bs=4/kv=8192  (total=32K)  -> einsum: ~36µs  [BIG WIN vs ASM ~100+µs]

All other shapes (bs=32,64,256) use FP8 ASM with shape-tuned splits (same as A8).

Expected geomean improvement: the bs=4/kv=8192 shape goes from ~100+µs to 36µs,
which significantly improves the geometric mean.
"""

import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# Use einsum for all shapes with bs<=4 (small batch, any KV length)
EINSUM_MAX_BS = 4

_cache: dict = {}


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_kv_splits(total_kv: int) -> int:
    """Shape-tuned splits for ranked shapes (same as A8)."""
    if total_kv <= 32768:
        return 4
    if total_kv <= 65536:
        return 4
    if total_kv <= 262144:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _get_cached_metadata(
    bs, qseqlen, kvseqlen, q_dtype, kv_dtype, qo_indptr, kv_indptr, num_kv_splits
):
    key = (bs, qseqlen, kvseqlen, q_dtype, kv_dtype, num_kv_splits)
    if key in _cache:
        return _cache[key]

    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        NUM_HEADS,
        q_dtype,
        kv_dtype,
        is_sparse=False,
        fast_mode=True,
        num_kv_splits=num_kv_splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    (
        work_metadata,
        work_indptr,
        work_info_set,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
    ) = work

    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        NUM_HEADS // NUM_KV_HEADS,
        NUM_KV_HEADS,
        True,
        work_metadata,
        work_info_set,
        work_indptr,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen,
        uni_seqlen_qo=qseqlen,
        fast_mode=True,
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype,
        dtype_kv=kv_dtype,
    )

    total_kv_len = int(kv_indptr[-1].item())
    total_q = bs * qseqlen
    meta = {
        "work_meta_data": work_metadata,
        "work_indptr": work_indptr,
        "work_info_set": work_info_set,
        "reduce_indptr": reduce_indptr,
        "reduce_final_map": reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last_page_len": kv_last_page_len,
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }
    _cache[key] = meta
    return meta


def _einsum_attention(data):
    """BF16 einsum attention — fast for small bs due to no kernel launch overhead."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, NUM_HEADS, V_HEAD_DIM)
        .to(torch.bfloat16)
    )


def _asm_attention(data):
    """FP8 ASM attention for large-bs shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)
    meta = _get_cached_metadata(
        bs,
        qseqlen,
        kvseqlen,
        q_fp8.dtype,
        kv_buffer_fp8.dtype,
        qo_indptr,
        kv_indptr,
        num_kv_splits,
    )
    output = meta["output"]
    mla_decode_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
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
        q_scale=q_scale,
        kv_scale=kv_scale,
        intra_batch_mode=True,
        **{
            k: meta[k]
            for k in [
                "work_meta_data",
                "work_indptr",
                "work_info_set",
                "reduce_indptr",
                "reduce_final_map",
                "reduce_partial_map",
            ]
        },
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]

    # Use einsum for all small-batch shapes — benchmarks show it's 3-4x faster
    # than ASM for bs=4 regardless of KV length
    if bs <= EINSUM_MAX_BS:
        return _einsum_attention(data)

    return _asm_attention(data)
