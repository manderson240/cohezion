"""
MLA decode: combined optimal — einsum + adaptive splits + direct ASM.

Three regimes:
1. Tiny (≤8k tokens): bf16 einsum — avoids all metadata/kernel overhead
2. Small-medium (8k-256k): a16w8 + adaptive splits (1-16) + direct ASM
3. Large (>256k): a8w8 fp8 + 32 splits + direct ASM

Key optimizations:
- Direct stage1_asm + reduce_v1 calls bypass mla_decode_fwd wrapper (~3-8 µs saved)
- Pre-allocated split buffers eliminate per-call torch.empty (~1-3 µs saved)
- num_kv_splits=1 for small shapes skips reduce kernel entirely (~20-30 µs saved)
- a16w8 for small shapes skips Q quantization (~5 µs saved)
"""
import torch
from task import input_t, output_t
from aiter.mla import mla_decode_fwd
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
BF16_DTYPE = torch.bfloat16

EINSUM_THRESHOLD = 8192
A16W8_THRESHOLD = 262144

_cache: dict = {}
_split_cache: dict = {}

# Direct ASM functions (lazy loaded)
_stage1_fn = None
_reduce_fn = None
_asm_checked = False


def _ensure_asm_loaded():
    global _stage1_fn, _reduce_fn, _asm_checked
    if _asm_checked:
        return
    _asm_checked = True
    try:
        import aiter
        if hasattr(aiter, 'mla_decode_stage1_asm_fwd'):
            _stage1_fn = aiter.mla_decode_stage1_asm_fwd
        if hasattr(aiter, 'mla_reduce_v1'):
            _reduce_fn = aiter.mla_reduce_v1
        if _stage1_fn is None or _reduce_fn is None:
            try:
                from aiter.jit_build import module_mla_asm, module_mla_reduce
                _stage1_fn = module_mla_asm.mla_decode_stage1_asm_fwd
                _reduce_fn = module_mla_reduce.mla_reduce_v1
            except (ImportError, AttributeError):
                pass
    except Exception:
        pass


def _choose_num_kv_splits(total_kv):
    if total_kv <= 8192:
        return 1
    if total_kv <= 65536:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _quantize_fp8(tensor):
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (
        (tensor / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE),
        scale.float().reshape(1),
    )


def _build_cache(bs, qseqlen, kvseqlen, nheads, q_dtype, kv_dtype,
                 num_kv_splits, qo_indptr, kv_indptr):
    total_kv = bs * kvseqlen
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nheads, q_dtype, kv_dtype,
        is_sparse=False, fast_mode=True,
        num_kv_splits=num_kv_splits, intra_batch_mode=True,
    )
    wm, wi, wis, ri, rfm, rpm = [
        torch.empty(s, dtype=t, device="cuda") for s, t in info
    ]
    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        nheads // NUM_KV_HEADS, NUM_KV_HEADS, True,
        wm, wis, wi, ri, rfm, rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=True,
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype, dtype_kv=kv_dtype,
    )
    return {
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "work_meta_data": wm, "work_indptr": wi, "work_info_set": wis,
        "reduce_indptr": ri, "reduce_final_map": rfm, "reduce_partial_map": rpm,
    }


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen

    # Regime 1: Tiny shapes — matmul with 4D broadcast (no kernel overhead)
    if total_kv <= EINSUM_THRESHOLD:
        kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
        q_4d = q.view(bs, qseqlen, nheads, QK_HEAD_DIM).transpose(1, 2)
        k_t = kv.unsqueeze(1).transpose(2, 3)
        scores = torch.matmul(q_4d, k_t).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1)
        v = kv[:, :, :V_HEAD_DIM].unsqueeze(1)
        out = torch.matmul(weights, v)
        return out.transpose(1, 2).reshape(-1, nheads, V_HEAD_DIM)

    # Regime 2/3: mla_decode_fwd path
    use_a16w8 = total_kv <= A16W8_THRESHOLD
    num_kv_splits = _choose_num_kv_splits(total_kv)

    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    if use_a16w8:
        q_input = q
        q_scale = None
        q_dtype = BF16_DTYPE
    else:
        q_input, q_scale = _quantize_fp8(q)
        q_dtype = FP8_DTYPE

    key = (bs, qseqlen, kvseqlen, nheads, use_a16w8, num_kv_splits)
    if key not in _cache:
        _cache[key] = _build_cache(
            bs, qseqlen, kvseqlen, nheads,
            q_dtype, FP8_DTYPE, num_kv_splits,
            qo_indptr, kv_indptr,
        )
    c = _cache[key]

    o = torch.empty(
        (q.shape[0], nheads, V_HEAD_DIM),
        dtype=torch.bfloat16, device="cuda",
    )

    # Try direct ASM path (bypasses mla_decode_fwd wrapper)
    _ensure_asm_loaded()
    if _stage1_fn is not None and _reduce_fn is not None and num_kv_splits > 1:
        split_key = (bs, nheads, num_kv_splits)
        if split_key not in _split_cache:
            total_q = bs * qseqlen
            _split_cache[split_key] = {
                "split_data": torch.empty(
                    (total_q, num_kv_splits, nheads, V_HEAD_DIM + 8),
                    dtype=torch.float32, device="cuda",
                ),
                "split_lse": torch.empty(
                    (total_q, num_kv_splits, nheads),
                    dtype=torch.float32, device="cuda",
                ),
            }
        sc = _split_cache[split_key]
        try:
            _stage1_fn(
                q_input.view(-1, nheads, QK_HEAD_DIM), kv_4d,
                qo_indptr, kv_indptr,
                c["kv_indices"], c["kv_last_page_len"],
                None,
                c["work_meta_data"], c["work_indptr"], c["work_info_set"],
                qseqlen, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE,
                sc["split_data"], sc["split_lse"], o,
                q_scale=q_scale, kv_scale=kv_scale,
            )
            _reduce_fn(
                sc["split_data"], sc["split_lse"],
                c["reduce_indptr"], c["reduce_final_map"], c["reduce_partial_map"],
                qseqlen, o,
            )
            return o
        except Exception:
            pass  # Fall through to mla_decode_fwd

    # Fallback: mla_decode_fwd (also handles num_kv_splits=1)
    mla_decode_fwd(
        q_input.view(-1, nheads, QK_HEAD_DIM), kv_4d, o,
        qo_indptr, kv_indptr,
        c["kv_indices"], c["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE, nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE, logit_cap=0.0,
        num_kv_splits=num_kv_splits,
        q_scale=q_scale, kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=c["work_meta_data"],
        work_indptr=c["work_indptr"],
        work_info_set=c["work_info_set"],
        reduce_indptr=c["reduce_indptr"],
        reduce_final_map=c["reduce_final_map"],
        reduce_partial_map=c["reduce_partial_map"],
    )
    return o
