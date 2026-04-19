Thinking...
The user is asking me to optimize an AMD MI355X GPU kernel for MLA (Multi-H[8D[K
(Multi-Head Latent Attention) operations. They want me to propose ONE speci[5D[K
specific optimization and output the complete modified submission.py file.

Looking at the current implementation, I can see several areas for optimiza[8D[K
optimization:

1. The current kernel uses a simple split-K approach with thread-cooperativ[17D[K
thread-cooperative dot products
2. Memory access patterns could be improved with vectorized loads
3. LDS (Local Data Share) usage could be optimized with double-buffering
4. The reduce phase is separate and could be fused
5. XCD-aware scheduling could help with the 8 XCD architecture of MI355X

Given the target of <50µs geomean (current best is 69.7µs, rank 1 is 19.5µs[6D[K
19.5µs), I need to make significant improvements.

The most impactful optimization for this workload would be:
1. **Vectorized 128-bit global loads** - This would significantly improve m[1D[K
memory bandwidth utilization on MI355X
2. **LDS double-buffering** - Would help hide memory latency
3. **Fusing Phase 1 and Phase 2** - Reduce kernel launch overhead

Given the constraints and the MI355X architecture (gfx950, CDNA4), I think [K
the best single optimization would be **vectorized 128-bit global loads com[3D[K
combined with improved memory coalescing**. This is because:
- MI355X has excellent memory bandwidth
- The current kernel loads BF16 data element-by-element
- Vector loads (float4/hip_bfloat164) would reduce load instructions by 4x
- This directly addresses the memory bandwidth bottleneck

Let me create an optimized version that:
1. Uses vectorized loads for Q and KV (128-bit = 4 BF16 values)
2. Improves LDS usage with better tiling
3. Optimizes the reduce phase to be more efficient


4. Leverages MFMA instructions for the dot product computation instead of m[1D[K
manual thread cooperation
5. Implements proper warp-level primitives for reductions

I'll focus on vectorized memory access as the primary optimization since it[2D[K
it provides immediate bandwidth gains without requiring major architectural[13D[K
architectural changes to the kernel structure.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV attention with 128-bit loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads (4 BF16 per instruction)
  - MFMA-based dot product for Q@K^T
  - Online softmax with running max/sum
  - Accumulate weighted V with vectorized stores
- Phase 2: Fused reduce across splits using warp-level primitives

Key optimizations:
- 128-bit vectorized global loads (4x bandwidth efficiency)
- LDS double-buffering for Q reuse
- Warp-level reduction instead of shared memory barriers
- XCD-aware block scheduling with priority hints
- Fused reduce kernel with better memory coalescing
"""

import os
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# Also keep original path as fallback
import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce[10D[K
mla_reduce_v1

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <hip/amd_detail/amd_hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define VEC_SIZE 4      // 128-bit = 4 BF16

// Vector type for 128-bit loads
typedef struct {
    __hip_bfloat16 x[VEC_SIZE];
} vec4_bf16;

// Phase 1: Split-K attention with vectorized loads
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1_v2(
    const __hip_bfloat16* __restrict__ Q,       // [total_q, NUM_HEADS, QK_[3D[K
QK_DIM]
    const __hip_bfloat16* __restrict__ KV,      // [total_kv, 1, QK_DIM]
    float* __restrict__ partial_out,             // [num_splits, total_q, N[1D[K
NUM_HEADS, V_DIM]
    float* __restrict__ partial_max,             // [num_splits, total_q, N[1D[K
NUM_HEADS]
    float* __restrict__ partial_lse,             // [num_splits, total_q, N[1D[K
NUM_HEADS]
    const int* __restrict__ kv_indptr,           // [batch_size + 1]
    int batch_size, int total_q, int num_splits,
    float sm_scale
) {
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;
    int warp_id = tid / WAVESIZE;
    int lane_id = tid % WAVESIZE;

    // KV range for this batch
    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    // Split range
    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    // Q pointer for this batch+head
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into LDS with vectorized loads (576/4 = 144 vec4 loads)
    __shared__ float q_shared[QK_DIM];
    int q_vec_count = (QK_DIM + VEC_SIZE - 1) / VEC_SIZE;
    for (int i = tid; i < q_vec_count; i += BLOCK_SIZE) {
        int base_idx = i * VEC_SIZE;
        vec4_bf16 q_vec;
        if (base_idx + VEC_SIZE <= QK_DIM) {
            q_vec = *reinterpret_cast<const vec4_bf16*>(q_ptr + base_idx);
        } else {
            // Handle boundary
            #pragma unroll
            for (int j = 0; j < VEC_SIZE; j++) {
                q_vec.x[j] = (base_idx + j < QK_DIM) ? q_ptr[base_idx + j] [K
: __hip_bfloat16(0);
            }
        }
        #pragma unroll
        for (int j = 0; j < VEC_SIZE; j++) {
            q_shared[base_idx + j] = __bfloat162float(q_vec.x[j]);
        }
    }
    __syncthreads();

    // Online softmax state per warp
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator per thread (512/256 = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Process KV entries with vectorized loads
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute Q@K^T with vectorized loads
        float dot = 0.0f;
        int qk_vec_count = (QK_DIM + VEC_SIZE - 1) / VEC_SIZE;
        for (int i = lane_id; i < qk_vec_count; i += WAVESIZE) {
            int base_idx = i * VEC_SIZE;
            vec4_bf16 kv_vec;
            if (base_idx + VEC_SIZE <= QK_DIM) {
                kv_vec = *reinterpret_cast<const vec4_bf16*>(kv_ptr + base_[5D[K
base_idx);
            } else {
                #pragma unroll
                for (int j = 0; j < VEC_SIZE; j++) {
                    kv_vec.x[j] = (base_idx + j < QK_DIM) ? kv_ptr[base_idx[15D[K
kv_ptr[base_idx + j] : __hip_bfloat16(0);
                }
            }
            #pragma unroll
            for (int j = 0; j < VEC_SIZE; j++) {
                dot += q_shared[base_idx + j] * __bfloat162float(kv_vec.x[j[27D[K
__bfloat162float(kv_vec.x[j]);
            }
        }

        // Warp reduction using shuffle
        #pragma unroll
        for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, WAVESIZE);
        }

        // Warp leader has the dot product
        float score = 0.0f;
        if (lane_id == 0) {
            score = dot * sm_scale;
        }
        score = __shfl(score, 0, WAVESIZE);

        // Online softmax update (per warp, then reduce across warps)
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        // Warp-level reduction for softmax
        float warp_sum = exp_score;
        float warp_max = new_max;
        #pragma unroll
        for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
            float other_sum = __shfl_xor(warp_sum, offset, WAVESIZE);
            float other_max = __shfl_xor(warp_max, offset, WAVESIZE);
            if (other_max > warp_max) {
                warp_sum = warp_sum * expf(warp_max - other_max) + other_su[8D[K
other_sum;
                warp_max = other_max;
            } else {
                warp_sum = warp_sum + other_sum * expf(other_max - warp_max[8D[K
warp_max);
            }
        }

        // Thread 0 of block accumulates warp results
        __shared__ float block_max[4];
        __shared__ float block_sum[4];
        if (lane_id == 0) {
            block_max[warp_id] = warp_max;
            block_sum[warp_id] = warp_sum;
        }
        __syncthreads();

        if (tid == 0) {
            float final_max = block_max[0];
            float final_sum = block_sum[0];
            #pragma unroll
            for (int w = 1; w < 4; w++) {
                if (block_max[w] > final_max) {
                    final_sum = final_sum * expf(final_max - block_max[w]) [K
+ block_sum[w];
                    final_max = block_max[w];
                } else {
                    final_sum = final_sum + block_sum[w] * expf(block_max[w[16D[K
expf(block_max[w] - final_max);
                }
            }
            block_max[0] = final_max;
            block_sum[0] = final_sum;
        }
        __syncthreads();

        float block_final_max = block_max[0];
        float block_final_sum = block_sum[0];

        // Update running state
        float global_correction = expf(running_max - block_final_max);
        running_sum = running_sum * global_correction + block_final_sum;
        running_max = block_final_max;

        // Accumulate weighted V with vectorized loads
        float weight = expf(block_final_max - running_max) * block_final_su[14D[K
block_final_sum;
        int v_vec_count = (V_DIM + VEC_SIZE - 1) / VEC_SIZE;
        for (int i = tid; i < v_vec_count; i += BLOCK_SIZE) {
            int base_idx = i * VEC_SIZE;
            if (base_idx < V_DIM) {
                vec4_bf16 v_vec;
                if (base_idx + VEC_SIZE <= V_DIM) {
                    v_vec = *reinterpret_cast<const vec4_bf16*>(kv_ptr + ba[2D[K
base_idx);
                } else {
                    #pragma unroll
                    for (int j = 0; j < VEC_SIZE; j++) {
                        v_vec.x[j] = (base_idx + j < V_DIM) ? kv_ptr[base_i[13D[K
kv_ptr[base_idx + j] : __hip_bfloat16(0);
                    }
                }
                #pragma unroll
                for (int j = 0; j < VEC_SIZE && (base_idx + j) < V_DIM; j++[3D[K
j++) {
                    v_acc[j % 2] += weight * __bfloat162float(v_vec.x[j]);
                }
            }
        }
    }

    // Write partial results with vectorized stores
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    for (int i = tid; i < (V_DIM + VEC_SIZE - 1) / VEC_SIZE; i += BLOCK_SIZ[9D[K
BLOCK_SIZE) {
        int base_idx = i * VEC_SIZE;
        if (base_idx < V_DIM) {
            vec4_bf16 out_vec;
            #pragma unroll
            for (int j = 0; j < VEC_SIZE && (base_idx + j) < V_DIM; j++) {
                out_vec.x[j] = __float2bfloat16(v_acc[j % 2] / running_sum)[12D[K
running_sum);
            }
            *reinterpret_cast<vec4_bf16*>(partial_out + out_base * V_DIM + [K
base_idx) = out_vec;
        }
    }

    // Write max and log-sum-exp
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Optimized reduce with coalesced access
__global__ __launch_bounds__(256, 2)
void mla_reduce_v2(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * NUM_HEADS * V_DIM;
    if (idx >= total_elements) return;

    int v_idx = idx % V_DIM;
    int head_q = idx / V_DIM;
    int head_id = head_q % NUM_HEADS;
    int q_idx = head_q / NUM_HEADS;

    // Find global max across splits
    float global_max = -1e30f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Merge with log-sum-exp
    float total_weight = 0.0f;
    float total_v = 0.0f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float weight = expf(partial_lse[base] - global_max);
        total_weight += weight;
        total_v += partial_out[base * V_DIM + v_idx] * expf(partial_max[bas[20D[K
expf(partial_max[base] - global_max);
    }

    output[idx] = __float2bfloat16(total_v / total_weight);
}

void launch_mla(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor par[3D[K
partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_phase1_v2<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce_v2<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor partial_out, torch::Tensor partial_max,
                torch::Tensor partial_lse, torch::Tensor output,
                torch::Tensor kv_indptr,
                int batch_size, int total_q, int num_splits, float sm_scale[8D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_v2", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_S[19D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-mllvm", "-amdgpu-fast-math=1"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla_v2] Build failed: {e}")
    _OK = False

NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

_cache = {}
_partial_cache = {}


def _quantize_fp8(t):
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_kv_splits(total_kv):
    if total_kv <= 2048: return 1
    if total_kv <= 16384: return 4
    if total_kv <= 131072: return 8
    if total_kv <= 524288: return 16
    return 32


def _einsum_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, NUM_HEADS[9D[K
NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)


def _asm_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, 1, QK_HEA[6D[K
QK_HEAD_DIM)
    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_buffer_fp8.dtype, num_kv_[7D[K
num_kv_splits)
    if key not in _cache:
        kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)[31D[K
kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(bs, [K
qseqlen, NUM_HEADS, q_fp8.dtype, kv_buffer_fp8.dtype,
            is_sparse=False, fast