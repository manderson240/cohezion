"""MLA Top 10: Custom HIP Kernel with ctypes integration.

This submission compiles and calls a custom HIP kernel at runtime.
Target: 15µs (from 67µs) - 4.5× improvement needed.
"""

import ctypes
import subprocess
import tempfile
from pathlib import Path

import torch
from task import input_t, output_t


# HIP kernel source
HIP_SOURCE = """
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

__global__ void mla_top10_kernel(
    const __hip_bfloat16* __restrict__ Q,
    const uint8_t* __restrict__ KV,
    const uint8_t* __restrict__ KS,
    __hip_bfloat16* __restrict__ O,
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

    float norm = 1.0f / running_sum;
    for (int i = 0; i < 8; i++) {
        int v_idx = tid + i * 64;
        if (v_idx < V_DIM) {
            op[v_idx] = __float2bfloat16(local_v[i] * norm);
        }
    }
}

extern "C" void launch_mla_top10(
    void* q_ptr, void* kv_ptr, void* ks_ptr, void* o_ptr,
    int bs, int sl, int nh, float scale) 
{
    dim3 grid(nh, bs);
    dim3 block(64);
    hipStream_t stream = 0;
    mla_top10_kernel<<<grid, block, 0, stream>>>(
        (__hip_bfloat16*)q_ptr, (uint8_t*)kv_ptr, (uint8_t*)ks_ptr, (__hip_bfloat16*)o_ptr,
        bs, sl, nh, scale);
}
"""

# Global compiled library cache
_LIB_HANDLE = None


def _compile_and_load():
    """Compile HIP kernel and load via ctypes."""
    global _LIB_HANDLE

    if _LIB_HANDLE is not None:
        return _LIB_HANDLE

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write source
        src_path = Path(tmpdir) / "mla_kernel.hip"
        lib_path = Path(tmpdir) / "libmla_top10.so"

        with open(src_path, "w") as f:
            f.write(HIP_SOURCE)

        # Compile
        cmd = [
            "/opt/rocm/llvm/bin/amdclang++",
            "-O3",
            "-fPIC",
            "--offload-arch=gfx950",
            "-D__HIP_PLATFORM_AMD__",
            "-shared",
            "-o",
            str(lib_path),
            str(src_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed: {result.stderr}")

        # Load library
        _LIB_HANDLE = ctypes.CDLL(str(lib_path))

        # Define function signature
        _LIB_HANDLE.launch_mla_top10.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_float,
        ]

        return _LIB_HANDLE


def custom_kernel(data: input_t) -> output_t:
    """Custom MLA kernel with embedded HIP compilation."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    sl = config["kv_seq_len"]
    nh = config["num_heads"]

    # Get FP8 KV data
    kv_fp8, kv_scale = kv_data["fp8"]

    # Prepare output
    o = torch.empty((q.shape[0], nh, 512), dtype=torch.bfloat16, device="cuda")

    # Compile and load kernel
    lib = _compile_and_load()

    # Launch kernel
    lib.launch_mla_top10(
        q.data_ptr(),
        kv_fp8.data_ptr(),
        kv_scale.data_ptr(),
        o.data_ptr(),
        bs,
        sl,
        nh,
        1.0 / (576**0.5),
    )

    return o
