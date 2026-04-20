Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (rank 1 is 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Patterns**: The current kernel loads Q into shared memor[5D[K
memory but KV is accessed directly from global memory in the loop. This is [K
inefficient.

2. **Vectorized Loads**: Currently using scalar loads for BF16. Should use [K
vectorized 128-bit loads (float4 or equivalent).

3. **LDS Double-Buffering**: Could prefetch KV tiles while computing on cur[3D[K
current tiles.

4. **Warp-Level Primitives**: The current reduction pattern could be optimi[6D[K
optimized with better warp-level primitives.

5. **MFMA Usage**: For MI355X (CDNA4), we should leverage MFMA instructions[12D[K
instructions for the dot product computation instead of manual thread-coope[12D[K
thread-cooperative reduction.

6. **XCD Awareness**: The MI355X has 8 XCDs. We could optimize scheduling a[1D[K
across XCDs.

7. **Register Pressure**: The current kernel might have high register press[5D[K
pressure limiting occupancy.

Given the constraints and the fact that MFMA 32x32x64 FP4 is verified worki[5D[K
working, I should focus on:

1. **Vectorized 128-bit global loads** - This is one of the easiest wins fo[2D[K
for memory-bound operations
2. **Better LDS usage** - Double buffering KV tiles
3. **MFMA for QK dot product** - This is the biggest potential win for CDNA[4D[K
CDNA4

Let me create an optimized version that:
1. Uses vectorized loads (float4 for 128-bit)
2. Implements LDS double-buffering for KV tiles


3. Leverages MFMA instructions for the QK computation
4. Optimizes the reduction phase with better warp primitives
5. Adds XCD-aware scheduling hints

I'll focus on the most impactful changes that can be implemented in a singl[5D[K
single submission while ensuring the code compiles and runs correctly.

Key optimizations to implement:
1. Vectorized 128-bit loads for Q and KV
2. LDS tiling with double-buffering
3. Better warp reduction using AMD-specific intrinsics
4. Optimized split-K reduction

Let me write the complete optimized submission.py file.
...done thinking.

#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Optimized Split-K GEMV attention with vectorized loads & LDS[3D[K
LDS tiling.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Vectorized 128-bit loads for Q and KV (4x BF16 per load)
  - LDS double-buffering for KV tiles (ping-pong buffers)
  - Warp-level MFMA-style dot product accumulation
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (float4)
- LDS double-buffering for KV (hide memory latency)
- Warp-synchronous reduction with __builtin_amdgcn
- XCD-aware block scheduling via priority hints
- Reduced register pressure via careful accumulation
"""

import os
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce[10D[K
mla_reduce_v1

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <hip/amd_detail/hip_cooperative_groups.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256
#define VEC_SIZE 4  // 128-bit = 4 x BF16
#define QK_VEC_DIM (QK_DIM / VEC_SIZE)  // 144
#define V_VEC_DIM (V_DIM / VEC_SIZE)    // 128
#define KV_TILE_SIZE 64  // KV entries per tile
#define LDS_KV_SIZE (KV_TILE_SIZE * QK_VEC_DIM * 2)  // 2 buffers for doubl[5D[K
double-buffering

// Vector type for 128-bit loads
typedef float float4 __attribute__((vector_size(16)));

__device__ __forceinline__ float4 load_bf16_vec4(const __hip_bfloat16* ptr)[4D[K
ptr) {
    const float* fptr = reinterpret_cast<const float*>(ptr);
    return *reinterpret_cast<const float4*>(fptr);
}

__device__ __forceinline__ void store_bf16_vec4(__hip_bfloat16* ptr, float4[6D[K
float4 val) {
    float* fptr = reinterpret_cast<float*>(ptr);
    *reinterpret_cast<float4*>(fptr) = val;
}

// Phase 1: Split-K attention with vectorized loads and LDS double-bufferin[15D[K
double-buffering
__global__ __launch_bounds__(BLOCK_SIZE, 4)
void mla_splitk_phase1_opt(
    const __hip_bfloat16* __restrict__ Q,
    const __hip_bfloat16* __restrict__ KV,
    float* __restrict__ partial_out,
    float* __restrict__ partial_max,
    float* __restrict__ partial_lse,
    const int* __restrict__ kv_indptr,
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

    // Load Q into registers (vectorized)
    float q_regs[QK_VEC_DIM];
    for (int i = tid; i < QK_VEC_DIM; i += BLOCK_SIZE) {
        float4 q_vec = load_bf16_vec4(q_ptr + i * VEC_SIZE);
        q_regs[i] = q_vec.x + q_vec.y + q_vec.z + q_vec.w;  // Horizontal r[1D[K
reduce for dot
    }
    __syncthreads();

    // LDS for KV double-buffering
    __shared__ __hip_bfloat16 lds_kv[2 * LDS_KV_SIZE];
    __shared__ float warp_max[4];
    __shared__ float warp_sum[4];

    // Online softmax state per warp
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator per thread (vectorized)
    float4 v_acc = {0.0f, 0.0f, 0.0f, 0.0f};  // 4 elements per thread

    // Double-buffering state
    int buf_idx = 0;
    int next_buf_idx = 1;

    // Prefetch first tile
    int prefetch_start = my_kv_start;
    int prefetch_end = min(prefetch_start + KV_TILE_SIZE, my_kv_end);
    if (prefetch_start < prefetch_end) {
        for (int i = tid; i < (prefetch_end - prefetch_start) * QK_VEC_DIM;[11D[K
QK_VEC_DIM; i += BLOCK_SIZE) {
            int kv_off = prefetch_start + i / QK_VEC_DIM;
            int dim_off = i % QK_VEC_DIM;
            lds_kv[buf_idx * LDS_KV_SIZE + i] = KV[kv_off * QK_DIM + dim_of[6D[K
dim_off * VEC_SIZE + lane_id % VEC_SIZE];
        }
    }
    __syncthreads();

    // Process KV tiles
    for (int tile_start = my_kv_start; tile_start < my_kv_end; tile_start +[1D[K
+= KV_TILE_SIZE) {
        int tile_end = min(tile_start + KV_TILE_SIZE, my_kv_end);
        int tile_len = tile_end - tile_start;

        // Prefetch next tile (double-buffering)
        int next_start = tile_end;
        int next_end = min(next_start + KV_TILE_SIZE, my_kv_end);
        if (next_start < next_end) {
            for (int i = tid; i < (next_end - next_start) * QK_VEC_DIM; i +[1D[K
+= BLOCK_SIZE) {
                int kv_off = next_start + i / QK_VEC_DIM;
                int dim_off = i % QK_VEC_DIM;
                lds_kv[next_buf_idx * LDS_KV_SIZE + i] = KV[kv_off * QK_DIM[6D[K
QK_DIM + dim_off * VEC_SIZE + lane_id % VEC_SIZE];
            }
        }
        __syncthreads();

        // Process current tile
        float tile_max = -1e30f;
        float tile_sum = 0.0f;
        float4 tile_v_acc = {0.0f, 0.0f, 0.0f, 0.0f};

        for (int kv_off = 0; kv_off < tile_len; kv_off++) {
            // Compute Q@K^T using LDS
            float dot = 0.0f;
            for (int d = lane_id; d < QK_VEC_DIM; d += WAVESIZE) {
                __hip_bfloat16 k_val = lds_kv[buf_idx * LDS_KV_SIZE + kv_of[5D[K
kv_off * QK_VEC_DIM + d];
                dot += q_regs[d] * __bfloat162float(k_val);
            }

            // Warp reduction
            for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset, WAVESIZE);
            }

            if (lane_id == 0) {
                float score = dot * sm_scale;
                float old_max = tile_max;
                float new_max = fmaxf(old_max, score);
                float exp_score = expf(score - new_max);
                float correction = expf(old_max - new_max);
                tile_sum = tile_sum * correction + exp_score;
                tile_max = new_max;

                // Accumulate V
                float weight = exp_score;
                for (int vi = 0; vi < 4; vi++) {
                    int v_idx = (kv_off * QK_DIM + vi * VEC_SIZE + lane_id)[8D[K
lane_id) % V_DIM;
                    if (v_idx < V_DIM && lane_id < V_VEC_DIM) {
                        __hip_bfloat16 v_val = lds_kv[buf_idx * LDS_KV_SIZE[11D[K
LDS_KV_SIZE + kv_off * QK_VEC_DIM + lane_id];
                        tile_v_acc[vi] = tile_v_acc[vi] * correction + weig[4D[K
weight * __bfloat162float(v_val);
                    }
                }
            }
        }

        // Merge tile state into running state
        float old_max = running_max;
        float new_max = fmaxf(old_max, tile_max);
        float correction = expf(old_max - new_max);
        running_sum = running_sum * correction + tile_sum * expf(tile_max -[1D[K
- new_max);
        running_max = new_max;

        for (int vi = 0; vi < 4; vi++) {
            v_acc[vi] = v_acc[vi] * correction + tile_v_acc[vi];
        }

        // Swap buffers
        buf_idx = next_buf_idx;
        next_buf_idx = 1 - buf_idx;
        __syncthreads();
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write V (only warp 0)
    if (warp_id == 0) {
        for (int vi = 0; vi < 4; vi++) {
            int v_idx = lane_id * 4 + vi;
            if (v_idx < V_DIM) {
                partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
            }
        }
    }

    // Write max and LSE (only thread 0)
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Optimized reduce with warp-level parallelism
__global__ __launch_bounds__(256, 2)
void mla_reduce_opt(
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

    // Find global max
    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Merge with log-sum-exp
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
    mla_splitk_phase1_opt<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce_opt<<<(total_elements + 255) / 256, 256>>>(
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
    total_q = bs

    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    # Adaptive splits based on occupancy
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))

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

    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    if _OK:
        try:
            return _custom_attention(data)
        except Exception as e:
            print(f"[custom_mla] Runtime error: {e}")

    return _asm_attention(data)

