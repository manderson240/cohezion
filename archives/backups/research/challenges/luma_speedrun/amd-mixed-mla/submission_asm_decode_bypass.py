#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA: ASM decode kernel bypass attempt.

Strategy: Direct mla_decode_stage1_asm_fwd call with BF16-only tensors to bypass
router and trigger the decode-specific BF16 kernel (mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co).

Key hypothesis: The router selects prefill-style kernel because of:
1. FP8 quantization (forces a8w8/a16w8 path)
2. Metadata configuration
3. Indirect tensor passing

This submission uses:
- BF16 Q and KV directly (no FP8 quantization)
- Direct ASM API call (bypasses mla_decode_fwd wrapper)
- Specific metadata flags that may trigger decode kernel selection
- qseqlen=1 to signal decode mode
"""

import aiter
import torch
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1

# Thresholds
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
BF16_ASM_THRESHOLD = 4096  # Use BF16 ASM for medium shapes

_cache: dict = {}


def _choose_num_kv_splits(total_kv: int) -> int:
    """Adaptive splits based on total KV length."""
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 65536:
        return 8
    if total_kv <= 262144:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _get_cached_metadata_decode(
    bs: int,
    qseqlen: int,
    kvseqlen: int,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    num_kv_splits: int,
):
    """Metadata configured to trigger decode-specific BF16 kernel.

    Key configuration:
    - fast_mode=False (better CU distribution for decode)
    - BF16 dtypes for both Q and KV
    - is_sparse=False (dense attention)
    - intra_batch_mode=True (persistent kernel mode)
    """
    key = ("decode_bf16", bs, qseqlen, kvseqlen, num_kv_splits)
    if key in _cache:
        return _cache[key]

    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    # BF16 for both Q and KV - no FP8 quantization
    bf16_dtype = torch.bfloat16

    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        NUM_HEADS,
        bf16_dtype,
        bf16_dtype,
        is_sparse=False,
        fast_mode=False,  # Better for decode on MI355X
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
        NUM_HEADS // NUM_KV_HEADS,  # 16 (matches subQ16)
        NUM_KV_HEADS,  # 1 (but we want mqa16 behavior)
        True,  # is_causal
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
        fast_mode=False,  # Consistent with info_v1
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=bf16_dtype,
        dtype_kv=bf16_dtype,
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
        "logits": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.float32,
            device="cuda",
        ),
        "attn_lse": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS),
            dtype=torch.float32,
            device="cuda",
        ),
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }
    _cache[key] = meta
    return meta


def _einsum_attention(data):
    """Pure PyTorch einsum for small shapes."""
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


def _decode_asm_bypass(data):
    """Direct ASM decode with BF16 tensors to trigger decode kernel.

    Key differences from standard path:
    1. BF16 tensors passed directly (no FP8 quant/dequant)
    2. Direct mla_decode_stage1_asm_fwd call (bypasses Python wrapper)
    3. No scale tensors passed (BF16 doesn't need scales)
    4. Metadata configured for decode mode

    Target kernel: mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # BF16 Q and KV directly - no quantization
    q_bf16 = q.view(-1, NUM_HEADS, QK_HEAD_DIM)  # [total_q, 16, 576]
    kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]

    # Reshape KV to 4D for ASM API: [total_kv, page_size=1, nhead_kv=1, dim=576]
    kv_4d = kv_bf16.view(kv_bf16.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    num_kv_splits = _choose_num_kv_splits(total_kv)

    meta = _get_cached_metadata_decode(bs, qseqlen, kvseqlen, qo_indptr, kv_indptr, num_kv_splits)

    output = meta["output"]
    logits = meta["logits"]
    attn_lse = meta["attn_lse"]

    # Direct ASM call - bypasses mla_decode_fwd wrapper
    # Key parameters:
    # - num_kv_splits_indptr=None (not using split pointer mode)
    # - work_meta_data, work_indptr, work_info_set (metadata tensors)
    # - max_seqlen_q=qseqlen (1 for decode)
    # - nhead_kv=1 (but kernel may interpret differently)
    # - q_scale=None, kv_scale=None (BF16 doesn't need scales)
    aiter.mla_decode_stage1_asm_fwd(
        q_bf16,  # BF16 Q tensor [total_q, 16, 576]
        kv_4d,  # BF16 KV tensor [total_kv, 1, 1, 576]
        qo_indptr,  # [bs+1] indptr for Q/O
        kv_indptr,  # [bs+1] indptr for KV
        meta["kv_indices"],  # [total_kv] indices
        meta["kv_last_page_len"],  # [bs] last page lens
        None,  # num_kv_splits_indptr (not used)
        meta["work_meta_data"],
        meta["work_indptr"],
        meta["work_info_set"],
        qseqlen,  # max_seqlen_q = 1 for decode
        PAGE_SIZE,  # page_size = 1
        NUM_KV_HEADS,  # nhead_kv = 1
        SM_SCALE,  # softmax_scale
        logits,  # splitData output [splits, total_q, 16, 512]
        attn_lse,  # splitLse output [splits, total_q, 16]
        output,  # final output [total_q, 16, 512]
        None,  # q_scale (BF16 doesn't need)
        None,  # kv_scale (BF16 doesn't need)
    )

    # Reduce across splits
    mla_reduce_v1(
        logits,
        attn_lse,
        meta["reduce_indptr"],
        meta["reduce_final_map"],
        meta["reduce_partial_map"],
        qseqlen,
        output,
        None,  # final_lse not needed
    )

    return output


def custom_kernel(data: input_t) -> output_t:
    """Three-regime routing with BF16 decode ASM bypass for medium shapes.

    Regimes:
    1. Small (total_kv <= 32768 OR bs <= 4): einsum (no quantization overhead)
    2. Medium (32768 < total_kv <= 262144): BF16 ASM decode bypass
    3. Large (total_kv > 262144): BF16 ASM with more splits
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Regime 1: Small shapes -> einsum
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Regime 2 & 3: BF16 ASM decode bypass
    # No FP8 quantization, direct ASM call
    return _decode_asm_bypass(data)
