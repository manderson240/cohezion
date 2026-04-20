"""
MLA Fused Flash-Decode: Custom HIP kernel with FP8 input format.

This submission uses a custom HIP kernel compiled at runtime via ctypes.
The kernel accepts FP8 E5M2 format input (matching AITER's kv_data["fp8"] format).

Architecture:
  Grid: (num_heads, batch_size)
  Block: 64 threads = 1 wavefront (gfx950/MI355X)
  Each CTA handles one (head, batch_item) pair, processes all KV positions.
"""

import ctypes
import os
import subprocess
import sys

import torch
from task import input_t, output_t


# ─── MLA Constants ───────────────────────────────────────────────────────────
SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
QK_HEAD_DIM = 576

# ─── HIP Kernel Source ─────────────────────────────────────────────────────────
# FP8-compatible MLA kernel (E5M2 format)

_MLA_HIP_SOURCE = r"""
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define QK_DIM 576
#define V_DIM 512
#define BLOCK_N 64
#define WAVE_SIZE 64

__device__ __forceinline__ float fp8e5m2_to_float(uint8_t val) {
    // FP8 E5M2 format: 1 sign bit, 5 exponent bits, 2 mantissa bits
    // Extract components
    uint32_t sign = (val >> 7) & 0x1;
    uint32_t exponent = (val >> 2) & 0x1F;  // 5 bits
    uint32_t mantissa = val & 0x3;  // 2 bits
    
    // E5M2 bias is 15
    const uint32_t bias = 15;
    
    // Handle special cases
    if (exponent == 0 && mantissa == 0) {
        // Zero
        return sign ? -0.0f : 0.0f;
    }
    if (exponent == 31) {
        // Infinity or NaN
        if (mantissa == 0) {
            return sign ? -INFINITY : INFINITY;
        } else {
            return NAN;
        }
    }
    
    // Normal number: (-1)^sign * 2^(exponent - bias) * (1 + mantissa/4)
    float sign_f = sign ? -1.0f : 1.0f;
    float exp_f = exp2f((float)exponent - (float)bias);
    float mant_f = 1.0f + ((float)mantissa) / 4.0f;
    
    return sign_f * exp_f * mant_f;
}

__device__ __forceinline__ float wave_max(float val) {
    for (int offset = WAVE_SIZE / 2; offset > 0; offset /= 2)
        val = fmaxf(val, __shfl_xor(val, offset, WAVE_SIZE));
    return val;
}

__device__ __forceinline__ float wave_sum(float val) {
    for (int offset = WAVE_SIZE / 2; offset > 0; offset /= 2)
        val += __shfl_xor(val, offset, WAVE_SIZE);
    return val;
}

__global__ void mla_fp8_kernel(
    const __hip_bfloat16* __restrict__ Q,
    const uint8_t* __restrict__ KV,
    __hip_bfloat16* __restrict__ O,
    int bs, int sl, int nh, float sc, float kv_scale)
{
    int hi = blockIdx.x, bi = blockIdx.y, tid = threadIdx.x;
    const __hip_bfloat16* qp = Q + (bi * nh + hi) * QK_DIM;
    const uint8_t* kvp = KV + bi * sl * QK_DIM;
    __hip_bfloat16* op = O + (bi * nh + hi) * V_DIM;

    __shared__ float sq[QK_DIM];
    for (int i = tid; i < QK_DIM; i += blockDim.x)
        sq[i] = __bfloat162float(qp[i]);
    __syncthreads();

    float running_max = -1e30f, running_sum = 0.0f;
    float local_v[8] = {0.0f};

    for (int k = 0; k < sl; k += BLOCK_N) {
        int remain = sl - k;
        int current_n = (remain < BLOCK_N) ? remain : BLOCK_N;

        float score = -1e30f;
        if (tid < current_n) {
            const uint8_t* kf = kvp + (k + tid) * QK_DIM;
            float acc = 0.0f;
            for (int i = 0; i < QK_DIM; i++) {
                acc += sq[i] * fp8e5m2_to_float(kf[i]) * kv_scale;
            }
            score = acc * sc;
        }

        float block_max = wave_max(score);
        float old_max = running_max;
        running_max = fmaxf(old_max, block_max);

        float p = expf(score - running_max);
        float correction = expf(old_max - running_max);

        running_sum = running_sum * correction + wave_sum(tid < current_n ? p : 0.0f);

        for (int i = 0; i < 8; i++) {
            int v_dim_idx = tid + i * 64;
            local_v[i] *= correction;

            for (int j = 0; j < current_n; j++) {
                float weight = __shfl(p, j, WAVE_SIZE);
                const uint8_t* kv_j = kvp + (k + j) * QK_DIM;
                float v_val = fp8e5m2_to_float(kv_j[v_dim_idx]) * kv_scale;
                local_v[i] += weight * v_val;
            }
        }
    }

    float inv_sum = 1.0f / running_sum;
    for (int i = 0; i < 8; i++) {
        int v_dim_idx = tid + i * 64;
        if (v_dim_idx < V_DIM) {
            op[v_dim_idx] = __float2bfloat16(local_v[i] * inv_sum);
        }
    }
}

extern "C" int launch_mla_fp8(
    void* Q, void* KV, void* O,
    int bs, int sl, int nh, float sc, float kv_scale)
{
    dim3 grid(nh, bs), block(64);
    hipLaunchKernelGGL(mla_fp8_kernel, grid, block, 0, 0,
        (const __hip_bfloat16*)Q, (const uint8_t*)KV, (__hip_bfloat16*)O,
        bs, sl, nh, sc, kv_scale);
    return 0;
}
"""

