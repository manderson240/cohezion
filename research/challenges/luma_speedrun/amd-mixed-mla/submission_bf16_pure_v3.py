#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA Variant 2: BF16-Only Pure Attention without Quantization.

Key Optimizations:
- Eliminates ALL quantization overhead (no FP8 Q quant, no KV scale handling)
- Pure BF16 arithmetic from input to output (tolerates 10% error margin)
- Fused Q@K and softmax in single kernel launch
- No dtype conversions, no scale multiplications
- Optimized memory access patterns for BF16 loads/stores

This variant maximizes throughput by removing quantization/dequantization
bottlenecks that exist in FP8 paths. BF16 has native hardware support on
MI355X and sufficient precision for the task's 10% tolerance.
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256

// BF16-only attention kernel - no quantization whatsoever
// Processes entire attention in fused manner
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_bf16_attention_kernel(
    const __hip_bfloat16* __restrict__ Q,       // [total_q, NUM_HEADS, QK_DIM]
    const __hip_bfloat16* __restrict__ KV,      // [total_kv, QK_DIM]
    __hip_bfloat16* __restrict__ output,        // [total_q, NUM_HEADS, V_DIM]
    const int* __restrict__ kv_indptr,          // [batch_size + 1]
    int batch_size, int total_q, int num_splits,
    float sm_scale
) {
    // Grid: (split_id, head_id, batch_id)
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;
    int wid = tid / WAVESIZE;
    int lid = tid % WAVESIZE;

    // KV range for this batch
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    // Split range
    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    // Q for this (batch, head)
    int q_idx = batch_id;  // decode: qseqlen=1
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    // Load Q into registers (cooperative)
    __shared__ float q_shared[QK_DIM];
    #pragma unroll 3
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator
    float v_acc[2] = {0.0f, 0.0f};  // V_DIM/BLOCK_SIZE = 2

    // Process KV entries
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Q@K^T dot product - pure BF16 arithmetic
        float dot = 0.0f;
        #pragma unroll 3
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            dot += q_shared[d] * __bfloat162float(kv_ptr[d]);
        }

        // Warp reduction
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        __shared__ float warp_dots[4];
        if (lid == 0) {
            warp_dots[wid] = dot;
        }
        __syncthreads();

        float score;
        if (tid == 0) {
            score = (warp_dots[0] + warp_dots[1] + warp_dots[2] + warp_dots[3]) * sm_scale;
            warp_dots[0] = score;
        }
        __syncthreads();
        score = warp_dots[0];

        // Online softmax
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = (old_max > -1e20f) ? expf(old_max - new_max) : 0.0f;

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate V - first V_DIM elements
        float weight = exp_score;
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Write to output buffer (intermediate for multi-split)
    // Each split writes its partial result, final reduction needed
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Store partial V
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            // Use float output for accumulation
            int idx = out_base * V_DIM + v_idx;
            // Write via atomic or to intermediate - simplified: direct write with flag
        }
    }
}

// Single-split BF16 attention - no reduction needed
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_bf16_singlesplit_kernel(
    const __hip_bfloat16* __restrict__ Q,
    const __hip_bfloat16* __restrict__ KV,
    __hip_bfloat16* __restrict__ output,
    const int* __restrict__ kv_indptr,
    int batch_size, int total_q,
    float sm_scale
) {
    int head_id = blockIdx.x;
    int batch_id = blockIdx.y;
    int tid = threadIdx.x;
    int wid = tid / WAVESIZE;
    int lid = tid % WAVESIZE;

    // KV range
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];

    // Q for this (batch, head)
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    // Cooperative Q load
    __shared__ float q_shared[QK_DIM];
    #pragma unroll 3
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // Online softmax
    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    // Process all KV
    for (int kv_idx = kv_start; kv_idx < kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Q@K dot product
        float dot = 0.0f;
        #pragma unroll 3
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            dot += q_shared[d] * __bfloat162float(kv_ptr[d]);
        }

        // Warp reduction
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        __shared__ float warp_dots[4];
        if (lid == 0) {
            warp_dots[wid] = dot;
        }
        __syncthreads();

        float score;
        if (tid == 0) {
            score = (warp_dots[0] + warp_dots[1] + warp_dots[2] + warp_dots[3]) * sm_scale;
            warp_dots[0] = score;
        }
        __syncthreads();
        score = warp_dots[0];

        // Online softmax
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = (old_max > -1e20f) ? expf(old_max - new_max) : 0.0f;

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Weighted V accumulation
        float weight = exp_score;
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Final normalization and write
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            float val = v_acc[vi] / running_sum;
            int out_idx = ((q_idx * NUM_HEADS + head_id) * V_DIM + v_idx);
            output[out_idx] = __float2bfloat16(val);
        }
    }
}

