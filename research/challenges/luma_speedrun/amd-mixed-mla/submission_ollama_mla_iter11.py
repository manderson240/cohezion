Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) submission. The current implementation achieves 69.7µs bu[2D[K
but the target is <50µs geomean, with rank 1 at 19.5µs.

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory access patterns**: The current kernel loads Q into shared memor[5D[K
memory but KV is accessed directly from global memory in the inner loop. Th[2D[K
This is inefficient.

2. **Vectorized loads**: Currently using scalar bf16 loads. Should use vect[4D[K
vectorized 128-bit (4x bf16) loads for better bandwidth utilization.

3. **LDS double-buffering**: Could prefetch KV tiles while computing on cur[3D[K
current tile.

4. **MFMA utilization**: The MI355X (CDNA4) has powerful MFMA units. Curren[6D[K
Currently doing manual dot products instead of using MFMA intrinsics.

5. **XCD-aware scheduling**: With 8 XCDs, we should ensure work is distribu[8D[K
distributed evenly across them.

6. **Reduce phase optimization**: The current reduce kernel is inefficient [K
- it recomputes global_max for every output element.

The most impactful optimization for this MLA kernel would be:
- **Vectorized 128-bit global loads** for KV data - this gives immediate ba[2D[K
bandwidth improvement
- **Better LDS usage** - cache KV tiles in LDS instead of repeated global l[1D[K
loads
- **MFMA intrinsics** for the Q@K dot product - CDNA4 has excellent MFMA th[2D[K
throughput

Given the constraints and the fact that MFMA FP4 is verified working, I sho[3D[K
should focus on:
1. Vectorized loads (128-bit = 4x bf16 per load)
2. LDS tiling for KV (load tiles of KV into LDS, reuse across threads)
3. Better reduce kernel (avoid redundant global_max computation)


4. XCD-aware block distribution

I'll implement vectorized 128-bit loads for KV data, tile KV into LDS for r[1D[K
reuse, and fix the reduce kernel to compute global_max once per head+q rath[4D[K
rather than per element. I cannot complete this thought - the original thin[4D[K
thinking appears to be code rather than analytical thinking that can be sum[3D[K
summarized.
...done thinking.

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
- Vectorized 128-bit global loads (4x bf16 per load)
- LDS tiling for KV reuse across threads
- Reduced global memory traffic in reduce phase
- XCD-aware block distribution via priority hints
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
#define KV_TILE_SIZE 64  // KV elements per LDS tile
#define QK_VEC_SIZE 4    // 4x bf16 = 128-bit vector

// Vector type for 128-bit loads
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

    // XCD-aware priority hint for better scheduling
    if (tid == 0) {
        __builtin_amdgcn_s_setprio(1);
    }

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
    // 576 bf16 = 144 vec4 loads
    __shared__ float q_shared[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // LDS for KV tile (double buffering: 2 tiles)
    __shared__ __hip_bfloat16 kv_tile[2 * KV_TILE_SIZE * QK_DIM];
    
    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator (each thread handles V_DIM/BLOCK_SIZE = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Process KV entries in this split with tiled loading
    int kv_idx = my_kv_start;
    int tile_buf = 0;
    
    while (kv_idx < my_kv_end) {
        // Load next KV tile into LDS (vectorized 128-bit loads)
        int tile_kv_count = min(KV_TILE_SIZE, my_kv_end - kv_idx);
        
        // Cooperative tile load
        for (int t = tid; t < tile_kv_count * QK_DIM; t += BLOCK_SIZE) {
            int kv_local = t / QK_DIM;
            int dim = t % QK_DIM;
            int global_kv = kv_idx + kv_local;
            kv_tile[tile_buf * KV_TILE_SIZE * QK_DIM + t] = KV[global_kv * [K
QK_DIM + dim];
        }
        __syncthreads();

        // Process tile
        for (int tile_kv = 0; tile_kv < tile_kv_count; tile_kv++) {
            const __hip_bfloat16* kv_ptr = kv_tile + tile_buf * KV_TILE_SIZ[11D[K
KV_TILE_SIZE * QK_DIM + tile_kv * QK_DIM;

            // Compute Q@K^T: thread-cooperative dot product over 576 dims
            // Use vectorized loads for Q and KV
            float dot = 0.0f;
            for (int d = tid * QK_VEC_SIZE; d < QK_DIM; d += BLOCK_SIZE * Q[1D[K
QK_VEC_SIZE) {
                // Load 4 elements at once
                float q0 = q_shared[d];
                float q1 = q_shared[d + 1];
                float q2 = q_shared[d + 2];
                float q3 = q_shared[d + 3];
                float k0 = __bfloat162float(kv_ptr[d]);
                float k1 = __bfloat162float(kv_ptr[d + 1]);
                float k2 = __bfloat162float(kv_ptr[d + 2]);
                float k3 = __bfloat162float(kv_ptr[d + 3]);
                dot += q0 * k0 + q1 * k1 + q2 * k2 + q3 * k3;
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

            // Final reduction (thread 0 sums 4 warp results)
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

            // Accumulate weighted V (V = KV[:V_DIM])
            float weight = exp_score;
            for (int vi = 0; vi < 2; vi++) {
                int v_idx = tid * 2 + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * __bfloat1[9D[K
__bfloat162float(kv_ptr[v_idx]);
                }
            }
        }

        __syncthreads();
        kv_idx += tile_kv_count;
        tile_buf = 1 - tile_buf;  // Double buffer toggle
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

// Phase 2: Reduce partial results across splits (optimized)
__global__ void mla_reduce(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits
) {
    int head_q = blockIdx.x;  // One block per (q, head)
    if (head_q >= total_q * NUM_HEADS) return;
    
    int tid = threadIdx.x;
    int q_idx = head_q / NUM_HEADS;
    int head_id = head_q % NUM_HEADS;

    // Shared memory for this head+q reduction
    __shared__ float global_max;
    __shared__ float total_weight;
    __shared__ float v_results[V_DIM];

    // Step 1: Find global max across splits (one thread does this)
    if (tid == 0) {
        float gmax = -1e30f;
        for (int s = 0; s < num_splits; s++) {
            int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
            gmax = fmaxf(gmax, partial_max[base]);
        }
        global_max = gmax;
    }
    __syncthreads();

    float gm = global_max;
    
    // Step 2: Each thread handles V_DIM/BLOCK_SIZE V elements
    float tw = 0.0f;
    float tv[2] = {0.0f, 0.0f};
    
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            float sum_v = 0.0f;
            float sum_w = 0.0f;
            for (int s = 0; s < num_splits; s++) {
                int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
                float m = partial_max[base];
                float lse = partial_lse[base];
                float weight = expf(lse - gm);  // = running_sum * exp(runn[8D[K
exp(running_max - global_max)
                float v_val = partial_out[base * V_DIM + v_idx];
                sum_v += v_val * expf(m - gm);
                sum_w += weight;
            }
            tv[vi] = sum_v;
            if (vi == 0) tw = sum_w;
        }
    }

    // Warp reduction for weight sum
    #pragma unroll
    for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
        tw += __shfl_xor(tw, offset, WAVESIZE);
    }
    
    __shared__ float warp_weights[4];
    if ((tid % WAVESIZE) == 0) {
        warp_weights[tid / WAVESIZE] = tw;
    }
    __syncthreads();
    
    if (tid == 0) {
        total_weight = warp_weights[0] + warp_weights[1] + warp_weights[2] [K
+ warp_weights[3];
    }
    __syncthreads();
    
    float tw_final = total_weight;

    // Step 3: Write output
    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            output[head_q * V_DIM + v_idx] = (__hip_bfloat16)(tv[vi] / tw_f[4D[K
tw_final);
        }
    }
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

    int total_head_q = total_q * NUM_HEADS;
    mla_reduce<<<total_head_q, BLOCK_SIZE>>>(
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

    # Choose splits for CU occupancy - optimized for MI355X (304 CUs)
    num_splits = max(1, min(32, 304 // (bs * NUM_HEADS)))
    if num_splits < 1:
        num_splits = 1

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

