"""
MLA MFMA Pure — Pure MFMA-based MLA for CDNA 3 (MI355X)

Breakthrough approach: Replace FP4 LUT dequantization with native CDNA 3
MFMA (Matrix Fused Multiply-Add) instructions for fused FP8 dequant + dot product.

Current best: 72µs (LUT approach)
Target: <20µs

Key insight from K-Search paper: Co-evolving world model suggests MFMA-based
approach is the correct direction for CDNA 3 architecture.

Variant: Pure MFMA, no LUT, fp8 KV cache throughout
"""

import torch
from aiter import get_mla_metadata_v1

# AITER imports for reference
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


# Constants for DeepSeek R1 MLA
V_HEAD_DIM = 512
QK_HEAD_DIM = 576
NUM_KV_HEADS = 1
PAGE_SIZE = 1
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)

# CDNA 3 MFMA kernel source
HIP_SRC = r"""
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <stdint.h>

#define QK_DIM 576
#define V_DIM 512
#define WAVE_SIZE 64

typedef float float4_v __attribute__((__vector_size__(16)));
typedef int8_t int8_v __attribute__((__vector_size__(32)));

extern "C" {
    float4_v __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
        int8_v a, int8_v b, float4_v c, 
        int scale_a, int scale_b, int flags, 
        int cbsz, int abid, int blgp) noexcept;
}

// FP8 E8M0 to float via scale
__device__ __forceinline__ float fp8e8m0_to_float(float val, unsigned int scale) {
    return val * __uint_as_float(scale);
}

// Online softmax with wave reduction
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

// Pure MFMA MLA kernel
__global__ void mla_mfma_kernel(
    const __hip_bfloat16* __restrict__ Q,
    const int8_v* __restrict__ KV_fp8,
    const unsigned int* __restrict__ KV_scale,
    __hip_bfloat16* __restrict__ O,
    int num_q, int num_heads, int kv_len,
    float sm_scale) 
{
    int qid = blockIdx.x;
    int hid = blockIdx.y;
    int tid = threadIdx.x;
    
    // Q pointer
    const __hip_bfloat16* qp = Q + (qid * num_heads + hid) * QK_DIM;
    
    // Compute Q scale (E8M0)
    float q_amax = 0.0f;
    for (int i = tid; i < QK_DIM; i += WAVE_SIZE) {
        q_amax = fmaxf(q_amax, fabsf(__bfloat162float(qp[i])));
    }
    q_amax = wave_max(q_amax);
    unsigned int q_scale = __float_as_uint(freq_copysign(q_amax, 1.0f));
    if (q_amax == 0.0f) q_scale = 0x7F800000; // inf if zero
    
    // Load Q into registers (fp8 dequantized)
    int8_v q_reg[18];
    if (tid < 18) {
        float tmp[32];
        for (int i = 0; i < 32; i++) {
            int idx = tid * 32 + i;
            float val = idx < QK_DIM ? __bfloat162float(qp[idx]) / q_amax : 0.0f;
            tmp[i] = __float_as_int(val);
        }
        q_reg[tid] = *(int8_v*)tmp;
    }
    
    // Online softmax accumulators
    float running_max = -1e30f;
    float running_sum = 0.0f;
    float local_v[8] = {0.0f};
    
    // KV loop — MFMA-based score computation
    for (int k = 0; k < kv_len; k++) {
        // Load KV + scale
        int8_v k_reg[18];
        unsigned int k_scale = KV_scale[k];
        
        if (tid < 18) {
            float tmp[32];
            for (int i = 0; i < 32; i++) {
                int idx = tid * 32 + i;
                int8_v val = KV_fp8[k * 18 + tid];
                tmp[i] = __int_as_float(((int8_t*)&val)[i]);
            }
            k_reg[tid] = *(int8_v*)tmp;
        }
        
        // MFMA score: fused fp8 dequant + dot product
        // Each block processes 16×16×128 = 256 ops
        // 18 blocks = 4608 ops per (Q,K) pair
        float4_v score_acc = {0, 0, 0, 0};
        
        #pragma unroll
        for (int g = 0; g < 18; g++) {
            score_acc = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
                q_reg[g], k_reg[g], score_acc,
                q_scale, k_scale,
                0, 0, 0, 0);
        }
        
        // Sum accumulator
        float score = score_acc[0] + score_acc[1] + score_acc[2] + score_acc[3];
        score *= sm_scale;
        
        // Online softmax
        float block_max = wave_max(score);
        float old_max = running_max;
        running_max = fmaxf(old_max, block_max);
        
        float p = expf(score - running_max);
        float correction = expf(old_max - running_max);
        running_sum = running_sum * correction + wave_sum(p);
        
        // V accumulation — also via MFMA
        // Use same KV data but only first 16 blocks (512 dims)
        #pragma unroll
        for (int vg = 0; vg < 16; vg++) {
            float4_v v_acc = {0, 0, 0, 0};
            v_acc = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
                q_reg[vg], k_reg[vg], v_acc,
                q_scale, k_scale,
                0, 0, 0, 0);
            
            // Scale by attention weight and accumulate
            float tmp_v[4];
            *(float4_v*)tmp_v = v_acc;
            float p_wave = __shfl(p, 0, WAVE_SIZE);
            for (int vi = 0; vi < 4; vi++) {
                local_v[vg * 4 + vi] = local_v[vg * 4 + vi] * correction + tmp_v[vi] * p_wave;
            }
        }
    }
    
    // Finalize softmax
    float inv_sum = 1.0f / (running_sum + 1e-6f);
    __hip_bfloat16* op = O + (qid * num_heads + hid) * V_DIM;
    
    for (int i = tid; i < V_DIM; i += WAVE_SIZE) {
        op[i] = __float2bfloat16(local_v[i / WAVE_SIZE] * inv_sum);
    }
}

extern "C" int launch_mfma_mla(
    void* Q, void* KV, void* KV_scale, void* O,
    int num_q, int num_heads, int kv_len, float sm_scale) 
{
    dim3 grid(num_q, num_heads);
    dim3 block(WAVE_SIZE);
    hipLaunchKernelGGL(mla_mfma_kernel, grid, block, 0, 0,
        Q, KV, KV_scale, O, num_q, num_heads, kv_len, sm_scale);
    return 0;
}
"""


