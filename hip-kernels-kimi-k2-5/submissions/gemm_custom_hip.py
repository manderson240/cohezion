"""
MXFP4 GEMM: Custom HIP kernel with fallback to gemm_a4w4.

Current best: ~22.7µs (gemm_a4w4)
Target: ~9.7µs (leader)

This submission attempts custom HIP kernel compilation,
falling back to proven gemm_a4w4 path if needed.
"""

import ctypes
import os
import subprocess
import sys

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# ─── HIP Kernel Source ─────────────────────────────────────────────────────────
# Simplified MXFP4 GEMM kernel

_GEMM_HIP_SOURCE = r"""
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <stdint.h>

#define WARP_SIZE 64
#define BLOCK_M 128
#define BLOCK_N 128
#define BLOCK_K 128

__device__ __forceinline__ float unpack_fp4(uint8_t val) {
    float sign = ((val >> 3) & 0x1) ? -1.0f : 1.0f;
    float exp = (val >> 2) & 0x1;
    float mant = val & 0x3;
    return exp ? sign * (1.0f + mant * 0.5f) : sign * mant * 0.125f;
}

__device__ __forceinline__ float e8m0_to_float(uint8_t val) {
    int exp = (int)val - 127;
    return exp2f((float)exp);
}

__global__ __launch_bounds__(256, 2)
void mxfp4_gemm_kernel(
    const uint8_t* __restrict__ A_fp4,
    const uint8_t* __restrict__ B_fp4,
    const uint8_t* __restrict__ A_scale,
    const uint8_t* __restrict__ B_scale,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int m_block = blockIdx.y * BLOCK_M;
    int n_block = blockIdx.x * BLOCK_N;
    int tid = threadIdx.x;
    
    int local_m = tid / BLOCK_N;
    int local_n = tid % BLOCK_N;
    
    float acc = 0.0f;
    
    for (int k = 0; k < K; k += 32) {
        int k_group = k / 32;
        
        for (int k_off = 0; k_off < 32 && (k + k_off) < K; k_off++) {
            int global_k = k + k_off;
            
            int a_idx = (m_block + local_m) * (K / 2) + (global_k / 2);
            uint8_t a_packed = A_fp4[a_idx];
            uint8_t a_val = (global_k % 2 == 0) ? (a_packed & 0xF) : (a_packed >> 4);
            
            int b_idx = (n_block + local_n) * (K / 2) + (global_k / 2);
            uint8_t b_packed = B_fp4[b_idx];
            uint8_t b_val = (global_k % 2 == 0) ? (b_packed & 0xF) : (b_packed >> 4);
            
            float a_scale = e8m0_to_float(A_scale[(m_block + local_m) * (K / 32) + k_group]);
            float b_scale = e8m0_to_float(B_scale[(n_block + local_n) * (K / 32) + k_group]);
            
            acc += unpack_fp4(a_val) * a_scale * unpack_fp4(b_val) * b_scale;
        }
    }
    
    int c_idx = (m_block + local_m) * N + (n_block + local_n);
    if ((m_block + local_m) < M && (n_block + local_n) < N) {
        C[c_idx] = __float2bfloat16(acc);
    }
}

extern "C" int launch_mxfp4_gemm(
    void* A_fp4, void* B_fp4,
    void* A_scale, void* B_scale,
    void* C, int M, int N, int K
) {
    dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);
    dim3 block(BLOCK_M * BLOCK_N);
    
    hipLaunchKernelGGL(mxfp4_gemm_kernel, grid, block, 0, 0,
        (const uint8_t*)A_fp4, (const uint8_t*)B_fp4,
        (const uint8_t*)A_scale, (const uint8_t*)B_scale,
        (__hip_bfloat16*)C, M, N, K);
    return 0;
}
"""

# ─── HIP Compilation ─────────────────────────────────────────────────────────

_hip_lib = None
_hip_compile_done = False


def _compile_gemm_hip():
    """Compile the GEMM HIP kernel and load via ctypes."""
    global _hip_lib, _hip_compile_done
    if _hip_compile_done:
        return _hip_lib
    _hip_compile_done = True

    hip_path = "/tmp/gemm_mxfp4_kernel.hip"
    so_path = "/tmp/gemm_mxfp4_kernel.so"

    try:
        with open(hip_path, "w") as f:
            f.write(_GEMM_HIP_SOURCE)

        compiler = "/opt/rocm/llvm/bin/amdclang++"
        if not os.path.exists(compiler):
            compiler = "hipcc"

        result = subprocess.run(
            [
                compiler,
                "-x",
                "hip",
                hip_path,
                "--offload-arch=gfx950",
                "--rocm-path=/opt/rocm",
                "-shared",
                "-fPIC",
                "-o",
                so_path,
                "-D__HIP_PLATFORM_AMD__",
                "-I/opt/rocm/include",
                "-L/opt/rocm/lib",
                "-lamdhip64",
                "-O3",
                "-ffast-math",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"[GEMM-HIP] Compile error: {result.stderr[:500]}", file=sys.stderr)
            return None

        lib = ctypes.CDLL(so_path)
        lib.launch_mxfp4_gemm.restype = ctypes.c_int
        lib.launch_mxfp4_gemm.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _hip_lib = lib
        print("[GEMM-HIP] Compilation SUCCEEDED", file=sys.stderr)

    except Exception as e:
        print(f"[GEMM-HIP] Compilation FAILED: {e}", file=sys.stderr)
        _hip_lib = None

    return _hip_lib


_compile_gemm_hip()


# ─── Main Entry Point ─────────────────────────────────────────────────────────


def custom_kernel(data: input_t) -> output_t:
    """
    MXFP4 GEMM with custom HIP kernel.
    Falls back to gemm_a4w4 if custom kernel unavailable.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    # Quantize A to MXFP4
    A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
    A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
    A_q = A_q_raw.view(dtypes.fp4x2)

    M, K = A.shape
    N = B.shape[0]

    # Check if HIP kernel is available
    if _hip_lib is not None and M <= 128 and N <= 128 and K <= 512:
        try:
            # Simple shapes only for now
            C = torch.empty((M, N), dtype=torch.bfloat16, device="cuda")

            err = _hip_lib.launch_mxfp4_gemm(
                ctypes.c_void_p(A_q.data_ptr()),
                ctypes.c_void_p(B_shuffle.data_ptr()),
                ctypes.c_void_p(A_scale_shuffled.data_ptr()),
                ctypes.c_void_p(B_scale_sh.data_ptr()),
                ctypes.c_void_p(C.data_ptr()),
                ctypes.c_int(M),
                ctypes.c_int(N),
                ctypes.c_int(K),
            )

            if err == 0:
                return C
        except Exception as e:
            print(f"[GEMM] HIP kernel error: {e}", file=sys.stderr)

    # Fallback to proven gemm_a4w4 path
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_shuffled,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
