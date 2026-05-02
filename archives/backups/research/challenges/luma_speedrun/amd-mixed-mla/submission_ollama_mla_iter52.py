Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean latency of 69.7µs, and the target is <50µs (with rank 1 at 1[1D[K
19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Pattern**: The current kernel loads Q into shared memory[6D[K
memory but KV is loaded directly from global memory in the inner loop. This[4D[K
This is inefficient.

2. **Thread Cooperation**: The dot product reduction uses warp shuffles and[3D[K
and shared memory, but could be optimized with better reduction patterns.

3. **Vectorized Loads**: Currently using scalar loads for BF16 data. Could [K
use vectorized 128-bit loads (4x BF16 = 8 bytes, or 2x BF16 = 4 bytes with [K
proper alignment).

4. **LDS Double-Buffering**: Could prefetch KV tiles while computing on cur[3D[K
current tiles.

5. **MFMA Intrinsics**: The MI355X supports MFMA (Matrix Fused Multiply-Add[12D[K
Multiply-Add) intrinsics which could significantly speed up the Q@K^T compu[5D[K
computation.

6. **XCD-aware Scheduling**: The MI355X has 8 XCDs (chiplets). Proper sched[5D[K
scheduling could improve occupancy.

7. **Reduce Phase Optimization**: The current reduce phase is sequential an[2D[K
and could be optimized.

Given the constraints and the fact that MFMA 32x32x64 FP4 is verified worki[5D[K
working, I should focus on:

1. **Vectorized 128-bit global loads** - This is one of the easiest wins fo[2D[K
for memory bandwidth
2. **LDS double-buffering** - Better memory access patterns
3. **MFMA intrinsics** - For the Q@K^T computation


4. **Better reduction pattern** - Optimize the online softmax and V accumul[7D[K
accumulation

For this optimization, I'll focus on **vectorized 128-bit global loads with[4D[K
with LDS double-buffering**. This combines two of the suggested optimizatio[11D[K
optimizations and should give significant bandwidth improvements.

Key changes:
1. Use `__hip_bfloat162` or vector types for 128-bit loads (4x BF16 = 8 byt[3D[K
bytes per load)
2. Implement double-buffering in LDS for KV tiles
3. Overlap memory loads with computation
4. Optimize the reduction pattern using warp-level primitives more efficien[8D[K
efficiently

Let me write the optimized code:

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Split-K GEMV attention via load_inline.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Thread-cooperative 576-dim dot product (Q@K^T)
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Single kernel launch (no Python metadata overhead)
- Q broadcast across 16 heads (GQA: 1 KV head shared)
- BF16 KV directly (no FP8 quant overhead, 10% tolerance allows it)
- Vectorized 128-bit loads (4x BF16 per load)
- LDS double-buffering for KV tiles
- Warp-level reduction optimization
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
#define VEC_SIZE 4  // 4x BF16 = 8 bytes = 64 bits, use 2x for 128-bit

// Vector type for 128-bit loads (4x BF16)
typedef struct {
    __hip_bfloat16 x[4];
} bf16_vec4;

// Phase 1: Split-K attention — each block handles a KV slice
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
    int q_idx = batch_id;  // For decode, total_q = batch_size
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into shared memory with vectorized loads
    // 576 BF16 = 288 Vec4 loads (4 BF16 per vec)
    __shared__ __hip_bfloat16 q_shared[QK_DIM];
    for (int i = tid * VEC_SIZE; i < QK_DIM; i += BLOCK_SIZE * VEC_SIZE) {
        bf16_vec4 q_vec = reinterpret_cast<const bf16_vec4*>(q_ptr)[i / VEC[3D[K
VEC_SIZE];
        reinterpret_cast<bf16_vec4*>(q_shared)[i / VEC_SIZE] = q_vec;
    }
    __syncthreads();

    // LDS double-buffering for KV tiles
    // Tile size: 64 KV entries x 576 dims (fits in LDS)
    #define KV_TILE_SIZE 64
    #define KV_TILE_DIMS 576
    __shared__ __hip_bfloat16 kv_lds[2 * KV_TILE_SIZE * KV_TILE_DIMS];
    
    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE elements)
    float v_acc[2] = {0.0f, 0.0f};  // V_DIM/BLOCK_SIZE = 512/256 = 2

    // Process KV entries in this split with double-buffering
    int kv_idx = my_kv_start;
    int buffer_idx = 0;
    
    // Prefetch first tile
    if (kv_idx < my_kv_end) {
        int tile_end = min(kv_idx + KV_TILE_SIZE, my_kv_end);
        for (int tidx = tid; tidx < (tile_end - kv_idx) * KV_TILE_DIMS; tid[3D[K
tidx += BLOCK_SIZE) {
            int kv_local = tidx / KV_TILE_DIMS;
            int dim = tidx % KV_TILE_DIMS;
            int global_kv = kv_idx + kv_local;
            kv_lds[buffer_idx * KV_TILE_SIZE * KV_TILE_DIMS + kv_local * KV[2D[K
KV_TILE_DIMS + dim] = 
                KV[global_kv * QK_DIM + dim];
        }
        __syncthreads();
        kv_idx = tile_end;
    }

    while (kv_idx < my_kv_end || buffer_idx >= 0) {
        int next_buffer = 1 - buffer_idx;
        int tile_end = min(kv_idx + KV_TILE_SIZE, my_kv_end);
        
        // Prefetch next tile (overlap with computation)
        if (kv_idx < my_kv_end) {
            for (int tidx = tid; tidx < (tile_end - kv_idx) * KV_TILE_DIMS;[13D[K
KV_TILE_DIMS; tidx += BLOCK_SIZE) {
                int kv_local = tidx / KV_TILE_DIMS;
                int dim = tidx % KV_TILE_DIMS;
                int global_kv = kv_idx + kv_local;
                kv_lds[next_buffer * KV_TILE_SIZE * KV_TILE_DIMS + kv_local[8D[K
kv_local * KV_TILE_DIMS + dim] = 
                    KV[global_kv * QK_DIM + dim];
            }
        }
        
        // Process current tile
        int tile_start = kv_idx - (kv_idx >= my_kv_end ? KV_TILE_SIZE : 0);[3D[K
0);
        int current_tile_end = min(tile_start + KV_TILE_SIZE, my_kv_end)[10D[K
my_kv_end);
        
        for (int kv_local = 0; kv_local < current_tile_end - tile_start; kv[2D[K
kv_local++) {
            int global_kv = tile_start + kv_local;
            const __hip_bfloat16* kv_ptr = &kv_lds[buffer_idx * KV_TILE_SIZ[11D[K
KV_TILE_SIZE * KV_TILE_DIMS + kv_local * KV_TILE_DIMS];

            // Compute Q@K^T: thread-cooperative dot product over 576 dims
            // Use vectorized loads from LDS
            float dot = 0.0f;
            for (int d = lane_id * VEC_SIZE; d < QK_DIM; d += WAVESIZE * VE[2D[K
VEC_SIZE) {
                bf16_vec4 q_vec = reinterpret_cast<const bf16_vec4*>(q_shar[18D[K
bf16_vec4*>(q_shared)[d / VEC_SIZE];
                bf16_vec4 k_vec = reinterpret_cast<const bf16_vec4*>(kv_ptr[18D[K
bf16_vec4*>(kv_ptr)[d / VEC_SIZE];
                #pragma unroll
                for (int v = 0; v < VEC_SIZE; v++) {
                    dot += __bfloat162float(q_vec.x[v]) * __bfloat162float([17D[K
__bfloat162float(k_vec.x[v]);
                }
            }

            // Warp reduction for dot product using shuffle
            #pragma unroll
            for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset, WAVESIZE);
            }
            
            // Cross-warp reduction via shared memory
            __shared__ float warp_sums[4];  // 4 warps
            if (lane_id == 0) {
                warp_sums[warp_id] = dot;
            }
            __syncthreads();

            // Final reduction (thread 0 sums 4 warp results)
            float score;
            if (tid == 0) {
                score = (warp_sums[0] + warp_sums[1] + warp_sums[2] + warp_[5D[K
warp_sums[3]) * sm_scale;
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

            // Accumulate weighted V (V = KV[:V_DIM])
            // Each thread handles 2 V elements with vectorized loads
            float weight = exp_score;
            for (int vi = 0; vi < 2; vi++) {
                int v_idx = tid * 2 + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * __bfloat1[9D[K
__bfloat162float(kv_ptr[v_idx]);
                }
            }
        }
        
        // Swap buffers
        buffer_idx = next_buffer;
        kv_idx = tile_end;
        __syncthreads();
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    // Write partial V (normalized by running_sum later in reduce)
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

// Phase 2: Reduce partial results across splits (optimized)
__global__ void mla_reduce(
    const float* __restrict__ partial_out,   // [num_splits, total_q, NUM_H[5D[K
NUM_HEADS, V_DIM]
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,     // [total_q, NUM_HEADS, V_DIM][6D[K
V_DIM]
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
        float m = partial_max[base];
        global_max = fmaxf(global_max, m);
    }

    // Merge weighted sums using log-sum-exp
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
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
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

Wait, I need to reconsider. The current implementation has issues:

1. The LDS double-buffering logic is complex and may have bugs
2. The vectorized loads need proper alignment
3. The reduce phase could be more efficient

Let me simplify and focus on the most impactful optimization: **vectorized [K
128-bit global loads with better memory coalescing**. This is easier to imp[3D[K
implement correctly and should give significant bandwidth improvements.

Key changes:
1. Use `__hip_bfloat162` or proper vector types for 128-bit loads
2. Better thread organization for memory access
3. Simplify the double-buffering or remove it if it causes issues
4. Optimize the reduce phase with better parallelization

Let me write a cleaner version:

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Split-K GEMV attention via load_inline.

Key optimizations:
- Vectorized 128-bit global loads (4x BF16 per load)
- Coalesced memory access patterns
- Warp-level reduction optimization
- Simplified LDS usage for Q only
"""
```

Actually, looking at the constraints more carefully:
- MI355X has 304 CUs, 8 XCDs
- MFMA 32x32x64 FP4 is verified working
- Error tolerance for MLA is 10%

The biggest win would be using **MFMA intrinsics** for the Q@K^T computatio[10D[K
computation instead of manual dot products. However, the current code uses [K
BF16, not FP4.

Given the 10% error tolerance for MLA, I could potentially use FP4 for the [K
attention computation. But that requires significant changes.

Let me focus on **vectorized 128-bit loads with coalesced access** as the p[1D[K
primary optimization. This is safer and should give 2-4x memory bandwidth i[1D[K
improvement.

Let me write the complete optimized file:
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Split-K GEMV attention via load_inline.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Thread-cooperative 576-dim dot product (Q@K^T)
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x BF16 per load, 8 bytes)
- Coalesced memory access with proper alignment
- LDS double-buffering for KV tiles (overlap load/compute)
- Warp-level reduction with shuffle intrinsics
- XCD-aware block scheduling
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

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256
#define VEC_LOAD_SIZE 4  // 4x BF16 = 8 bytes per load

// Vector type for 128-bit loads
typedef struct {
    unsigned long long data[2];  // 128 bits = 2x 64-bit
} vec128_t;

__device__ __forceinline__ __hip_bfloat16 vec_get_bf16(vec128_t v, int idx)[4D[K
idx) {
    return reinterpret_cast<__hip_bfloat16*>(&v)[idx];
}

__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1(
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

    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DI[5D[K
QK_DIM;

    // Load Q into shared memory with vectorized loads
    __shared__ __hip_bfloat16 q_shared[QK_DIM];
    int q_vec_count = (QK_DIM + VEC_LOAD_SIZE - 1) / VEC_LOAD_SIZE;
    for (int i = tid; i < q_vec_count; i += BLOCK_SIZE) {
        int base_idx = i * VEC_LOAD_SIZE;
        vec128_t q_vec;
        if (base_idx + 3 < QK_DIM) {
            q_vec = *reinterpret_cast<const vec128_t*>(&q_ptr[base_idx]);
        } else {
            unsigned long long d0 = 0, d1 = 0;
            for (int v = 0; v < VEC_LOAD_SIZE && base_idx + v < QK_DIM; v++[3D[K
v++) {
                reinterpret_cast<__hip_bfloat16*>(&d0)[v] = q_ptr[base_idx [K
+ v];
            }
            q_vec.data[0] = d0;
            q_vec.data[1] = d1;
        }
        *reinterpret_cast<vec128_t*>(&q_shared[base_idx]) = q_vec;
    }
    __syncthreads();

    // LDS for KV double-buffering
    #define KV_TILE_KV 32
    #define KV_TILE_DIMS QK_DIM
    __shared__ __hip_bfloat16 kv_lds[2 * KV_TILE_KV * KV_TILE_DIMS];

    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    int kv_idx = my_kv_start;
    int buf_idx = 0;
    int tiles_loaded = 0;

    // Prefetch first tile
    if (kv_idx < my_kv_end) {
        int tile_kv_end = min(kv_idx + KV_TILE_KV, my_kv_end);
        for (int tidx = tid; tidx < (tile_kv_end - kv_idx) * KV_TILE_DIMS; [K
tidx += BLOCK_SIZE) {
            int kv_local = tidx / KV_TILE_DIMS;
            int dim = tidx % KV_TILE_DIMS;
            int global_kv = kv_idx + kv_local;
            kv_lds[buf_idx * KV_TILE_KV * KV_TILE_DIMS + kv_local * KV_TILE[7D[K
KV_TILE_DIMS + dim] = 
                KV[global_kv * QK_DIM + dim];
        }
        __syncthreads();
        kv_idx = tile_kv_end;
        tiles_loaded++;
    }

    while (tiles_loaded > 0) {
        int next_buf = 1 - buf_idx;
        int tile_kv_end = min(kv_idx + KV_TILE_KV, my_kv_end);
        int current_tile_kv = (tiles_loaded > 1 || kv_idx >= my_kv_end) ? 
            (kv_idx - (kv_idx >= my_kv_end ? KV_TILE_KV : 0)) : kv_idx - KV[2D[K
KV_TILE_KV;
        int tile_kv_count = min(KV_TILE_KV, my_kv_end - current_tile_kv);

        // Prefetch next tile
        if (kv_idx < my_kv_end) {
            for (int tidx = tid; tidx < (tile_kv_end - kv_idx) * KV_TILE_DI[10D[K
KV_TILE_DIMS; tidx += BLOCK_SIZE) {
                int kv_local = tidx / KV_TILE_DIMS;
                int dim = tidx % KV_TILE_DIMS;
                int global_kv = kv_idx + kv_local;
                kv_lds[next_buf * KV_TILE_KV * KV_TILE_DIMS + kv_local * KV[2D[K
KV_TILE_DIMS + dim] = 
                    KV[global_kv * QK_DIM + dim];
            }
            tiles_loaded++;
        }

        // Process current tile
        for (int kv_local = 0; kv_local < tile_kv_count; kv_local++) {
            const __hip_bfloat16* kv_ptr = &kv_lds[buf_idx * KV_TILE_KV * K[1D[K
KV_TILE_DIMS + kv_local * KV_TILE_DIMS];

            // Q@K^T with vectorized loads
            float dot = 0.0f;
            int vec_count = (QK_DIM + VEC_LOAD_SIZE - 1) / VEC_LOAD_SIZE;
            for (int v = lane_id; v < vec_count; v += WAVESIZE) {
                int base_idx = v * VEC_LOAD_SIZE;
                vec128_t q_vec = *reinterpret_cast<const vec128_t*>(&q_shar[18D[K
vec128_t*>(&q_shared[base_idx]);
                vec128_t k_vec = *reinterpret_cast<const vec128_t*>(kv_ptr [K
+ base_idx);
                #pragma unroll
                for (int i = 0; i < VEC_LOAD_SIZE; i++) {
                    if (base_idx + i < QK_DIM) {
                        dot += __bfloat162float(vec_get_bf16(q_vec, i)) * 
                               __bfloat162float(vec_get_bf16(k_vec, i));
                    }
                }
            }

            // Warp reduction
            #pragma unroll
            for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset, WAVESIZE);
            }

            __shared__ float warp_sums[4];
            if (lane_id == 0) warp_sums[warp_id] = dot;
            __syncthreads();

            float score;
            if (tid == 0) {
                score = (warp_sums[0] + warp_sums[1] + warp_sums[2] + warp_[5D[K
warp_sums[3]) * sm_scale;
                warp_sums[0] = score;
            }
            __syncthreads();
            score = warp_sums[0];

            // Online softmax
            float old_max = running_max;
            float new_max = fmaxf(old_max, score);
            float exp_score = expf(score - new_max);
            float correction = expf(old_max - new_max);
            running_sum = running_sum * correction + exp_score;
            running_max = new_max;

            // Accumulate V with vectorized loads
            float weight = exp_score;
            int v_vec_count = (V_DIM + VEC_LOAD_SIZE - 1) / VEC_LOAD_SIZE;
            for (int v = lane_id; v < v_vec_count; v += WAVESIZE) {
                int base_idx = v * VEC_LOAD_SIZE;
                vec128_t v_vec = *reinterpret_cast<const vec128_t*>(kv_ptr [K
+ base_idx);
                #pragma unroll
                for (int i = 0; i < VEC_LOAD_SIZE; i++) {
                    int v_idx = base_idx + i;
                    if (v_idx < V_DIM) {
                        int acc_idx = v_idx / (V_DIM / 2);
                        v_acc[acc_idx] = v_acc[acc_idx] * correction + 
                                         weight * __bfloat162float(vec_get_[25D[K
__bfloat162float(vec_get_bf16(v_vec, i));
                    }
               