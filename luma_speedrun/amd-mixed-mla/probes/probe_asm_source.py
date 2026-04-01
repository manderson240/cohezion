"""Probe: Read aiter ASM wrapper source to discover kernel argument layout.

We now know hipModuleLaunchKernel is available and kernel functions can be loaded.
The missing piece: what arguments does the MLA kernel expect?

This probe reads the aiter source files on the runner to discover:
1. The C++ pybind11 wrapper that calls hipModuleLaunchKernel
2. The kernel argument struct layout
3. Grid/block dimensions used for launch

Also probes the codegen.py that generates the dispatch table.
"""

import inspect
import os
import sys

import torch
from task import input_t, output_t


# ── Probe: Read codegen.py (generates the ASM dispatch logic) ──
_codegen_path = "/home/runner/aiter/hsa/codegen.py"
if os.path.exists(_codegen_path):
    with open(_codegen_path) as f:
        content = f.read()
    # Print relevant sections (launch config, argument setup)
    lines = content.split("\n")
    print(f"PROBE: codegen.py has {len(lines)} lines", file=sys.stderr)
    # Find hipModuleLaunchKernel or launch-related code
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in [
            "hipmodulelaunchkernel", "launch", "gridsize", "blocksize",
            "args", "kernel_args", "hip.launch", "hipModuleLaunch",
            "launch_kernel", "grid_dim", "block_dim", "shared_mem",
        ]):
            start = max(0, i - 3)
            end = min(len(lines), i + 5)
            print(f"PROBE codegen.py [{start+1}-{end}]:", file=sys.stderr)
            for j in range(start, end):
                print(f"  {j+1}: {lines[j]}", file=sys.stderr)
            print("", file=sys.stderr)

# ── Probe: Read the mla_asm Python wrapper source ──
try:
    from aiter import mla_decode_stage1_asm_fwd
    src = inspect.getsource(mla_decode_stage1_asm_fwd)
    print(f"\nPROBE: mla_decode_stage1_asm_fwd source ({len(src)} chars):", file=sys.stderr)
    print(src[:3000], file=sys.stderr)
    if len(src) > 3000:
        print(f"... [{len(src) - 3000} more chars]", file=sys.stderr)
except Exception as e:
    print(f"PROBE: Cannot get mla_decode_stage1_asm_fwd source: {e}", file=sys.stderr)

# ── Probe: Read the asm_mla.py or similar file ──
_asm_paths = [
    "/home/runner/aiter/aiter/ops/asm_mla.py",
    "/home/runner/aiter/aiter/ops/mla_asm.py",
    "/home/runner/aiter/aiter/mla_asm.py",
    "/home/runner/aiter/hsa/mla_asm.py",
    "/home/runner/aiter/hsa/asm_mla.py",
]
for path in _asm_paths:
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        lines = content.split("\n")
        print(f"\nPROBE: {path} has {len(lines)} lines", file=sys.stderr)
        # Print the launch-related sections
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in [
                "launch", "hipmodule", "args_ptr", "kernel_arg",
                "grid", "block", "stream", "shared_mem", "c_void_p",
                "data_ptr", "numel", "stride",
            ]):
                start = max(0, i - 2)
                end = min(len(lines), i + 4)
                print(f"PROBE {os.path.basename(path)} [{start+1}-{end}]:", file=sys.stderr)
                for j in range(start, end):
                    print(f"  {j+1}: {lines[j]}", file=sys.stderr)
                print("", file=sys.stderr)
        break

# ── Probe: Find all Python files in aiter that reference hipModuleLaunchKernel ──
import glob


_aiter_py_files = glob.glob("/home/runner/aiter/**/*.py", recursive=True)
for pyf in _aiter_py_files:
    try:
        with open(pyf) as f:
            content = f.read()
        if "hipModuleLaunchKernel" in content or "launch_kernel" in content:
            print(f"\nPROBE: {pyf} contains launch references", file=sys.stderr)
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "launch" in line.lower() and ("kernel" in line.lower() or "module" in line.lower()):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 8)
                    for j in range(start, end):
                        print(f"  {j+1}: {lines[j]}", file=sys.stderr)
                    print("", file=sys.stderr)
    except Exception:
        pass

# ── Probe: Check the JIT build C++ source if available ──
_cpp_sources = glob.glob("/home/runner/aiter/aiter/jit/**/*.cpp", recursive=True)
_cpp_sources += glob.glob("/home/runner/aiter/aiter/jit/**/*.cu", recursive=True)
_cpp_sources += glob.glob("/home/runner/aiter/hsa/**/*.cpp", recursive=True)
print(f"\nPROBE: Found {len(_cpp_sources)} C++/CUDA files in aiter JIT/HSA", file=sys.stderr)
for f in _cpp_sources[:10]:
    print(f"  {f}", file=sys.stderr)

# ── Probe: Inspect mla_decode_stage1_asm_fwd signature more carefully ──
try:
    sig = inspect.signature(mla_decode_stage1_asm_fwd)
    print(f"\nPROBE: mla_decode_stage1_asm_fwd signature:", file=sys.stderr)
    for name, param in sig.parameters.items():
        print(f"  {name}: {param.annotation} = {param.default}", file=sys.stderr)
except Exception as e:
    print(f"PROBE: Cannot get signature: {e}", file=sys.stderr)


# ── Actual kernel: known-working aiter path ──
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
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
