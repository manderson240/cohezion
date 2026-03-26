"""MLA decode — direct CK-Tile dispatch via ctypes (bypass Python wrapper overhead).

Stage1: hipModuleLaunchKernel with mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co
Stage2: aiter.mla_reduce_v1 (not bypassable — compiled into .so, not .co)

Expected: eliminate ~20-25µs stage1 Python dispatch overhead.
Baseline: ~70µs | Target: ~45-50µs | Leader: ~33µs
"""

import ctypes

import torch
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
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

# ── Kernel file + symbol ──
# Runner path: /home/runner/aiter/hsa/gfx950/ (NOT local ~/dev/aiter/)
_CO_PATH = b"/home/runner/aiter/hsa/gfx950/mla/mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co"
_KERNEL_SYMBOL = b"_ZN5aiter36mla_a8w8_qh16_qseqlen1_gqaratio16_psE"

# ── HIP launch param tokens ──
HIP_LAUNCH_PARAM_BUFFER_POINTER = ctypes.c_void_p(0x01)
HIP_LAUNCH_PARAM_BUFFER_SIZE    = ctypes.c_void_p(0x02)
HIP_LAUNCH_PARAM_END            = ctypes.c_void_p(0x03)

# ══════════════════════════════════════════════════════════════════════════════
# ctypes struct definitions — must exactly match the C __attribute__((packed))
# layout in csrc/py_itfs_cu/asm_mla.cu / aiter_hip_common.h
# ══════════════════════════════════════════════════════════════════════════════

class _p2(ctypes.Structure):
    """8-byte padding between pointer and next field."""
    _fields_ = [("_p0", ctypes.c_uint32), ("_p1", ctypes.c_uint32)]


class _p3(ctypes.Structure):
    """12-byte padding between scalar and next field."""
    _fields_ = [("_p0", ctypes.c_uint32), ("_p1", ctypes.c_uint32), ("_p2", ctypes.c_uint32)]


class MlaKernelArgs(ctypes.Structure):
    """320-byte packed arg buffer for mla_a8w8_qh16_qseqlen1_gqaratio16_ps.

    Field offsets are fixed by the kernel ABI; p2/p3 padding must be preserved
    exactly as in the C struct definition.
    """
    _pack_ = 1  # __attribute__((packed)) — overrides all alignment, same as GCC packed struct
    _fields_ = [
        ("ptr_R",           ctypes.c_void_p),  # offset 0   — splitData (logits) [splits,q,heads,v_dim] f32
        ("_p0",             _p2),               # offset 8
        ("ptr_LSE",         ctypes.c_void_p),  # offset 16  — splitLse (attn_lse) [splits,q,heads] f32
        ("_p1",             _p2),               # offset 24
        ("ptr_Q",           ctypes.c_void_p),  # offset 32  — Q [total_q, heads, qk_head_dim] fp8
        ("_p2",             _p2),               # offset 40
        ("ptr_KV",          ctypes.c_void_p),  # offset 48  — KV [pages, ps, kv_heads, qk_head_dim] fp8
        ("_p3",             _p2),               # offset 56
        ("ptr_LTP",         ctypes.c_void_p),  # offset 64  — kv_indptr [batch+1] int32
        ("_p4",             _p2),               # offset 72
        ("ptr_LTD",         ctypes.c_void_p),  # offset 80  — kv_page_indices [total_kv_pages] int32
        ("_p5",             _p2),               # offset 88
        ("ptr_LTL",         ctypes.c_void_p),  # offset 96  — kv_last_page_lens [batch] int32
        ("_p6",             _p2),               # offset 104
        ("scalar",          ctypes.c_float),   # offset 112 — softmax_scale
        ("_p12",            _p3),               # offset 116
        ("s_MQA",           ctypes.c_uint32),  # offset 128 — gqa_ratio * max_seqlen_q
        ("_p13",            _p3),               # offset 132
        ("s_kv_split",      ctypes.c_uint32),  # offset 144 — number of KV splits
        ("_p14",            _p3),               # offset 148
        ("s_Q_Bs",          ctypes.c_uint32),  # offset 160 — Q stride bytes per seq
        ("_p15",            _p3),               # offset 164
        ("s_Bs",            ctypes.c_uint32),  # offset 176 — KV page stride bytes
        ("_p16",            _p3),               # offset 180
        ("s_log2_plen",     ctypes.c_uint32),  # offset 192 — log2(page_size)
        ("_p17",            _p3),               # offset 196
        ("ptr_QTP",         ctypes.c_void_p),  # offset 208 — qo_indptr [batch+1] int32
        ("_p18",            _p2),               # offset 216
        ("ptr_STP",         ctypes.c_void_p),  # offset 224 — persistent metadata (work_meta_data ptr)
        ("_p19",            _p2),               # offset 232
        ("ptr_RP",          ctypes.c_void_p),  # offset 240 — final output [total_q, heads, v_dim] bf16
        ("_p20",            _p2),               # offset 248
        ("ptr_QSCALE",      ctypes.c_void_p),  # offset 256 — q_scale [1] f32
        ("_p21",            _p2),               # offset 264
        ("ptr_KVSCALE",     ctypes.c_void_p),  # offset 272 — kv_scale [1] f32
        ("_p22",            _p2),               # offset 280
        ("out_16_nosplit",  ctypes.c_uint32),  # offset 288 — = kv_split (duplicate)
        ("_p23",            _p3),               # offset 292
        ("ptr_LSEP",        ctypes.c_void_p),  # offset 304 — final LSE (nullable)
        ("_p24",            _p2),               # offset 312
        #                                       # total: 320 bytes
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Module-level HIP setup — runs once at import time, not in the hot path
# ══════════════════════════════════════════════════════════════════════════════

# Verify struct layout before doing anything else
assert ctypes.sizeof(MlaKernelArgs) == 320, (
    f"MlaKernelArgs size mismatch: got {ctypes.sizeof(MlaKernelArgs)}, expected 320"
)

# Load HIP runtime
_hip = ctypes.CDLL("libamdhip64.so")

# Declare restype/argtypes to prevent ctypes from guessing (and segfaulting)
_hip.hipModuleLoad.restype = ctypes.c_int
_hip.hipModuleLoad.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p]

