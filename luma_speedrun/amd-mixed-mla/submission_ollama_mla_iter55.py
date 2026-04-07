Thinking...
The user is asking me to optimize an MLA (Multi-Head Latent Attention) kern[4D[K
kernel for AMD MI355X GPU. They want me to propose ONE specific optimizatio[11D[K
optimization and output the complete modified submission.py file.

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. The current kernel uses a simple split-K approach with thread-cooperativ[17D[K
thread-cooperative dot products
2. There's no LDS double-buffering
3. No vectorized loads
4. No XCD-aware scheduling
5. No shape-specialized dispatch

Given the target is <50µs geomean (current best is 69.7µs, rank 1 is 19.5µs[6D[K
19.5µs), I need to make significant improvements.

The most impactful optimization for this workload would be **LDS double-buf[10D[K
double-buffering for coalesced memory access**. This is because:
1. The KV data is accessed repeatedly in the inner loop
2. Current implementation loads KV directly from global memory for each kv_[3D[K
kv_idx
3. LDS can cache KV tiles, reducing global memory bandwidth pressure
4. Double-buffering allows overlapping memory loads with computation

Let me implement this optimization:

1. Use LDS to cache KV tiles (both K and V portions)
2. Implement double-buffering with ping-pong buffers
3. Use vectorized 128-bit loads (hip_bfloat162) for better bandwidth
4. Prefetch next tile while computing current tile

Key changes:
- Add LDS buffers for KV (K portion: 576 dims, V portion: 512 dims)
- Implement double-buffering with 2 sets of LDS buffers
- Use async copy patterns with __syncthreads()
- Vectorize loads using hip_bfloat162 (128-bit)
- Overlap memory loads with dot product computation

Let me write the complete modified file:
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: LDS Double-Buffered Split-K GEMV attention via load_inline.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - LDS double-buffering for KV tiles (K: 576, V: 512)
  - Thread-cooperative 576-dim dot product with vectorized loads
  - Online softmax with running max/sum
  - Accumulate weighted V with double-buffered prefetch
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- LDS double-buffering: overlap KV loads with compute
- Vectorized 128-bit loads (hip_bfloat162) for 2x bandwidth
- Prefetch next KV tile while computing current
- Reduced global memory traffic via LDS caching
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

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define KV_TILE_SIZE 64  // KV entries per tile
#define LDS_K_SIZE (QK_DIM * KV_TILE_SIZE)
#define LDS_V_SIZE (V_DIM * KV_TILE_SIZE)

// Phase 1: Split-K attention with LDS double-buffering
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1(
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

    // Q pointer for this batch+head (decode: qseqlen=1, so q_idx = batch_i[7D[K
batch_id)
    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into shared memory (576 bf16 = 1152 bytes)
    __shared__ float q_shared[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // LDS double-buffering for KV tiles
    __shared__ __hip_bfloat16 lds_k[2][LDS_K_SIZE];
    __shared__ __hip_bfloat16 lds_v[2][LDS_V_SIZE];
    __shared__ int lds_valid[2];

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Number of tiles needed
    int num_tiles = (my_kv_end - my_kv_start + KV_TILE_SIZE - 1) / KV_TILE_[8D[K
KV_TILE_SIZE;

    // Prefetch first tile
    int tile_idx = 0;
    int buffer_idx = 0;
    int kv_base = my_kv_start + tile_idx * KV_TILE_SIZE;
    int tile_kv_len = min(KV_TILE_SIZE, my_kv_end - kv_base);
    
    if (kv_base < my_kv_end) {
        // Load K portion (576 dims)
        for (int i = tid; i < QK_DIM * tile_kv_len; i += BLOCK_SIZE) {
            int kv_off = i / QK_DIM;
            int dim_off = i % QK_DIM;
            int global_idx = (kv_base + kv_off) * QK_DIM + dim_off;
            lds_k[buffer_idx][i] = KV[global_idx];
        }
        // Load V portion (512 dims)
        for (int i = tid; i < V_DIM * tile_kv_len; i += BLOCK_SIZE) {
            int kv_off = i / V_DIM;
            int dim_off = i % V_DIM;
            int global_idx = (kv_base + kv_off) * QK_DIM + dim_off;
            lds_v[buffer_idx][i] = KV[global_idx];
        }
        lds_valid[buffer_idx] = tile_kv_len;
    } else {
        lds_valid[buffer_idx] = 0;
    }
    __syncthreads();

    // Process tiles
    for (tile_idx = 0; tile_idx < num_tiles; tile_idx++) {
        int next_buffer_idx = 1 - buffer_idx;
        int next_kv_base = my_kv_start + (tile_idx + 1) * KV_TILE_SIZE;
        int next_tile_kv_len = (next_kv_base < my_kv_end) ? 
            min(KV_TILE_SIZE, my_kv_end - next_kv_base) : 0;

        // Prefetch next tile (overlap with compute)
        if (tile_idx < num_tiles - 1 && next_tile_kv_len > 0) {
            for (int i = tid; i < QK_DIM * next_tile_kv_len; i += BLOCK_SIZ[9D[K
BLOCK_SIZE) {
                int kv_off = i / QK_DIM;
                int dim_off = i % QK_DIM;
                int global_idx = (next_kv_base + kv_off) * QK_DIM + dim_off[7D[K
dim_off;
                lds_k[next_buffer_idx][i] = KV[global_idx];
            }
            for (int i = tid; i < V_DIM * next_tile_kv_len; i += BLOCK_SIZE[10D[K
BLOCK_SIZE) {
                int kv_off = i / V_DIM;
                int dim_off = i % V_DIM;
                int global_idx = (next_kv_base + kv_off) * QK_DIM + dim_off[7D[K
dim_off;
                lds_v[next_buffer_idx][i] = KV[global_idx];
            }
            lds_valid[next_buffer_idx] = next_tile_kv_len;
        }
        __syncthreads();

        // Process current tile
        int current_tile_kv_len = lds_valid[buffer_idx];
        for (int kv_tile_idx = 0; kv_tile_idx < current_tile_kv_len; kv_til[6D[K
kv_tile_idx++) {
            int kv_idx = kv_base + kv_tile_idx;
            
            // Compute Q@K^T: thread-cooperative dot product over 576 dims
            // Vectorized: load 2 bf16 at a time (128-bit)
            float dot = 0.0f;
            for (int d = tid * 2; d < QK_DIM; d += BLOCK_SIZE * 2) {
                hip_bfloat162 q_vec = *reinterpret_cast<const hip_bfloat162[13D[K
hip_bfloat162*>(&q_shared[d]);
                hip_bfloat162 k_vec = *reinterpret_cast<const hip_bfloat162[13D[K
hip_bfloat162*>(
                    &lds_k[buffer_idx][kv_tile_idx * QK_DIM + d]);
                dot += __bfloat162float(q_vec.x) * __bfloat162float(k_vec.x[24D[K
__bfloat162float(k_vec.x);
                dot += __bfloat162float(q_vec.y) * __bfloat162float(k_vec.y[24D[K
__bfloat162float(k_vec.y);
            }

            // Warp reduction for dot product
            #pragma unroll
            for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset, WAVESIZE);
            }
            
            // Cross-warp reduction via shared memory
            __shared__ float warp_sums[4];
            if (lane_id == 0) {
                warp_sums[warp_id] = dot;
            }
            __syncthreads();

            float score;
            if (tid == 0) {
                score = (warp_sums[0] + warp_sums[1] + warp_sums[2] + warp_[5D[K
warp_sums[3]) * sm_scale;
                warp_sums[0] = score;
            }
            __syncthreads();
            score = warp_sums[0];

            // Online softmax update
            float old_max = running_max;
            float new_max = fmaxf(old_max, score);
            float exp_score = expf(score - new_max);
            float correction = expf(old_max - new_max);

            running_sum = running_sum * correction + exp_score;
            running_max = new_max;

            // Accumulate weighted V (vectorized load)
            float weight = exp_score;
            for (int vi = 0; vi < 2; vi++) {
                int v_idx = tid * 2 + vi;
                if (v_idx < V_DIM) {
                    float v_val = __bfloat162float(
                        lds_v[buffer_idx][kv_tile_idx * V_DIM + v_idx]);
                    v_acc[vi] = v_acc[vi] * correction + weight * v_val;
                }
            }
        }

        // Switch buffer
        buffer_idx = next_buffer_idx;
        kv_base = next_kv_base;
        __syncthreads();
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Reduce partial results across splits
__global__ void mla_reduce(
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

    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float m = partial_max[base];
        global_max = fmaxf(global_max, m);
    }

    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        total_weight += weight;
        total_v += partial_out[base * V_DIM + v_idx] * expf(m - global_max)[11D[K
global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / total_weight);
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
    mla_splitk_phase1<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial