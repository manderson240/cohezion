"""
MLA decode: hybrid bf16-einsum + graph-captured mla_decode_fwd.

Two regimes:
  - Small (total_kv <= 32768): bf16 torch.matmul attention
    No quantization, no metadata, no kernel launch overhead.
    Pure PyTorch matmul + softmax + matmul — GPU-native, zero Python overhead.
  - Large (total_kv > 32768): mla_decode_fwd (a16w8) with CUDA graph capture
    Graph replay eliminates kernel launch overhead.

The bf16 matmul path uses Q@K^T (full 576 dims), softmax, attn@V[:512].
For small shapes, the matmul path avoids:
  - fp8 quantization (~5 µs)
  - metadata computation (~10 µs)
  - kernel dispatch overhead (~5 µs)
Total savings: ~20 µs for small shapes.
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

NUM_KV_SPLITS = 32
MATMUL_THRESHOLD = 32768  # total_kv threshold for matmul vs aiter

_meta_cache: dict = {}
_graph_cache: dict = {}


def _bf16_matmul_attention(q, kv_bf16, bs, kvseqlen, nheads):
    """Pure bf16 matmul attention — zero quantization overhead."""
    # q: (bs, nheads, 576), kv: (total_kv, 1, 576) -> (bs, kvseqlen, 576)
    kv = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)

    # Q: (bs, nheads, 576) -> (bs, nheads, 1, 576) for bmm
    q_4d = q.view(bs, nheads, 1, QK_HEAD_DIM)

    # K^T: (bs, 576, kvseqlen)
    k_t = kv.transpose(1, 2)  # (bs, 576, kvseqlen)

    # Score: (bs, nheads, 1, kvseqlen) via broadcast matmul
    # q_4d @ k_t.unsqueeze(1) -> broadcast over nheads
    scores = torch.matmul(q_4d, k_t.unsqueeze(1)) * SM_SCALE

    # Softmax
    attn = torch.softmax(scores, dim=-1)

    # V: (bs, kvseqlen, 512) -> (bs, 1, kvseqlen, 512)
    v = kv[:, :, :V_HEAD_DIM].unsqueeze(1)

    # Output: (bs, nheads, 1, 512) -> (bs, nheads, 512)
    out = torch.matmul(attn, v).squeeze(2)
    return out


def _build_metadata(bs, qseqlen, kvseqlen, nheads, qo_indptr, kv_indptr):
    total_kv = bs * kvseqlen
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nheads, BF16_DTYPE, FP8_DTYPE,
        is_sparse=False, fast_mode=True,
        num_kv_splits=NUM_KV_SPLITS, intra_batch_mode=True,
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
        max_split_per_batch=NUM_KV_SPLITS,
        intra_batch_mode=True,
        dtype_q=BF16_DTYPE, dtype_kv=FP8_DTYPE,
    )

    return {
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "work_meta_data": wm,
        "work_indptr": wi,
        "work_info_set": wis,
        "reduce_indptr": ri,
        "reduce_final_map": rfm,
        "reduce_partial_map": rpm,
    }


def _run_aiter(q, kv_4d, o, qo_indptr, kv_indptr, meta, nheads, qseqlen, kv_scale):
    mla_decode_fwd(
        q.view(-1, nheads, QK_HEAD_DIM), kv_4d, o,
        qo_indptr, kv_indptr,
        meta["kv_indices"], meta["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE, nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE, logit_cap=0.0,
        num_kv_splits=NUM_KV_SPLITS,
        q_scale=None, kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=meta["work_meta_data"],
        work_indptr=meta["work_indptr"],
        work_info_set=meta["work_info_set"],
        reduce_indptr=meta["reduce_indptr"],
        reduce_final_map=meta["reduce_final_map"],
        reduce_partial_map=meta["reduce_partial_map"],
    )


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    total_kv = bs * kvseqlen

    # Small shapes: pure bf16 matmul (no quantization, no metadata overhead)
    if total_kv <= MATMUL_THRESHOLD:
        kv_bf16 = kv_data["bf16"]
        out = _bf16_matmul_attention(q, kv_bf16, bs, kvseqlen, nheads)
        return out.reshape(-1, nheads, V_HEAD_DIM)

    # Large shapes: mla_decode_fwd with a16w8 + metadata caching
    key = (bs, qseqlen, kvseqlen, nheads)

    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    if key not in _meta_cache:
        _meta_cache[key] = _build_metadata(
            bs, qseqlen, kvseqlen, nheads, qo_indptr, kv_indptr,
        )
    meta = _meta_cache[key]

    o = torch.empty(
        (q.shape[0], nheads, V_HEAD_DIM),
        dtype=torch.bfloat16, device="cuda",
    )

    # Try graph replay
    if key in _graph_cache:
        g = _graph_cache[key]
        g["q_buf"].copy_(q)
        g["kv_buf"].copy_(kv_4d)
        g["kv_scale_buf"].copy_(kv_scale)
        g["graph"].replay()
        o.copy_(g["o_buf"])
        return o

    # First call: try graph capture
    try:
        q_s = q.clone()
        kv_s = kv_4d.clone()
        ks_s = kv_scale.clone()
        o_s = torch.empty_like(o)

        for _ in range(3):
            _run_aiter(q_s, kv_s, o_s, qo_indptr, kv_indptr,
                      meta, nheads, qseqlen, ks_s)

        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            _run_aiter(q_s, kv_s, o_s, qo_indptr, kv_indptr,
                      meta, nheads, qseqlen, ks_s)

        _graph_cache[key] = {
            "graph": graph, "q_buf": q_s, "kv_buf": kv_s,
            "kv_scale_buf": ks_s, "o_buf": o_s,
        }

        q_s.copy_(q)
        kv_s.copy_(kv_4d)
        ks_s.copy_(kv_scale)
        graph.replay()
        o.copy_(o_s)
        return o

    except Exception:
        _run_aiter(q, kv_4d, o, qo_indptr, kv_indptr,
                  meta, nheads, qseqlen, kv_scale)
        return o