_hip.hipModuleGetFunction.restype = ctypes.c_int
_hip.hipModuleGetFunction.argtypes = [
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.c_void_p,
    ctypes.c_char_p,
]

_hip.hipModuleLaunchKernel.restype = ctypes.c_int
_hip.hipModuleLaunchKernel.argtypes = [
    ctypes.c_void_p,                                        # function handle
    ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,     # grid x/y/z
    ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,     # block x/y/z
    ctypes.c_uint32,                                        # shared memory bytes
    ctypes.c_void_p,                                        # stream
    ctypes.c_void_p,                                        # kernelParams (must be nullptr)
    ctypes.c_void_p,                                        # extra (config array)
]

# Load the .co module and retrieve the function handle
_mla_module = ctypes.c_void_p(0)
_mla_func   = ctypes.c_void_p(0)

_mla_err_load = _hip.hipModuleLoad(ctypes.byref(_mla_module), _CO_PATH)
assert _mla_err_load == 0, f"hipModuleLoad failed with error code {_mla_err_load}"

_mla_err_func = _hip.hipModuleGetFunction(
    ctypes.byref(_mla_func), _mla_module, _KERNEL_SYMBOL
)
assert _mla_err_func == 0, f"hipModuleGetFunction failed with error code {_mla_err_func}"