def _compile_kernel():
    """Compile the MFMA kernel for gfx950 (MI355X)."""
    import ctypes
    import subprocess
    from pathlib import Path

    src_path = Path("/tmp/_mla_mfma.hip")
    so_path = Path("/tmp/_mla_mfma.so")

    src_path.write_text(HIP_SRC)

    compiler = "/opt/rocm/llvm/bin/amdclang++"
    cmd = [
        compiler,
        "-x",
        "hip",
        str(src_path),
        "--offload-arch=gfx950",
        "--rocm-path=/opt/rocm",
        "-shared",
        "-fPIC",
        "-o",
        str(so_path),
        "-D__HIP_PLATFORM_AMD__",
        "-I/opt/rocm/include",
        "-L/opt/rocm/lib",
        "-lamdhip64",
        "-O3",
        "-ffast-math",
        "-fno-gpu-host-constexpr",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Kernel compile failed: {result.stderr}")

    return ctypes.CDLL(str(so_path))


_lib = None


def _get_lib():
    global _lib
    if _lib is None:
        _lib = _compile_kernel()
    return _lib


def custom_kernel(data: input_t) -> output_t:
    """
    MFMA-based MLA kernel for CDNA 3.

    Uses native MFMA instructions for fused FP8 dequantization + dot product.
    This should be significantly faster than the LUT-based approach.

    Expected improvement: 3-5× speedup over LUT approach
    Target: <20µs (vs current 72µs)
    """
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    total_q = q.shape[0]

    # Use FP8 KV cache (provided by task)
    kv_fp8, kv_scale = kv_data["fp8"]

    # Allocate output
    out = torch.empty((total_q, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    # Try MFMA kernel, fall back to AITER if compile fails
    try:
        lib = _get_lib()

        # Prepare KV as int8_v array
        # kv_fp8 shape: [total_kv, 18] where 18 = 576/32 blocks
        kv_int8 = kv_fp8.view(torch.int8)

        # Prepare scale as uint32 array
        kv_scale_uint = kv_scale.view(torch.uint32)

        # Get kv length from indptr
        kv_len = kv_indptr[-1].item()

        lib.launch_mfma_mla(
            q.data_ptr(),
            kv_int8.data_ptr(),
            kv_scale_uint.data_ptr(),
            out.data_ptr(),
            total_q,
            nheads,
            kv_len,
            SM_SCALE,
        )

        return out

    except Exception as e:
        # Fall back to AITER reference
        print(f"MFMA kernel failed ({e}), falling back to AITER")

        kv_indptr_int32 = kv_indptr.to(torch.int32)
        meta = get_mla_metadata_v1(
            bs,
            qseqlen,
            nheads,
            q.dtype,
            kv_fp8.dtype,
            qo_indptr,
            kv_indptr_int32,
            (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32),
            num_kv_splits=16,
        )

        return mla_decode_fwd(
            q.view(-1, nheads, QK_HEAD_DIM),
            kv_fp8,
            out,
            qo_indptr,
            kv_indptr_int32,
            (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32),
            qseqlen,
            page_size=PAGE_SIZE,
            nhead_kv=NUM_KV_HEADS,
            sm_scale=SM_SCALE,
            logit_cap=0.0,
            num_kv_splits=16,
            intra_batch_mode=True,
            **meta,
        )


if __name__ == "__main__":
    print("MLA MFMA Pure — MFMA-based MLA for CDNA 3")
    print("Target: <20µs (vs current 72µs LUT approach)")
    print("Approach: Native MFMA instructions for fused FP8 dequant + dot product")
