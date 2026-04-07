#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Check if HipKittens headers are available on the runner."""

import os, subprocess
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
import aiter
from task import input_t, output_t

# Probe for HipKittens
_hk_available = False
try:
    _probe = load_inline(
        name="hk_probe",
        cpp_sources=["void hk_test();"],
        cuda_sources=[r"""
#include <hip/hip_runtime.h>
// Try including HipKittens
#if __has_include(<hipkittens/hipkittens.cuh>)
#include <hipkittens/hipkittens.cuh>
#define HK_FOUND 1
#elif __has_include("hipkittens/hipkittens.cuh")
#define HK_FOUND 1
#else
#define HK_FOUND 0
#endif

void hk_test() {
    printf("[PROBE] HipKittens available: %d\n", HK_FOUND);
}
"""],
        functions=["hk_test"],
        verbose=True,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _probe.hk_test()
    _hk_available = True
    print("[PROBE] HipKittens load_inline compiled successfully")
except Exception as e:
    print(f"[PROBE] HipKittens probe failed: {e}")

# Also check filesystem
for path in ["/opt/rocm/include/hipkittens", "/home/runner/hipkittens", "/usr/include/hipkittens"]:
    if os.path.exists(path):
        print(f"[PROBE] HipKittens found at: {path}")
        try:
            files = os.listdir(path)[:10]
            print(f"[PROBE] Contents: {files}")
        except:
            pass

# Check ROCm version and include paths
for path in ["/opt/rocm/include", "/opt/rocm/lib"]:
    if os.path.exists(path):
        dirs = [d for d in os.listdir(path) if 'kit' in d.lower() or 'hip' in d.lower()][:10]
        if dirs:
            print(f"[PROBE] {path} hip-related: {dirs}")

# Return correct GEMM result as fallback
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True)