# ── Metadata + intermediate cache ──
_cache: dict = {}


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════════════════

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
    bs: int, qseqlen: int, kvseqlen: int,
    q_dtype: torch.dtype, kv_dtype: torch.dtype,
    qo_indptr: torch.Tensor, kv_indptr: torch.Tensor,
    num_kv_splits: int,
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

    # Pre-allocate intermediates
    total_q = bs * qseqlen
    logits   = torch.empty((num_kv_splits, total_q, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda")
    attn_lse = torch.empty((num_kv_splits, total_q, nq), dtype=torch.float32, device="cuda")
    output   = torch.empty((total_q, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    meta = {
        "work_meta_data":    work_metadata,
        "work_indptr":       work_indptr,
        "work_info_set":     work_info_set,
        "reduce_indptr":     reduce_indptr,
        "reduce_final_map":  reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "kv_indices":        kv_indices,
        "kv_last_page_len":  kv_last_page_len,
        "logits":            logits,
        "attn_lse":          attn_lse,
        "output":            output,
    }
    _cache[key] = meta
    return meta


def _launch_mla_stage1(
    q_fp8: torch.Tensor,
    kv_4d: torch.Tensor,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    meta: dict,
    q_scale: torch.Tensor,
    kv_scale: torch.Tensor,
    qseqlen: int,
    num_kv_splits: int,
) -> None:
    """Launch mla_a8w8_qh16_qseqlen1_gqaratio16_ps directly via hipModuleLaunchKernel.

    Replaces the Python wrapper `mla_decode_stage1_asm_fwd`, eliminating the
    per-call dispatch overhead while keeping the same kernel execution path.
    """
    logits   = meta["logits"]
    attn_lse = meta["attn_lse"]
    output   = meta["output"]

    # ── Scalar computations (matching csrc/py_itfs_cu/asm_mla.cu) ──
    # s_Q_Bs = Q.stride(0) * element_size * max_seqlen_q
    s_Q_Bs = q_fp8.stride(0) * q_fp8.element_size() * qseqlen
    # s_Bs   = KV.stride(0) * element_size
    s_Bs   = kv_4d.stride(0) * kv_4d.element_size()
    # s_log2_plen = log2(PAGE_SIZE) = log2(1) = 0
    s_log2_plen = 0
    # s_MQA  = gqa_ratio * max_seqlen_q = (NUM_HEADS / NUM_KV_HEADS) * qseqlen
    s_MQA  = (NUM_HEADS // NUM_KV_HEADS) * qseqlen

    # ── Build the packed KernelArgs struct ──
    args = MlaKernelArgs()
    args.ptr_R          = logits.data_ptr()
    args.ptr_LSE        = attn_lse.data_ptr()
    args.ptr_Q          = q_fp8.data_ptr()
    args.ptr_KV         = kv_4d.data_ptr()
    args.ptr_LTP        = kv_indptr.data_ptr()
    args.ptr_LTD        = meta["kv_indices"].data_ptr()
    args.ptr_LTL        = meta["kv_last_page_len"].data_ptr()
    args.scalar         = SM_SCALE
    args.s_MQA          = s_MQA
    args.s_kv_split     = num_kv_splits
    args.s_Q_Bs         = s_Q_Bs
    args.s_Bs           = s_Bs
    args.s_log2_plen    = s_log2_plen
    args.ptr_QTP        = qo_indptr.data_ptr()
    # work_meta_data IS the pre-packed 80-byte uint64 GPU buffer — pass ptr directly
    args.ptr_STP        = meta["work_meta_data"].data_ptr()
    args.ptr_RP         = output.data_ptr()
    args.ptr_QSCALE     = q_scale.data_ptr()
    args.ptr_KVSCALE    = kv_scale.data_ptr()
    args.out_16_nosplit = num_kv_splits
    args.ptr_LSEP       = None  # no final LSE output needed

    # ── Build config array for BUFFER_POINTER launch style ──
    arg_size = ctypes.c_size_t(ctypes.sizeof(args))
    config = (ctypes.c_void_p * 5)(
        HIP_LAUNCH_PARAM_BUFFER_POINTER,
        ctypes.cast(ctypes.addressof(args), ctypes.c_void_p),
        HIP_LAUNCH_PARAM_BUFFER_SIZE,
        ctypes.cast(ctypes.addressof(arg_size), ctypes.c_void_p),
        HIP_LAUNCH_PARAM_END,
    )

    # ── Persistent mode grid: (work_indptr.size(0) - 1, 1, 1) ──
    gdx = meta["work_indptr"].size(0) - 1
    stream = torch.cuda.current_stream().cuda_stream

    ret = _hip.hipModuleLaunchKernel(
        _mla_func,
        gdx, 1, 1,   # grid
        256, 1, 1,   # block (4 wavefronts of 64 threads)
        0,           # shared memory
        stream,
        None,        # kernelParams — must be nullptr for BUFFER_POINTER style
        config,      # extra
    )
    if ret != 0:
        raise RuntimeError(f"hipModuleLaunchKernel failed with error code {ret}")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs       = config["batch_size"]
    qseqlen  = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # ── Regime 1: torch.matmul for small shapes ──
    # Small batch or short context: avoid aiter overhead entirely
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]
        q_3d    = q.view(bs, NUM_HEADS, QK_HEAD_DIM)            # [bs, 16, 576]
        kv_per  = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)       # [bs, kvseqlen, 576]
        scores  = torch.matmul(q_3d, kv_per.transpose(1, 2))    # [bs, 16, kvseqlen]
        scores.mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32).to(torch.bfloat16)
        v_per   = kv_per[:, :, :V_HEAD_DIM]                     # [bs, kvseqlen, 512]
        out     = torch.matmul(weights, v_per)                   # [bs, 16, 512]
        return out.view(bs * qseqlen, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2+3: direct CK-Tile ASM dispatch ──
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _get_cached_metadata(
        bs, qseqlen, kvseqlen,
        q_fp8.dtype, kv_buffer_fp8.dtype,
        qo_indptr, kv_indptr, num_kv_splits,
    )

    # Stage 1: direct hipModuleLaunchKernel (bypasses Python wrapper overhead)
    _launch_mla_stage1(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d, qo_indptr, kv_indptr,
        meta, q_scale, kv_scale,
        qseqlen, num_kv_splits,
    )

    # Stage 2: reduce (must remain via aiter — kernel lives in .so, not .co)
    mla_reduce_v1(
        meta["logits"], meta["attn_lse"],
        meta["reduce_indptr"], meta["reduce_final_map"], meta["reduce_partial_map"],
        qseqlen, meta["output"], None,
    )

    return meta["output"]
