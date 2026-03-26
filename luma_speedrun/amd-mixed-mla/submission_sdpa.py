"""MLA decode submission — SDPA fusion for small shapes.

Replaces the 4-op matmul path (Q@K^T, scale, softmax, @V) with a single
F.scaled_dot_product_attention call for the small-shape regime.

Challenge: MLA has K_dim=576, V_dim=512 (K≠V). Standard SDPA requires
K_dim == V_dim in the efficient path. Two approaches:
  A) Pad V to 576 and slice output (extra memory but single fused dispatch)
  B) Use the general path with attn_mask=None (PyTorch may auto-select)

We try approach A first — the padding cost should be negligible for small shapes.

For large shapes, the aiter ASM path is unchanged.

Expected gain: ~20-40µs on small shapes (4 dispatches → 1 dispatch).
"""

import torch
import torch.nn.functional as F
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)
from task import input_t, output_t


# ── DeepSeek R1 MLA constants ──
NUM_HEADS = 16
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# ── Routing thresholds ──
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

# ── Metadata + intermediate cache ──
_cache: dict = {}


def _choose_num_kv_splits(total_kv: int) -> int:
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _get_cached_metadata(
    bs, qseqlen, kvseqlen, q_dtype, kv_dtype,
    qo_indptr, kv_indptr, num_kv_splits,
):
    key = (bs, qseqlen, kvseqlen, q_dtype, kv_dtype, num_kv_splits)
    if key in _cache:
        return _cache[key]

    nq, nkv = NUM_HEADS, NUM_KV_HEADS
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nq, q_dtype, kv_dtype,
        is_sparse=False, fast_mode=False,
        num_kv_splits=num_kv_splits, intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    work_metadata, work_indptr, work_info_set, reduce_indptr, reduce_final_map, reduce_partial_map = work

    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        nq // nkv, nkv, True,
        work_metadata, work_info_set, work_indptr,
        reduce_indptr, reduce_final_map, reduce_partial_map,
        page_size=PAGE_SIZE, kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=False, max_split_per_batch=num_kv_splits,
        intra_batch_mode=True, dtype_q=q_dtype, dtype_kv=kv_dtype,
    )

    total_kv_len = int(kv_indptr[-1].item())
    kv_indices = torch.arange(total_kv_len, dtype=torch.int32, device="cuda")

    total_q = bs * qseqlen
    logits = torch.empty((num_kv_splits, total_q, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda")
    attn_lse = torch.empty((num_kv_splits, total_q, nq), dtype=torch.float32, device="cuda")
    output = torch.empty((total_q, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    meta = {
        "work_meta_data": work_metadata,
        "work_indptr": work_indptr,
        "work_info_set": work_info_set,
        "reduce_indptr": reduce_indptr,
        "reduce_final_map": reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "logits": logits,
        "attn_lse": attn_lse,
        "output": output,
    }
    _cache[key] = meta
    return meta


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # ── Regime 1: SDPA fusion for small shapes ──
    # Replaces 4 separate torch ops with single fused SDPA kernel
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]

        # SDPA expects [batch, heads, seq_len, head_dim]
        # Q: [bs, 16, 576] → [bs, 16, 1, 576]
        q_4d = q.view(bs, NUM_HEADS, QK_HEAD_DIM).unsqueeze(2)

        # KV: [total_kv, 1, 576] → [bs, kvseqlen, 576]
        kv_per_batch = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)

        # K: [bs, 1, kvseqlen, 576] → broadcast to [bs, 16, kvseqlen, 576]
        k_4d = kv_per_batch.unsqueeze(1).expand(-1, NUM_HEADS, -1, -1)

        # V: same shape but only first 512 dims
        # SDPA requires K_dim == head_dim for Q and K, but V can differ
        # Actually SDPA requires K.shape[-1] == Q.shape[-1] (for Q@K^T)
        # and V.shape[-2] == K.shape[-2] (seq_len match)
        # V.shape[-1] determines output head_dim
        v_4d = kv_per_batch[:, :, :V_HEAD_DIM].unsqueeze(1).expand(-1, NUM_HEADS, -1, -1)

        # Single fused SDPA: Q@K^T * scale + softmax + @V
        # is_causal=False since this is decode (no causal mask needed)
        out = F.scaled_dot_product_attention(
            q_4d, k_4d, v_4d,
            attn_mask=None,
            dropout_p=0.0,
            is_causal=False,
            scale=SM_SCALE,
        )
        # out: [bs, 16, 1, 512] → [bs*1, 16, 512]
        return out.squeeze(2).reshape(bs * qseqlen, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2+3: aiter direct ASM dispatch (unchanged) ──
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _get_cached_metadata(
        bs, qseqlen, kvseqlen,
        q_fp8.dtype, kv_buffer_fp8.dtype,
        qo_indptr, kv_indptr, num_kv_splits,
    )

    output = meta["output"]
    logits = meta["logits"]
    attn_lse = meta["attn_lse"]

    mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d, qo_indptr, kv_indptr,
        meta["kv_indices"], meta["kv_last_page_len"],
        None,
        meta["work_meta_data"], meta["work_indptr"], meta["work_info_set"],
        qseqlen, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE,
        logits, attn_lse, output,
        q_scale, kv_scale,
    )

    mla_reduce_v1(
        logits, attn_lse,
        meta["reduce_indptr"], meta["reduce_final_map"], meta["reduce_partial_map"],
        qseqlen, output, None,
    )

    return output