void launch_mla_bf16_pure(
    torch::Tensor Q, torch::Tensor KV, torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    if (num_splits == 1) {
        // Single-split: direct output, no reduction needed
        dim3 grid(NUM_HEADS, batch_size, 1);
        mla_bf16_singlesplit_kernel<<<grid, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
            kv_indptr.data_ptr<int>(),
            batch_size, total_q, sm_scale);
    } else {
        // Multi-split: requires reduction (not implemented - fall back)
        // For now, use single-split
        dim3 grid(NUM_HEADS, batch_size, 1);
        mla_bf16_singlesplit_kernel<<<grid, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
            kv_indptr.data_ptr<int>(),
            batch_size, total_q, sm_scale);
    }
}
"""

CPP_SOURCE = """
void launch_mla_bf16_pure(torch::Tensor Q, torch::Tensor KV, torch::Tensor output,
                          torch::Tensor kv_indptr,
                          int batch_size, int total_q, int num_splits, float sm_scale);
"""

# Compile the kernel
try:
    _mod_bf16 = load_inline(
        name="mla_bf16_pure_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_bf16_pure"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-ffast-math"],
    )
    _BF16_OK = True
except Exception as e:
    print(f"[bf16_pure] Build failed: {e}")
    _BF16_OK = False

# Constants
NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1

# Thresholds
EINSUM_MAX_TOTAL_KV = 4096
BF16_DIRECT_MAX_TOTAL_KV = 32768  # Up to this size, use direct BF16 kernel

# Caches
_bf16_cache = {}


def _einsum_attention(data):
    """Pure PyTorch einsum for small shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, NUM_HEADS, V_DIM).to(torch.bfloat16)
    )


def _bf16_pure_attention(data):
    """Pure BF16 custom kernel without any quantization."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_q = bs  # decode: qseqlen=1

    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    # Get or create output buffer
    key = (bs, "bf16_pure_output")
    if key not in _bf16_cache:
        _bf16_cache.clear()
        _bf16_cache[key] = torch.empty(
            (total_q, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"
        )

    output = _bf16_cache[key]

    _mod_bf16.launch_mla_bf16_pure(q, kv_flat, output, kv_indptr, bs, total_q, 1, SM_SCALE)
    return output


def _aiter_bf16_attention(data):
    """aiter BF16 fallback - no quantization, pure BF16."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_bf16 = kv_data["bf16"]
    num_kv_splits = 1 if total_kv <= 8192 else 4

    kv_4d = kv_bf16.view(kv_bf16.shape[0], PAGE_SIZE, 1, QK_HEAD_DIM)

    key = ("aiter_bf16", bs, qseqlen, kvseqlen, num_kv_splits)
    if key not in _bf16_cache:
        kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(
            bs,
            qseqlen,
            NUM_HEADS,
            torch.bfloat16,
            torch.bfloat16,
            is_sparse=False,
            fast_mode=False,
            num_kv_splits=num_kv_splits,
            intra_batch_mode=True,
        )
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, ws, ri, rf, rp = work
        get_mla_metadata_v1(
            qo_indptr,
            kv_indptr,
            kv_last_page_len,
            NUM_HEADS,
            1,
            True,
            wm,
            ws,
            wi,
            ri,
            rf,
            rp,
            page_size=PAGE_SIZE,
            kv_granularity=max(PAGE_SIZE, 16),
            max_seqlen_qo=qseqlen,
            uni_seqlen_qo=qseqlen,
            fast_mode=False,
            max_split_per_batch=num_kv_splits,
            intra_batch_mode=True,
            dtype_q=torch.bfloat16,
            dtype_kv=torch.bfloat16,
        )
        total_q_val = bs * qseqlen
        _bf16_cache[key] = {
            "work_metadata": wm,
            "work_indptr": wi,
            "work_info_set": ws,
            "reduce_indptr": ri,
            "reduce_final_map": rf,
            "reduce_partial_map": rp,
            "kv_indices": torch.arange(int(kv_indptr[-1].item()), dtype=torch.int32, device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "output": torch.empty(
                (total_q_val, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"
            ),
        }

    meta = _bf16_cache[key]

    aiter.mla_decode_fwd(
        q.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        meta["output"],
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=1,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_kv_splits,
        q_scale=None,  # No Q quantization
        kv_scale=None,  # No KV quantization
        intra_batch_mode=True,
        work_meta_data=meta["work_metadata"],
        work_indptr=meta["work_indptr"],
        work_info_set=meta["work_info_set"],
        reduce_indptr=meta["reduce_indptr"],
        reduce_final_map=meta["reduce_final_map"],
        reduce_partial_map=meta["reduce_partial_map"],
    )
    return meta["output"]


def custom_kernel(data: input_t) -> output_t:
    """Main entry: pure BF16 attention, no quantization."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Small shapes: einsum
    if total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Medium shapes: try custom BF16 kernel
    if _BF16_OK and total_kv <= BF16_DIRECT_MAX_TOTAL_KV:
        try:
            return _bf16_pure_attention(data)
        except Exception as e:
            print(f"[bf16_pure] Runtime error: {e}")

    # All other shapes: aiter BF16
    return _aiter_bf16_attention(data)
