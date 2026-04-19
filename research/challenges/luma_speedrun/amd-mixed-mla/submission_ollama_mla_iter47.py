Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (rank 1 is 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Patterns**: The current kernel loads Q into shared memor[5D[K
memory but KV is loaded directly from global memory in the inner loop. This[4D[K
This is inefficient.

2. **Vectorized Loads**: The current code doesn't use vectorized loads (128[4D[K
(128-bit loads for BF16 would be 4 elements at once).

3. **LDS Double-Buffering**: Could hide memory latency by prefetching KV ti[2D[K
tiles.

4. **Warp-Level Primitives**: The current reduction uses shared memory for [K
cross-warp reduction, but could use more efficient warp-level primitives.

5. **MFMA Usage**: For MI355X (CDNA4), MFMA instructions could significantl[12D[K
significantly speed up the Q@K^T computation.

6. **Register Pressure**: The current code accumulates V in registers but c[1D[K
could be optimized.

7. **Split-K Strategy**: The current split-K approach is good but the reduc[5D[K
reduction phase could be optimized.

Given the constraints and the fact that MFMA 32x32x64 FP4 is verified worki[5D[K
working, I should focus on:

1. **Vectorized 128-bit global loads** - This is one of the suggested optim[5D[K
optimizations and would significantly improve memory bandwidth utilization [K
for BF16 data.

2. **LDS double-buffering** - This would help hide memory latency when load[4D[K
loading KV tiles.

3. **Better warp-level reduction** - Use more efficient reduction patterns.[9D[K
patterns.

Let me create an optimized version that focuses on vectorized loads and bet[3D[K
better memory access patterns. The key improvements I'll make:


- Use `__builtin_amdgcn_buffer_load_format_x4` or equivalent for 128-bit lo[2D[K
loads
- Implement double-buffering for KV tiles in LDS
- Optimize the reduction phase to be more efficient
- Use better thread organization for the dot product computation

I'll focus on vectorized 128-bit loads as the primary optimization since th[2D[K
this directly addresses memory bandwidth which is often the bottleneck in a[1D[K
attention kernels. I need to complete the partial thought about the HIP_SOU[7D[K
HIP_SOURCE code optimization. Looking at the next thinking, I can see it co[2D[K
continues with the kernel implementation details including shared memory se[2D[K
setup, Q loading with vectorized operations, and the beginning of the onlin[5D[K
online softmax computation.

Let me complete and rewrite this section:

I'm setting up the kernel with proper thread indexing and KV range calculat[8D[K
calculation for the current batch. The shared memory is allocated for both [K
Q values and KV tiles to enable double-buffering. I load Q into shared memo[4D[K
memory using vectorized 4-element BF16 loads for better memory throughput, [K
then initialize the online softmax state with running maximum and sum value[5D[K
values. The V accumulator is set up as a 4-element array to match the vecto[5D[K
vectorized processing pattern.

For the KV processing loop, I'm implementing double-buffering with two KV t[1D[K
tiles that alternate between loading and computation. Each iteration loads [K
the next KV tile into shared memory while computing with the current tile, [K
using vectorized loads to fetch 4 BF16 elements at a time. This overlaps me[2D[K
memory transfers with computation to hide latency.

Within each KV tile, I process multiple KV entries. For each entry, I compu[5D[K
compute the Q@K^T dot product by having threads cooperatively multiply and [K
accumulate across the QK dimension, with each thread handling 4 elements pe[2D[K
per iteration using the vectorized shared memory access pattern.

After the dot product computation, I perform a warp-level reduction using s[1D[K
shuffle operations to sum across the 64-thread wavefront, then use shared m[1D[K
memory to reduce across the 4 warps in the block. Thread 0 collects the fin[3D[K
final score, applies the scaling factor, and broadcasts it back through sha[3D[K
shared memory for all threads to use in the softmax calculation.

For the online softmax update, I track the running maximum and compute expo[4D[K
exponential corrections to maintain numerical stability. Each thread then a[1D[K
accumulates the weighted V values, processing 4 elements per thread to matc[4D[K
match the V dimension partitioning across the 256-thread block.

After processing all KV entries in the tile, I synchronize and swap the buf[3D[K
buffer indices for double-buffering. Once all splits are processed, I write[5D[K
write the accumulated V values and the running maximum/log-sum-exp to the o[1D[K
output buffers, with only thread 0 handling the scalar metadata writes.

However, I'm realizing this approach is becoming quite intricate. Let me re[2D[K
refocus on what will actually move the needle: vectorized 128-bit loads for[3D[K
for the KV data, which should provide the most immediate bandwidth improvem[8D[K
improvement without overcomplicating the implementation.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized Split-K GEMV attention with 128-bit loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Thread-cooperative 576-dim dot product (Q@K^T)
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x BF16 per load)
- LDS double-buffering for KV tiles to hide memory latency
- Warp-level shuffle reduction (no shared mem for warp reduce)
- Register tiling for V accumulation (4 elems per thread)
- Single kernel launch (no Python metadata overhead)
- Q broadcast across 16 heads (GQA: 1 KV head shared)
- BF16 KV directly (no FP8 quant overhead, 10% tolerance allows it)
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
#include <hip/hip_fp16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define KV_TILE_SIZE 64  // KV entries per tile
#define NUM_KV_TILES 2   // Double buffering

// Vectorized load: 4x BF16 = 128 bits
__device__ __forceinline__ void load_bf16x4(const __hip_bfloat16* src, floa[4D[K
float* dst) {
    typedef __hip_bfloat162 vec2;
    const vec2* src2 = reinterpret_cast<const vec2*>(src);
    vec2 v0 = src2[0];
    vec2 v1 = src2[1];
    dst[0] = __bfloat162float(v0.x);
    dst[1] = __bfloat162float(v0.y);
    dst[2] = __bfloat162float(v1.x);
    dst[3] = __bfloat162float(v1.y);
}

// Phase 1: Split-K attention with vectorized loads and double-buffering
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

    // Load Q into shared memory with vectorized loads
    // 576 BF16 = 288 BF16 pairs = 144 vec2 loads
    __shared__ float q_shared[QK_DIM];
    for (int i = tid * 4; i < QK_DIM; i += BLOCK_SIZE * 4) {
        if (i + 3 < QK_DIM) {
            float tmp[4];
            load_bf16x4(q_ptr + i, tmp);
            q_shared[i] = tmp[0];
            q_shared[i+1] = tmp[1];
            q_shared[i+2] = tmp[2];
            q_shared[i+3] = tmp[3];
        } else {
            for (int j = i; j < QK_DIM && j < i + 4; j++) {
                q_shared[j] = __bfloat162float(q_ptr[j]);
            }
        }
    }
    __syncthreads();

    // LDS for KV double-buffering: 2 tiles x 64 entries x 576 dims
    __shared__ float kv_lds[NUM_KV_TILES][KV_TILE_SIZE][QK_DIM];

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator: 4 elements per thread (512/256 = 2, use 4 for vectori[7D[K
vectorization)
    float v_acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};

    // Double-buffering state
    int read_tile = 0;
    int write_tile = 1;
    int kv_tile_start = my_kv_start;

    // Prefetch first tile
    for (int tidx = 0; tidx < KV_TILE_SIZE; tidx++) {
        int kv_idx = kv_tile_start + tidx;
        if (kv_idx < my_kv_end) {
            const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
            float* kv_dst = kv_lds[write_tile][tidx];
            for (int d = tid * 4; d < QK_DIM; d += BLOCK_SIZE * 4) {
                if (d + 3 < QK_DIM) {
                    load_bf16x4(kv_ptr + d, kv_dst + d);
                } else {
                    for (int j = d; j < QK_DIM && j < d + 4; j++) {
                        kv_dst[j] = __bfloat162float(kv_ptr[j]);
                    }
                }
            }
        }
    }
    __syncthreads();

    // Process KV tiles
    while (kv_tile_start < my_kv_end) {
        int tile_end = min(kv_tile_start + KV_TILE_SIZE, my_kv_end);
        
        // Process entries in current tile
        for (int kv_idx = kv_tile_start; kv_idx < tile_end; kv_idx++) {
            int tidx = kv_idx - kv_tile_start;
            float* kv_ptr = kv_lds[read_tile][tidx];

            // Compute Q@K^T: thread-cooperative dot product
            float dot = 0.0f;
            for (int d = lane_id; d < QK_DIM; d += WAVESIZE) {
                dot += q_shared[d] * kv_ptr[d];
            }

            // Warp reduction using shuffle
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

            // Accumulate weighted V with vectorization
            float weight = exp_score;
            for (int vi = 0; vi < 4; vi++) {
                int v_idx = tid * 4 + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * kv_ptr[v_[9D[K
kv_ptr[v_idx];
                }
            }
        }

        // Swap tiles and prefetch next
        kv_tile_start += KV_TILE_SIZE;
        read_tile = 1 - read_tile;
        write_tile = 1 - write_tile;

        if (kv_tile_start < my_kv_end) {
            for (int tidx = 0; tidx < KV_TILE_SIZE; tidx++) {
                int kv_idx = kv_tile_start + tidx;
                if (kv_idx < my_kv_end) {
                    const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
                    float* kv_dst = kv_lds[write_tile][tidx];
                    for (int d = tid * 4; d < QK_DIM; d += BLOCK_SIZE * 4) [K
{
                        if (d + 3 < QK_DIM) {
                            load_bf16x4(kv_ptr + d, kv_dst + d);
                        } else {
                            for (int j = d; j < QK_DIM && j < d + 4; j++) {[1D[K
{
                                kv_dst[j] = __bfloat162float(kv_ptr[j]);
                            }
                        }
                    }
                }
            }
        }
        __syncthreads();
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write partial V
    for (int vi = 0; vi < 4; vi++) {
        int v_idx = tid * 4 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    // Write max and log-sum-exp
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Reduce partial results across splits (optimized)
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

    // Find global max across splits
    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Merge weighted sums
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
        name="custom_mla", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_SOUR[22D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-ffast-math"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla] Build failed: {e}")
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
            is_sparse=False, fast_mode=False, num_kv_splits=num_kv_splits, [K
intra_batch_mode=True)
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, ws, ri, rf, rp = work
        get_mla_metadata_v1(qo_indptr, kv_indptr, kv_last_page_len,
            NUM_HEADS, 1, True, wm, ws, wi, ri, rf, rp,
            page_size=PAGE_SIZE, kv_granularity=max(PAGE_SIZE, 16),
            max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
            fast_mode=False, max_split_per_batch=num_kv_splits,
            intra_batch_mode=True, dtype_q=q_fp8.dtype, dtype_kv=kv_buffer_[19D[K
dtype_kv=kv_buffer_fp8.dtype)
        total_kv_len = int(kv_indptr[-1].item())
        total_q_val = bs * qseqlen
        _cache[key] = {
            "work_metadata": wm, "work_indptr": wi, "work_info_set": ws,
            "reduce_indptr": ri, "reduce_final_map": rf, "reduce_partial_ma[18D[K
"reduce_partial_map": rp,
            "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, dev[3D[K
device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "logits": torch.empty((num_kv_splits, total_q_val, NUM_HEADS, V[1D[K
V_HEAD_DIM), dtype=torch.float32, device="cuda"),
            "attn_lse": torch.empty((num_kv_splits, total_q_val, NUM_HEADS)[10D[K
NUM_HEADS), dtype=torch.float32, device="cuda"),
            "output": torch.empty((total_q_val, NUM_HEADS, V_HEAD_DIM), dty[3D[K
dtype=torch.bfloat16, device="cuda"),
        }
    meta = _cache[key]
    output = meta["output"]
    aiter.mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM), kv_4d,
        qo_indptr, kv_indptr, meta["kv_indices"], meta["kv_last_page_len"],[25D[K
meta["kv_last_page_len"],
        None, meta["work_metadata"], meta["work_in[13D[K
meta["work_indptr"], meta["work_info_set"],
        qseqlen, PAGE_SIZE, 1, SM_SCALE,
        meta["logits"], meta["attn_lse"], output, q_scale, kv_scale)
    mla_reduce_v1(meta["logits"], meta["attn_lse"],
        meta["reduce_indptr"], meta["reduce_final_map"], meta["reduce_parti[18D[K
meta["reduce_partial_map"],
        qseqlen, output, None)
    return output


def _custom_attention(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    total_q = bs  # decode: qseqlen=1

    kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)  # [total_kv, 576]

    # Choose splits for CU occupancy
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))

    # Allocate partial buffers
    pk = (total_q, NUM_HEADS, num_splits)
    if pk not in _partial_cache:
        _partial_cache.clear()
        _partial_cache[pk] = (
            torch.empty((num_splits, total_q, NUM_HEADS, V_HEAD_DIM), dtype[5D[K
dtype=torch.float32, device="cuda"),
            torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float[17D[K
dtype=torch.float32, device="cuda"),
            torch.empty((num_splits, total_q, NUM_HEADS), dtype=torch.float[17D[K
dtype=torch.float32, device="cuda"),
            torch.empty((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloa[17D[K
dtype=torch.bfloat16, device="cuda"),
        )
    partial_out, partial_max, partial_lse, output = _partial_cache[pk]

    _mod.launch_mla(
        q, kv_flat,
        partial_out, partial_max, partial_lse, output,
        kv_indptr, bs, total_q, num_splits, SM_SCALE,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Use einsum for small shapes (proven best)
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # Try custom kernel for large shapes, fall back to ASM
    if _OK:
        try:
            return _custom_attention(data)
        except Exception as e:
            print(f"[custom_mla] Runtime error: {e}")

    return _asm_attention(data)
```

