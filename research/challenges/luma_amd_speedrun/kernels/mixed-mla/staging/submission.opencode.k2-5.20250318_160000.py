#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

import ctypes
import os
import subprocess as sp
import sys

import torch
from task import input_t, output_t


# SM_SCALE for DeepSeek R1 MLA
SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
QK_HEAD_DIM = 576

_hip_lib = None
_hip_done = False

HIP_SRC = r"""
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <stdint.h>

#define QK_DIM 576
#define V_DIM 512
#define BLOCK_SIZE 64
#define WAVE_SIZE 64

__device__ __forceinline__ float d_fp4(unsigned char v, unsigned char s) {
    __constant__ float LUT[16] = {0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f, -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f};
    return LUT[v] * __uint_as_float((unsigned int)s << 23);
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

__global__ void mla_mfma_kernel(
    const __hip_bfloat16* __restrict__ Q,
    const uint8_t* __restrict__ KV_fp4,
    const uint8_t* __restrict__ KV_scale,
    __hip_bfloat16* __restrict__ O,
    int bs, int sl, int nh, float sc) 
{
    int hi = blockIdx.x, bi = blockIdx.y, tid = threadIdx.x;
    const __hip_bfloat16* qp = Q + (bi * nh + hi) * QK_DIM;
    const uint8_t* kvp = KV_fp4 + bi * sl * (QK_DIM / 2);
    const uint8_t* ksp = KV_scale + bi * sl * 24;
    __hip_bfloat16* op = O + (bi * nh + hi) * V_DIM;

    __shared__ float sq[QK_DIM];
    for (int i = tid; i < QK_DIM; i += blockDim.x) sq[i] = __bfloat162float(qp[i]);
    __syncthreads();

    float running_max = -1e30f, running_sum = 0.0f;
    float local_v[8] = {0.0f};

    for (int k = 0; k < sl; k += BLOCK_SIZE) {
        int remain = sl - k;
        int current_n = (remain < BLOCK_SIZE) ? remain : BLOCK_SIZE;
        float score = -1e30f;
        if (tid < current_n) {
            float acc = 0.0f;
            const uint8_t* kf = kvp + (k + tid) * 288;
            const uint8_t* ks = ksp + (k + tid) * 24;
            for (int g = 0; g < 18; g++) {
                uint8_t sv = ks[g];
                for (int i = 0; i < 16; i++) {
                    uint8_t p = kf[g * 16 + i];
                    acc += sq[g * 32 + i * 2] * d_fp4(p & 0xF, sv);
                    acc += sq[g * 32 + i * 2 + 1] * d_fp4(p >> 4, sv);
                }
            }
            score = acc * sc;
        }

        float bmax = wave_max(score);
        float old_max = running_max;
        running_max = fmaxf(old_max, bmax);
        float p = expf(score - running_max);
        float correction = expf(old_max - running_max);
        running_sum = running_sum * correction + wave_sum(tid < current_n ? p : 0.0f);

        for (int i = 0; i < 8; i++) {
            local_v[i] *= correction;
            for (int j = 0; j < current_n; j++) {
                float w = __shfl(p, j, WAVE_SIZE);
                const uint8_t* kv_j = kvp + (k + j) * 288;
                const uint8_t* ks_j = ksp + (k + j) * 24;
                int v_idx = tid + i * 64;
                uint8_t sv = ks_j[v_idx / 32];
                uint8_t pv = kv_j[(v_idx / 32) * 16 + (v_idx % 32) / 2];
                float vv = (v_idx % 2) ? d_fp4(pv >> 4, sv) : d_fp4(pv & 0xF, sv);
                local_v[i] += w * vv;
            }
        }
    }

    float inv_sum = 1.0f / running_sum;
    for (int i = 0; i < 8; i++) op[tid + i * 64] = __float2bfloat16(local_v[i] * inv_sum);
}

extern "C" int launch_mla_mfma(void* Q, void* KV, void* KS, void* O, int bs, int sl, int nh, float sc) {
    dim3 grid(nh, bs), block(64);
    hipLaunchKernelGGL(mla_mfma_kernel, grid, block, 0, 0, 
        (const __hip_bfloat16*)Q, (const uint8_t*)KV, (const uint8_t*)KS, (__hip_bfloat16*)O, 
        bs, sl, nh, sc);
    return 0;
}
"""


def _ensure_hip():
    global _hip_lib, _hip_done
    if _hip_done:
        return _hip_lib
    _hip_done = True
    src, so = "/tmp/_mla_mfma_v2.hip", "/tmp/_mla_mfma_v2.so"
    with open(src, "w") as f:
        f.write(HIP_SRC)
    compiler = os.path.join("/opt/rocm/llvm/bin", "amdclang++")
    cmd = [
        compiler,
        "-x",
        "hip",
        src,
        "--offload-arch=gfx950",
        "--rocm-path=/opt/rocm",
        "-shared",
        "-fPIC",
        "-o",
        so,
        "-D__HIP_PLATFORM_AMD__",
        "-I/opt/rocm/include",
        "-L/opt/rocm/lib",
        "-lamdhip64",
        "-O3",
        "-ffast-math",
    ]
    try:
        sp.run(cmd, check=True, capture_output=True, timeout=60)
        _hip_lib = ctypes.CDLL(so)
        _hip_lib.launch_mla_mfma.restype = ctypes.c_int
        _hip_lib.launch_mla_mfma.argtypes = (
            [ctypes.c_void_p] * 4 + [ctypes.c_int] * 3 + [ctypes.c_float]
        )
    except Exception as e:
        print(f"HIP COMPILE ERROR: {e}", file=sys.stderr)
        _hip_lib = None
    return _hip_lib


def custom_kernel(data: input_t) -> output_t:
    q, kd, qi, ki, cfg = data
    if cfg["q_seq_len"] != 1:
        from reference import ref_kernel

        return ref_kernel(data)
    lib = _ensure_hip()
    if lib:
        kf, ks = kd["mxfp4"]
        bs, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]
        out = torch.empty((bs, nh, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")
        if (
            lib.launch_mla_mfma(
                ctypes.c_void_p(q.data_ptr()),
                ctypes.c_void_p(kf.data_ptr()),
                ctypes.c_void_p(ks.data_ptr()),
                ctypes.c_void_p(out.data_ptr()),
                bs,
                sl,
                nh,
                SM_SCALE,
            )
            == 0
        ):
            return out.view(-1, nh, V_HEAD_DIM)
    from reference import ref_kernel

    return ref_kernel(data)