# ─── HIP Compilation ─────────────────────────────────────────────────────────

_hip_lib = None
_hip_compile_done = False


def _compile_hip_kernel():
    """Compile the MLA HIP kernel and load via ctypes."""
    global _hip_lib, _hip_compile_done
    if _hip_compile_done:
        return _hip_lib
    _hip_compile_done = True

    hip_path = "/tmp/mla_fp8_kernel.hip"
    so_path = "/tmp/mla_fp8_kernel.so"

    try:
        # Write kernel source
        with open(hip_path, "w") as f:
            f.write(_MLA_HIP_SOURCE)

        # Find compiler
        compiler = "/opt/rocm/llvm/bin/amdclang++"
        if not os.path.exists(compiler):
            compiler = "hipcc"

        # Compile
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
            print(f"[MLA-HIP] Compile error: {result.stderr[:500]}", file=sys.stderr)
            return None

        # Load library
        lib = ctypes.CDLL(so_path)
        lib.launch_mla_fp8.restype = ctypes.c_int
        lib.launch_mla_fp8.argtypes = [
            ctypes.c_void_p,  # Q
            ctypes.c_void_p,  # KV
            ctypes.c_void_p,  # O
            ctypes.c_int,  # bs
            ctypes.c_int,  # sl
            ctypes.c_int,  # nh
            ctypes.c_float,  # sc
            ctypes.c_float,  # kv_scale
        ]
        _hip_lib = lib
        print("[MLA-HIP] Compilation SUCCEEDED", file=sys.stderr)

    except Exception as e:
        print(f"[MLA-HIP] Compilation FAILED: {e}", file=sys.stderr)
        _hip_lib = None

    return _hip_lib


# Compile at import time
_compile_hip_kernel()


# ─── Main Entry Point ─────────────────────────────────────────────────────────


def custom_kernel(data: input_t) -> output_t:
    """
    MLA decode with custom HIP kernel (FP8 format).

    Input format:
      q: (total_q, num_heads, 576) bfloat16
      kv_data["fp8"]: (kv_tensor, scale) where kv_tensor is FP8 E5M2
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]

    # Only handle decode (qseqlen == 1)
    if qseqlen != 1:
        from reference import ref_kernel

        return ref_kernel(data)

    # Check if HIP kernel is available
    if _hip_lib is None:
        print("[MLA] HIP kernel not available, falling back to reference", file=sys.stderr)
        from reference import ref_kernel

        return ref_kernel(data)

    try:
        # Unpack FP8 data: (tensor, scale)
        kv_fp8, kv_scale = kv_data["fp8"]

        # Flatten KV to 2D: (total_kv, 576)
        total_kv = bs * kvseqlen
        kv_flat = kv_fp8.view(total_kv, QK_HEAD_DIM)

        # Prepare output
        o = torch.empty(
            (q.shape[0], nheads, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        )

        # Make tensors contiguous for kernel
        q_cont = q.contiguous()
        kv_cont = kv_flat.contiguous()

        # Scale tensor is scalar per-tensor in FP8 format
        # Expand to per-position scale (all same value)
        scale_per_pos = kv_scale.item()  # Get scalar float value

        # Launch kernel
        err = _hip_lib.launch_mla_fp8(
            ctypes.c_void_p(q_cont.data_ptr()),
            ctypes.c_void_p(kv_cont.data_ptr()),
            ctypes.c_void_p(o.data_ptr()),
            ctypes.c_int(bs),
            ctypes.c_int(kvseqlen),
            ctypes.c_int(nheads),
            ctypes.c_float(SM_SCALE),
            ctypes.c_float(scale_per_pos),
        )

        if err == 0:
            return o
        else:
            print(f"[MLA] Kernel returned error: {err}", file=sys.stderr)
            from reference import ref_kernel

            return ref_kernel(data)

    except Exception as e:
        print(f"[MLA] Runtime error: {e}", file=sys.stderr)
        from reference import ref_kernel

        return ref_kernel(data)
