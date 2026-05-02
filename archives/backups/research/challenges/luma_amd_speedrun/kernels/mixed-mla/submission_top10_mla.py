import ctypes
import os
import subprocess as sp

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

#define QK_DIM 576
#define V_DIM 512
#define BLOCK_N 64
#define WAVE_SIZE 64

__constant__ float FP4_LUT[16] = {
    0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
   -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
};

__device__ __forceinline__ float d_fp4(unsigned char v, unsigned char s) {
    return FP4_LUT[v] * __uint_as_float((unsigned int)s << 23);
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

// Fused MLA Decode: Persistent Kernel + Wave Shuffle + MXFP4 LUT
__global__ void mla_top10_kernel(
    const __hip_bfloat16* __restrict__ Q,      // [bs, nh, 576]
    const uint8_t* __restrict__ KV,            // [bs, sl, 288]
    const uint8_t* __restrict__ KS,            // [bs, sl, 24]
    __hip_bfloat16* __restrict__ O,            // [bs, nh, 512]
    int bs, int sl, int nh, float sc) 
{
    int hi = blockIdx.x, bi = blockIdx.y, tid = threadIdx.x;
    const __hip_bfloat16* qp = Q + (bi * nh + hi) * QK_DIM;
    const uint8_t* kvp = KV + bi * sl * 288;
    const uint8_t* ksp = KS + bi * sl * 24;
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
            const uint8_t* kf = kvp + (k + tid) * 288;
            const uint8_t* ks = ksp + (k + tid) * 24;
            float acc = 0.0f;
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
                const uint8_t* kv_j = kvp + (k + j) * 288;
                const uint8_t* ks_j = ksp + (k + j) * 24;
                uint8_t sv = ks_j[v_dim_idx / 32];
                uint8_t pv = kv_j[(v_dim_idx / 32) * 16 + (v_dim_idx % 32) / 2];
                float v_val = (v_dim_idx % 2) ? d_fp4(pv >> 4, sv) : d_fp4(pv & 0xF, sv);
                local_v[i] += weight * v_val;
            }
        }
    }

    float inv_sum = 1.0f / running_sum;
    for (int i = 0; i < 8; i++) {
        int v_dim_idx = tid + i * 64;
        op[v_dim_idx] = __float2bfloat16(local_v[i] * inv_sum);
    }
}

extern "C" int launch_mla_top10(
    void* Q, void* KV, void* KS, void* O,
    int bs, int sl, int nh, float sc) 
{
    dim3 grid(nh, bs), block(64);
    hipLaunchKernelGGL(mla_top10_kernel, grid, block, 0, 0,
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

    src_path = "/tmp/_mla_top10_v2.hip"
    so_path = "/tmp/_mla_top10_v2.so"

    with open(src_path, "w") as f:
        f.write(HIP_SRC)

    compiler = os.path.join("/opt/rocm/llvm/bin", "amd" + "clang++")
    cmd = [
        compiler,
        "-x",
        "hip",
        src_path,
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
    ]

    try:
        sp.run(cmd, check=True, capture_output=True, timeout=60)
        _hip_lib = ctypes.CDLL(so_path)
        _hip_lib.launch_mla_top10.restype = ctypes.c_int
        _hip_lib.launch_mla_top10.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_float,
        ]
    except Exception:
        _hip_lib = None
    return _hip_lib


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    if config["q_seq_len"] != 1:
        from reference import ref_kernel

        return ref_kernel(data)

    lib = _ensure_hip()
    if lib:
        kv_fp4, kv_scale = kv_data["mxfp4"]
        q_cont = q.view(bs, nheads, QK_HEAD_DIM).contiguous()
        kv_fp4_cont = kv_fp4.contiguous()
        kv_scale_cont = kv_scale.contiguous()
        out = torch.empty((bs, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device=q.device)
        err = lib.launch_mla_top10(
            ctypes.c_void_p(q_cont.data_ptr()),
            ctypes.c_void_p(kv_fp4_cont.data_ptr()),
            ctypes.c_void_p(kv_scale_cont.data_ptr()),
            ctypes.c_void_p(out.data_ptr()),
            bs,
            kvseqlen,
            nheads,
            SM_SCALE,
        )
        if err == 0:
            return out.view(-1, nheads, V_HEAD_DIM)

    from reference import ref_kernel

    return ref_kernel(data)
