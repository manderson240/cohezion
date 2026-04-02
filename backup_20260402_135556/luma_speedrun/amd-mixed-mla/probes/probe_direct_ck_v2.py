"""Probe v2: Direct CK kernel dispatch with known function name.

Discovery from probe v1:
  - libamdhip64.so: LOADS
  - hipModuleLoad: WORKS (module handle obtained)
  - 1372 .co files at /home/runner/aiter/hsa/gfx950/mla/
  - Kernel name: _ZN5aiter36mla_a8w8_qh16_qseqlen1_gqaratio16_psE

This probe:
1. Lists ALL kernel names from the .co files via hipModuleGetFunction
2. Attempts to get function handles for the known kernel names
3. Probes hipModuleLaunchKernel if function handle obtained
4. Discovers kernel argument layout by inspecting aiter's JIT module

ALSO: Probes whether we can call the JIT .so directly via ctypes
instead of going through Python pybind11 wrapper.
"""

import ctypes
import glob
import os
import sys

import torch
from task import input_t, output_t


# ── Load HIP runtime ──
hip = ctypes.CDLL("libamdhip64.so")

# ── Known kernel files and their mangled names ──
_CO_DIR = "/home/runner/aiter/hsa/gfx950/mla"
_co_files = sorted(glob.glob(os.path.join(_CO_DIR, "*.co")))
print(f"PROBE v2: {len(_co_files)} .co files in {_CO_DIR}", file=sys.stderr)

# The kernel names from aiter's stdout show the pattern:
# hipModuleLoad: /path/to/<kernel>.co
# GetFunction: _ZN5aiter<len><kernel>E
#
# So for file "mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co",
# the function name is "_ZN5aiter36mla_a8w8_qh16_qseqlen1_gqaratio16_psE"
# where 36 = len("mla_a8w8_qh16_qseqlen1_gqaratio16_ps")

def _mangle_kernel_name(basename: str) -> bytes:
    """Convert .co filename to C++ mangled kernel name."""
    name = basename.replace(".co", "")
    return f"_ZN5aiter{len(name)}{name}E".encode("utf-8")


# ── Probe: Get function handles for ALL MLA kernels ──
_kernel_handles: dict[str, ctypes.c_void_p] = {}
_modules: dict[str, ctypes.c_void_p] = {}

# Focus on the kernels that matter for decode (qseqlen1)
_priority_patterns = [
    "mla_a8w8_qh16_qseqlen1",  # FP8 Q, FP8 KV, 16 heads, decode
    "mla_a16w8_qh16",          # FP16 Q, FP8 KV
    "mla_a16w16_qh16",         # FP16 Q, FP16 KV
]

for co_path in _co_files:
    basename = os.path.basename(co_path)
    # Only probe priority kernels to save time
    if not any(pat in basename for pat in _priority_patterns):
        continue

    module = ctypes.c_void_p()
    err = hip.hipModuleLoad(ctypes.byref(module), co_path.encode("utf-8"))
    if err != 0:
        continue

    func_name = _mangle_kernel_name(basename)
    func = ctypes.c_void_p()
    err = hip.hipModuleGetFunction(ctypes.byref(func), module, func_name)

    if err == 0:
        _kernel_handles[basename] = func
        _modules[basename] = module
        print(f"PROBE v2: GOT FUNCTION {basename} → {func.value}", file=sys.stderr)
    else:
        # Try without _ps suffix
        alt_name = func_name.replace(b"_psE", b"E")
        alt_len = str(len(basename.replace(".co", "").replace("_ps", "")))
        alt_name2 = f"_ZN5aiter{alt_len}{basename.replace('.co', '').replace('_ps', '')}E".encode()
        err2 = hip.hipModuleGetFunction(ctypes.byref(func), module, alt_name2)
        if err2 == 0:
            _kernel_handles[basename] = func
            _modules[basename] = module
            print(f"PROBE v2: GOT FUNCTION (alt) {basename} → {func.value}", file=sys.stderr)

