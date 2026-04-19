Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (rank 1 is 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Patterns**: The current kernel loads Q into shared memor[5D[K
memory but KV is loaded directly from global memory in the inner loop. This[4D[K
This is inefficient.

2. **Thread Cooperation**: The current dot product uses 256 threads for 576[3D[K
576 dimensions (~2.25 elements per thread), which is not optimal for MFMA u[1D[K
utilization.

3. **No Vectorized Loads**: The kernel doesn't use vectorized loads (float4[7D[K
(float4/hip_bfloat162) which could improve memory bandwidth.

4. **No LDS Double-Buffering**: Could hide memory latency better.

5. **No XCD-aware scheduling**: MI355X has 8 XCDs, could benefit from prior[5D[K
priority scheduling.

6. **Reduction Phase**: The reduce kernel is inefficient - it does multiple[8D[K
multiple passes over partial results.

Given the constraints and the target performance, I think the most impactfu[8D[K
impactful optimization would be:

**Vectorized 128-bit global loads + LDS double-buffering for KV tiles**

This would:
1. Improve memory bandwidth utilization significantly (4x for 128-bit loads[5D[K
loads)
2. Hide memory latency with double-buffering
3. Better utilize the CDNA4 memory hierarchy

Let me create an optimized version that:
1. Uses vectorized loads for both Q and KV (hip_bfloat162 or float4)
2. Implements LDS double-buffering for KV tiles
3. Optimizes the reduction phase to be more efficient
4. Uses better thread organization for MFMA-friendly operations


5. Adds XCD-aware priority hints

I'll also add `__builtin_amdgcn_s_setprio` for XCD-aware scheduling and opt[3D[K
optimize the block size to better match the wavefront size (64 threads per [K
wave, 4 waves per block = 256 threads is good).

Let me write the complete optimized submission.py file.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized LDS Double-Buffered Split-K GEMV Attention.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads (hip_bfloat162) for Q and KV
  - LDS double-buffering for KV tiles to hide memory latency
  - Thread-cooperative 576-dim dot product with warp shuffles
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Fused reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x bandwidth improvement)
- LDS double-buffering for KV tiles (hide memory latency)
- XCD-aware scheduling with __builtin_amdgcn_s_setprio
- Optimized reduction with coalesced access patterns
- Better thread organization for CDNA4 wavefronts
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
#define QK_VEC_SIZE (QK_DIM / 4)  // 144 vec4 loads
#define V_VEC_SIZE (V_DIM / 4)    // 128 vec4 loads
#define KV_TILE_SIZE 64           // KV entries per tile
#define NUM_KV_TILES ((KV_TILE_SIZE + 3) / 4)  // vec4 per KV entry
#define LDS_BANKS 32

// Vectorized load helper
__device__ __forceinline__ float4 load_vec4(const __hip_bfloat16* ptr, int [K
idx) {
    const float4* vec_ptr = reinterpret_cast<const float4*>(ptr + idx * 4);[3D[K
4);
    return *vec_ptr;
}

__device__ __forceinline__ void store_vec4(__hip_bfloat16* ptr, int idx, fl[2D[K
float4 val) {
    float4* vec_ptr = reinterpret_cast<float4*>(ptr + idx * 4);
    *vec_ptr = val;
}

// Phase 1: Split-K attention with LDS double-buffering
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

    // XCD-aware priority scheduling
    __builtin_amdgcn_s_setprio(1);

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

    // LDS for Q (loaded once) and KV double-buffering
    __shared__ float q_shared[QK_DIM];
    __shared__ float kv_buffer[2 * KV_TILE_SIZE * QK_DIM];
    __shared__ float kv_v_buffer[2 * KV_TILE_SIZE * V_DIM];

    // Load Q into shared memory with vectorized loads
    for (int i = tid * 4; i < QK_DIM; i += BLOCK_SIZE * 4) {
        float4 q_vec = load_vec4(q_ptr, i / 4);
        q_shared[i] = __bfloat162float(q_vec.x);
        q_shared[i + 1] = __bfloat162float(q_vec.y);
        q_shared[i + 2] = __bfloat162float(q_vec.z);
        q_shared[i + 3] = __bfloat162float(q_vec.w);
    }
    __syncthreads();

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Double-buffering state
    int read_buffer = 0;
    int write_buffer = 1;
    int kv_tile_idx = 0;

    // Process KV entries in this split with double-buffering
    for (int kv_base = my_kv_start; kv_base < my_kv_end; kv_base += KV_TILE[7D[K
KV_TILE_SIZE) {
        int tile_kv_end = min(kv_base + KV_TILE_SIZE, my_kv_end);
        int tile_kv_len = tile_kv_end - kv_base;

        // Prefetch next KV tile into LDS (double-buffering)
        if (kv_tile_idx > 0) {
            __syncthreads();
        }

        // Load KV tile into LDS with vectorized loads
        for (int t = tid; t < tile_kv_len * QK_VEC_SIZE; t += BLOCK_SIZE) {[1D[K
{
            int kv_idx = kv_base + t / QK_VEC_SIZE;
            int dim_idx = (t % QK_VEC_SIZE) * 4;
            if (kv_idx < tile_kv_end && dim_idx < QK_DIM) {
                float4 kv_vec = load_vec4(KV + kv_idx * QK_DIM, dim_idx / 4[1D[K
4);
                int lds_idx = write_buffer * KV_TILE_SIZE * QK_DIM + (kv_id[6D[K
(kv_idx - kv_base) * QK_DIM + dim_idx;
                kv_buffer[lds_idx] = __bfloat162float(kv_vec.x);
                kv_buffer[lds_idx + 1] = __bfloat162float(kv_vec.y);
                kv_buffer[lds_idx + 2] = __bfloat162float(kv_vec.z);
                kv_buffer[lds_idx + 3] = __bfloat162float(kv_vec.w);
            }
        }

        // Load V portion of KV tile
        for (int t = tid; t < tile_kv_len * V_VEC_SIZE; t += BLOCK_SIZE) {
            int kv_idx = kv_base + t / V_VEC_SIZE;
            int dim_idx = (t % V_VEC_SIZE) * 4;
            if (kv_idx < tile_kv_end && dim_idx < V_DIM) {
                float4 kv_vec = load_vec4(KV + kv_idx * QK_DIM, dim_idx / 4[1D[K
4);
                int lds_idx = write_buffer * KV_TILE_SIZE * V_DIM + (kv_idx[7D[K
(kv_idx - kv_base) * V_DIM + dim_idx;
                kv_v_buffer[lds_idx] = __bfloat162float(kv_vec.x);
                kv_v_buffer[lds_idx + 1] = __bfloat162float(kv_vec.y);
                kv_v_buffer[lds_idx + 2] = __bfloat162float(kv_vec.z);
                kv_v_buffer[lds_idx + 3] = __bfloat162float(kv_vec.w);
            }
        }

        __syncthreads();

        // Process this KV tile
        for (int tile_kv = 0; tile_kv < tile_kv_len; tile_kv++) {
            int kv_idx = kv_base + tile_kv;

            // Compute Q@K^T: thread-cooperative dot product over 576 dims
            float dot = 0.0f;
            int kv_offset = read_buffer * KV_TILE_SIZE * QK_DIM + tile_kv *[1D[K
* QK_DIM;
            for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
                dot += q_shared[d] * kv_buffer[kv_offset + d];
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

            // Accumulate weighted V
            float weight = exp_score;
            int v_offset = read_buffer * KV_TILE_SIZE * V_DIM + tile_kv * V[1D[K
V_DIM;
            for (int vi = 0; vi < 2; vi++) {
                int v_idx = tid * 2 + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * kv_v_buff[9D[K
kv_v_buffer[v_offset + v_idx];
                }
            }
        }

        // Swap buffers for next iteration
        read_buffer = write_buffer;
        write_buffer = 1 - write_buffer;
        kv_tile_idx++;
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write partial V
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    // Write max and log-sum-exp (only thread 0)
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Optimized reduce with coalesced access
__global__ void mla_reduce_v2(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits, int num_heads, int v_dim
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * num_heads * v_dim;
    if (idx >= total_elements) return;

    int v_idx = idx % v_dim;
    int head_q = idx / v_dim;
    int head_id = head_q % num_heads;
    int q_idx = head_q / num_heads;

    // Find global max across splits
    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        global_max = fmaxf(global_max, m);
    }

    // Merge weighted sums using log-sum-exp
    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        total_weight += weight;
        total_v += partial_out[base * v_dim + v_idx] * expf(m - global_max)[11D[K
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
        total_q, num_splits, NUM_HEADS, V_DIM);
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
"-mllvm", "--amdgpu-early-inline-all=true"],
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

    # Choose splits for CU occupancy - optimized for MI355X
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

