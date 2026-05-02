Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) to achieve <50µs geomean latency. Current best is 69.7µs,[7D[K
69.7µs, rank 1 is 19.5µs.

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Pattern**: The current kernel loads Q into shared memory[6D[K
memory but KV is accessed directly from global memory in the inner loop. Th[2D[K
This is inefficient.

2. **Thread Cooperation**: The dot product computation uses thread cooperat[8D[K
cooperation but could be optimized with better warp-level primitives.

3. **Vectorized Loads**: Currently using scalar loads for KV data. Should u[1D[K
use vectorized 128-bit loads (float4 or equivalent for bf16).

4. **LDS Double Buffering**: Could prefetch KV tiles while computing curren[6D[K
current tile.

5. **XCD-aware Scheduling**: MI355X has 8 XCDs, should use priority hints f[1D[K
for better scheduling.

6. **MFMA Usage**: The MI355X supports MFMA (Matrix Fused Multiply Add) ins[3D[K
instructions which are much faster than scalar FMA for matrix operations.

7. **Reduce Phase Optimization**: The reduce phase is currently a separate [K
kernel with poor memory access patterns.

Key optimizations I should focus on:

1. **Vectorized 128-bit global loads** for KV data - this is one of the big[3D[K
biggest wins for memory-bound operations
2. **LDS double-buffering** to hide memory latency
3. **MFMA intrinsics** for the Q@K^T computation instead of scalar dot prod[4D[K
products
4. **Better warp-level reduction** using AMD-specific intrinsics
5. **Merge Phase 1 and Phase 2** if possible to reduce kernel launch overhe[6D[K
overhead

Given the constraints and the fact that MFMA 32x32x64 FP4 is verified worki[5D[K
working, I should leverage MFMA for the attention computation. However, sin[3D[K
since we're working with BF16, I should use MFMA for BF16 operations.


 
For MI355X (CDNA4), I need to use `__builtin_amdgcn_mfma_f32_32x32x16_bf16`[41D[K
`__builtin_amdgcn_mfma_f32_32x32x16_bf16` or similar. The most impactful ch[2D[K
change would be implementing vectorized loads combined with MFMA for the QK[2D[K
QK computation, along with LDS double-buffering to hide memory latency. I'l[3D[K
I'll restructure the kernel to load KV tiles into LDS with double-buffering[16D[K
double-buffering, use MFMA for the matrix multiply, and optimize the reduce[6D[K
reduce phase.

Looking at the decode scenario more carefully: Q has shape [batch_size, 1, [K
NUM_HEADS, 576] and KV has shape [total_kv, 1, 576] where total_kv = batch_[6D[K
batch_size * kv_seq_len. This is a decode attention pattern with Q sequence[8D[K
sequence length = 1.

The main bottleneck is the Q@K^T computation across all KV tokens. I should[6D[K
should focus on vectorized 128-bit loads for KV data, MFMA for the dot prod[4D[K
product computation, LDS double-buffering to hide memory latency, and bette[5D[K
better warp-level primitives for reduction.

Let me write an optimized version:

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: MFMA-accelerated Split-K GEMV attention with vectorized load[4D[K
loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - MFMA 32x32x16 BF16 for Q@K^T (batched GEMV)
  - Vectorized 128-bit global loads for KV (4x BF16 per load)
  - LDS double-buffering for KV tiles
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Reduce across splits using log-sum-exp merge (inlined)

Key optimizations:
- MFMA 32x32x16 BF16 intrinsics for 16x throughput vs scalar FMA
- Vectorized 128-bit loads (float4 equivalent for BF16)
- LDS double-buffering to hide global memory latency
- Warp-level primitives for reduction (__builtin_amdgcn_*)
- XCD-aware priority hints (__builtin_amdgcn_s_setprio)
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
#include <amdhip64.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define KV_TILE_SIZE 64  // KV tokens per tile
#define VECTORIZED_LOAD 4  // 4 BF16 per 128-bit load

// MFMA intrinsic for BF16 32x32x16
#define MFMA_BF16(a, b, c) __builtin_amdgcn_mfma_f32_32x32x16_bf16(a, b, c,[2D[K
c, 0, 0, 0)

// Priority hint for XCD scheduling
#define SET_HIGH_PRIORITY() __builtin_amdgcn_s_setprio(1)
#define SET_NORMAL_PRIORITY() __builtin_amdgcn_s_setprio(0)

// Phase 1: Split-K attention with MFMA and vectorized loads
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1_mfma(
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

    // Set high priority for better XCD scheduling
    SET_HIGH_PRIORITY();

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

    // Load Q into registers (576 BF16 = 288 float4 loads)
    // Each thread loads QK_DIM/BLOCK_SIZE elements
    __hip_bfloat16 q_reg[3];  // 576/256 ≈ 2.25, round to 3
    #pragma unroll
    for (int i = 0; i < 3; i++) {
        int d = tid * 3 + i;
        q_reg[i] = (d < QK_DIM) ? q_ptr[d] : __hip_bfloat16(0);
    }

    // LDS for KV double-buffering (2 tiles)
    __shared__ __hip_bfloat16 kv_lds[2 * KV_TILE_SIZE * QK_DIM];
    __shared__ float warp_sums[4 * 2];  // 4 warps, 2 buffers

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Double-buffering state
    int load_tile = 0;
    int compute_tile = 0;

    // Process KV entries in tiles
    for (int tile_start = my_kv_start; tile_start < my_kv_end; tile_start +[1D[K
+= KV_TILE_SIZE) {
        int tile_end = min(tile_start + KV_TILE_SIZE, my_kv_end);
        int tile_len = tile_end - tile_start;
        if (tile_len <= 0) continue;

        // Prefetch next KV tile into LDS (vectorized loads)
        #pragma unroll
        for (int kv_idx = tile_start; kv_idx < tile_end; kv_idx += 4) {
            int lds_idx = ((kv_idx - tile_start) % KV_TILE_SIZE) * QK_DIM;
            // Vectorized 128-bit load (4 BF16 = 8 bytes)
            if (kv_idx < my_kv_end) {
                const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
                #pragma unroll
                for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
                    kv_lds[load_tile * KV_TILE_SIZE * QK_DIM + lds_idx + d][2D[K
d] = kv_ptr[d];
                }
            }
        }
        __syncthreads();

        // Compute Q@K^T for this tile using MFMA
        for (int kv_idx = tile_start; kv_idx < tile_end; kv_idx++) {
            int lds_idx = ((kv_idx - tile_start) % KV_TILE_SIZE) * QK_DIM;
            const __hip_bfloat16* kv_ptr = &kv_lds[compute_tile * KV_TILE_S[9D[K
KV_TILE_SIZE * QK_DIM + lds_idx];

            // MFMA-based dot product (32x32x16 BF16)
            // Each warp computes partial dot for 32 KV dims at a time
            float dot = 0.0f;
            
            // Use MFMA for 16-element chunks
            for (int mfma_chunk = 0; mfma_chunk < QK_DIM / 16; mfma_chunk++[12D[K
mfma_chunk++) {
                // Load 16 Q and 16 K elements for MFMA
                // This is simplified - actual MFMA needs proper register l[1D[K
layout
                float q_val = 0.0f, k_val = 0.0f;
                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    int d = mfma_chunk * 16 + i;
                    if (d < QK_DIM) {
                        q_val += __bfloat162float(q_reg[d % 3]);
                        k_val += __bfloat162float(kv_ptr[d]);
                    }
                }
                dot += q_val * k_val;
            }

            // Warp reduction
            #pragma unroll
            for (int offset = 32; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset, WAVESIZE);
            }

            // Cross-warp reduction
            if (lane_id == 0) {
                warp_sums[warp_id * 2 + compute_tile] = dot;
            }
            __syncthreads();

            float score;
            if (tid == 0) {
                score = 0.0f;
                #pragma unroll
                for (int w = 0; w < 4; w++) {
                    score += warp_sums[w * 2 + compute_tile];
                }
                score *= sm_scale;
                warp_sums[compute_tile] = score;
            }
            __syncthreads();
            score = warp_sums[compute_tile];

            // Online softmax update
            float old_max = running_max;
            float new_max = fmaxf(old_max, score);
            float exp_score = expf(score - new_max);
            float correction = expf(old_max - new_max);

            running_sum = running_sum * correction + exp_score;
            running_max = new_max;

            // Accumulate weighted V
            float weight = exp_score;
            #pragma unroll
            for (int vi = 0; vi < 2; vi++) {
                int v_idx = tid * 2 + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * __bfloat1[9D[K
__bfloat162float(kv_ptr[v_idx]);
                }
            }
        }

        // Swap buffers
        load_tile = 1 - load_tile;
        compute_tile = 1 - compute_tile;
        __syncthreads();
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    #pragma unroll
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

    SET_NORMAL_PRIORITY();
}

// Phase 2: Reduce (optimized with warp primitives)
__global__ void mla_reduce_mfma(
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

    SET_HIGH_PRIORITY();

    float global_max = -1e30f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    float total_weight = 0.0f;
    float total_v = 0.0f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float w = expf(partial_lse[base] - global_max);
        total_weight += w;
        total_v += partial_out[base * V_DIM + v_idx] * expf(partial_max[bas[20D[K
expf(partial_max[base] - global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / total_weight);
    SET_NORMAL_PRIORITY();
}

void launch_mla_mfma(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor par[3D[K
partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits, float sm_scale
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_splitk_phase1_mfma<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_reduce_mfma<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_mla_mfma(torch::Tensor Q, torch::Tensor KV,
                torch::Tensor partial_out, torch::Tensor partial_max,
                torch::Tensor partial_lse, torch::Tensor output,
                torch::Tensor kv_indptr,
                int batch_size, int total_q, int num_splits, float sm_scale[8D[K
sm_scale);
"""

try:
    _mod = load_inline(
        name="custom_mla_mfma", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP[17D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla_mfma"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-mllvm --amdgpu-fast-math=1"],
    )
    _OK = True
except Exception as e:
    print(f"[custom_mla_mfma] Build failed: {e}")
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

    _mod.launch_mla_mfma(
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
            print(f"[custom_mla_mfma] Runtime error: {e}")

    return _asm_attention(data)
```

Wait, I need to reconsider. The MFMA implementation I wrote above is not co[2D[K
correct - MFMA requires specific register layouts and the intrinsic signatu[7D[K
signature is different. Let me focus on the most impactful optimization tha[3D[K
that's guaranteed to work:

**Vectorized 128-bit global loads** - This is the safest and most impactful[9D[K
impactful optimization for memory-bound attention kernels.

Let me rewrite with proper vectorized loads and better memory access patter[6D[K
patterns:

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized loads + LDS tiling for GEMV attention.

Key optimizations:
- Vectorized 128-bit global loads (4x BF16 per load = 8 bytes)
- LDS tiling for KV reuse across threads
- Warp-level shuffle reduction (no shared memory barriers)
- XCD priority hints for better scheduling
- Fused Phase 1+2 for small split counts
"""
```

Actually, looking at the constraints more carefully:
- The kernel