print(f"\nPROBE v2: Successfully loaded {len(_kernel_handles)} kernel functions:", file=sys.stderr)
for name, handle in sorted(_kernel_handles.items()):
    print(f"  {name}: handle={handle.value}", file=sys.stderr)

# ── Probe: Can we access the JIT .so module directly? ──
_JIT_SO = "/home/runner/aiter/aiter/jit/module_mla_asm.so"
_jit_lib = None
try:
    if os.path.exists(_JIT_SO):
        _jit_lib = ctypes.CDLL(_JIT_SO)
        # List all symbols
        print(f"\nPROBE v2: Loaded JIT .so: {_JIT_SO}", file=sys.stderr)
    else:
        print(f"\nPROBE v2: JIT .so not found (may need build first)", file=sys.stderr)
except Exception as e:
    print(f"\nPROBE v2: JIT .so load failed: {e}", file=sys.stderr)

# ── Probe: Check hipModuleLaunchKernel signature ──
try:
    launch_fn = hip.hipModuleLaunchKernel
    print(f"\nPROBE v2: hipModuleLaunchKernel found: {launch_fn}", file=sys.stderr)
except AttributeError:
    print("\nPROBE v2: hipModuleLaunchKernel NOT FOUND in libamdhip64.so", file=sys.stderr)

# ── Probe: Check if we can get data_ptr (need to avoid HIP error state) ──
try:
    _t = torch.zeros(4, device="cuda")
    ptr = _t.data_ptr()
    print(f"PROBE v2: data_ptr() works: {ptr}", file=sys.stderr)
    del _t
except Exception as e:
    print(f"PROBE v2: data_ptr() failed: {e}", file=sys.stderr)

# ── Probe: Check what's in the reduce .co dir ──
_reduce_cos = glob.glob("/home/runner/aiter/hsa/gfx950/reduce/*.co")
print(f"\nPROBE v2: Found {len(_reduce_cos)} reduce kernels", file=sys.stderr)
for co in _reduce_cos[:5]:
    print(f"  {os.path.basename(co)}", file=sys.stderr)

# ── Probe: List all subdirs in hsa/gfx950/ ──
_hsa_dirs = [d for d in glob.glob("/home/runner/aiter/hsa/gfx950/*/") if os.path.isdir(d)]
print(f"\nPROBE v2: HSA subdirectories:", file=sys.stderr)
for d in sorted(_hsa_dirs):
    count = len(glob.glob(os.path.join(d, "*.co")))
    print(f"  {os.path.basename(d.rstrip('/'))}: {count} .co files", file=sys.stderr)

print("\n" + "=" * 60, file=sys.stderr)
print("PROBE v2 SUMMARY:", file=sys.stderr)
print(f"  Kernel functions loaded: {len(_kernel_handles)}", file=sys.stderr)
print(f"  hipModuleLaunchKernel: {'AVAILABLE' if hasattr(hip, 'hipModuleLaunchKernel') else 'MISSING'}", file=sys.stderr)
print(f"  JIT .so direct load: {'OK' if _jit_lib else 'BLOCKED'}", file=sys.stderr)
print("=" * 60, file=sys.stderr)


# ── Actual kernel: Use known-working aiter path ──
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)


NUM_HEADS = 16
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM
V_HEAD_DIM = KV_LORA_RANK
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

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

    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv_bf16 = kv_data["bf16"]
        q_3d = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
        kv_per_batch = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)
        scores = torch.matmul(q_3d, kv_per_batch.transpose(1, 2))
        scores.mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32).to(torch.bfloat16)
        v_per_batch = kv_per_batch[:, :, :V_HEAD_DIM]
        out = torch.matmul(weights, v_per_batch)
        return out.view(bs * qseqlen, NUM_HEADS, V_HEAD_DIM)

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
