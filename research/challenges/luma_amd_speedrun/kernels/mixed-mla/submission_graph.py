"""
MLA decode: CUDA/HIP graph capture of mla_decode_fwd.

Strategy: capture the full mla_decode_fwd pipeline into a HIP graph per shape,
then replay with near-zero dispatch overhead. For decode (qseqlen=1), shapes
are deterministic based on (bs, kvseqlen, nheads).

Graph capture eliminates:
  - Python function call overhead (~2-5 µs)
  - HIP kernel launch overhead per internal kernel (~1-2 µs each)
  - Memory allocation overhead (pre-allocated in graph)

Uses a16w8 (bf16 Q + fp8 KV) to also eliminate Q quantization.
Metadata cached per shape. Output buffer reused across calls.
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

_meta_cache: dict = {}
_graph_cache: dict = {}


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


def _run_decode(q, kv_4d, o, qo_indptr, kv_indptr, meta, nheads, qseqlen, kv_scale):
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

    key = (bs, qseqlen, kvseqlen, nheads)

    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    # Build/cache metadata
    if key not in _meta_cache:
        _meta_cache[key] = _build_metadata(
            bs, qseqlen, kvseqlen, nheads, qo_indptr, kv_indptr,
        )
    meta = _meta_cache[key]

    # Output buffer (reuse)
    o = torch.empty(
        (q.shape[0], nheads, V_HEAD_DIM),
        dtype=torch.bfloat16, device="cuda",
    )

    # Try graph capture/replay
    if key in _graph_cache:
        # Copy input data into graph's static buffers, then replay
        g_info = _graph_cache[key]
        g_info["q_buf"].copy_(q)
        g_info["kv_buf"].copy_(kv_4d)
        g_info["kv_scale_buf"].copy_(kv_scale)
        g_info["graph"].replay()
        o.copy_(g_info["o_buf"])
        return o

    # First call: try to capture graph
    try:
        # Allocate static buffers for graph capture
        q_static = q.clone()
        kv_static = kv_4d.clone()
        kv_scale_static = kv_scale.clone()
        o_static = torch.empty_like(o)

        # Warmup (required before capture)
        for _ in range(3):
            _run_decode(q_static, kv_static, o_static,
                       qo_indptr, kv_indptr, meta, nheads, qseqlen,
                       kv_scale_static)

        # Capture
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            _run_decode(q_static, kv_static, o_static,
                       qo_indptr, kv_indptr, meta, nheads, qseqlen,
                       kv_scale_static)

        _graph_cache[key] = {
            "graph": graph,
            "q_buf": q_static,
            "kv_buf": kv_static,
            "kv_scale_buf": kv_scale_static,
            "o_buf": o_static,
        }

        # First replay with actual data
        q_static.copy_(q)
        kv_static.copy_(kv_4d)
        kv_scale_static.copy_(kv_scale)
        graph.replay()
        o.copy_(o_static)
        return o

    except Exception:
        # Graph capture failed — fall back to direct call
        _run_decode(q, kv_4d, o, qo_indptr, kv_indptr, meta,
                   nheads, qseqlen, kv_scale)
        return o
