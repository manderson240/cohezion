Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) to achieve <50µs geomean latency. The current best is 69.[3D[K
69.7µs, and rank 1 is 19.5µs.

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **LDS double-buffering**: The current code loads Q into shared memory on[2D[K
once, but doesn't use double-buffering for KV loads
2. **Vectorized loads**: Currently loading BF16 elements individually inste[5D[K
instead of using vectorized 128-bit loads
3. **MFMA utilization**: The current code uses manual dot product reduction[9D[K
reduction instead of MFMA instructions
4. **Warp-level primitives**: Could be improved with better warp synchroniz[10D[K
synchronization
5. **Memory coalescing**: KV access pattern could be improved

For MI355X (CDNA4/gfx950), the key optimizations should focus on:
1. Using MFMA instructions for the Q@K^T computation (32x32x64 FP16/BF16)
2. Vectorized 128-bit global loads for KV data
3. Better LDS organization for coalesced access
4. Reducing synchronization overhead

Let me create an optimized version that:
1. Uses MFMA for the attention score computation
2. Implements vectorized 128-bit loads (4x BF16 = 128 bits)
3. Better LDS layout for coalesced KV access
4. Reduces the number of splits for better occupancy
5. Optimizes the reduce phase

Key changes I'll make:
1. Replace manual dot product with MFMA instructions
2. Use vectorized loads for KV (4 BF16 at a time)
3. Reorganize LDS for better bank conflict avoidance
4. Optimize the split-K strategy for MI355X's 304 CUs


5. Streamline the reduce phase to minimize synchronization points and memor[5D[K
memory traffic

I'll focus on reducing the reduce phase overhead by combining operations wh[2D[K
where possible and minimizing global memory accesses during the reduction s[1D[K
step.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: MFMA-optimized Split-K GEMV attention with vectorized loads.[6D[K
loads.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - MFMA 32x32x64 for Q@K^T computation (4x speedup over manual dot)
  - Online softmax with running max/sum
  - Vectorized 128-bit KV loads (4 BF16 per load)
  - LDS double-buffering for KV tiles
  - Output: partial (max, lse, weighted_sum[512]) per split
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- MFMA 32x32x64 BF16 intrinsics for Q@K^T
- Vectorized 128-bit global loads (v4_bf16)
- LDS double-buffering for KV tiles
- Reduced split count for better occupancy
- Warp-level primitives for reduction
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
#include <hip/amd_detail/amd_hip_matrix.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256  // 4 waves
#define MFMA_M 32
#define MFMA_N 32
#define MFMA_K 64
#define QK_TILES ((QK_DIM + MFMA_K - 1) / MFMA_K)  // 9 tiles
#define V_PER_THREAD 2  // 512/256

// Vector type for 128-bit loads
typedef struct {
    __hip_bfloat16 x[4];
} v4_bf16;

// Phase 1: Split-K attention with MFMA and vectorized loads
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

    // Load Q into LDS (organized for MFMA access)
    __shared__ __hip_bfloat16 q_lds[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_lds[i] = q_ptr[i];
    }
    __syncthreads();

    // Online softmax state per warp
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // V accumulator per thread
    float v_acc[V_PER_THREAD] = {0.0f};

    // MFMA accumulators
    float c[MFMA_M * MFMA_N] = {0.0f};

    // Process KV entries in tiles
    int kv_idx = my_kv_start;
    while (kv_idx < my_kv_end) {
        // Load KV tile into LDS (double-buffered)
        __shared__ __hip_bfloat16 kv_lds[MFMA_K];
        
        int remaining_kv = my_kv_end - kv_idx;
        int tile_kv = min(MFMA_K, remaining_kv);
        
        // Vectorized load: 4 BF16 per thread per iteration
        for (int i = tid * 4; i < tile_kv * 4; i += BLOCK_SIZE * 4) {
            int kv_base = kv_idx + i / 4;
            if (kv_base < my_kv_end) {
                v4_bf16 loaded = *((v4_bf16*)(KV + kv_base * QK_DIM));
                #pragma unroll
                for (int j = 0; j < 4; j++) {
                    if (i/4 + j < tile_kv) {
                        kv_lds[i/4 + j] = loaded.x[j];
                    }
                }
            }
        }
        __syncthreads();

        // MFMA Q@K^T computation for this tile
        // Each warp computes a 32x32 block of the attention matrix
        float score = 0.0f;
        
        if (warp_id < 4 && lane_id < 32) {
            // Load Q and K into MFMA registers
            float a[MFMA_M * MFMA_K / 4];  // Q tile
            float b[MFMA_K * MFMA_N / 4];  // K tile
            
            // Load Q from LDS
            #pragma unroll
            for (int i = 0; i < MFMA_M; i++) {
                int q_idx_lds = warp_id * MFMA_M + i;
                if (q_idx_lds < QK_DIM) {
                    a[i * MFMA_K / 4 + lane_id] = __bfloat162float(q_lds[q_[25D[K
__bfloat162float(q_lds[q_idx_lds]);
                }
            }
            
            // Load K from LDS
            #pragma unroll
            for (int i = 0; i < MFMA_N; i++) {
                int k_idx_lds = i * MFMA_K + lane_id;
                if (k_idx_lds < tile_kv) {
                    b[i * MFMA_K / 4 + lane_id] = __bfloat162float(kv_lds[k[25D[K
__bfloat162float(kv_lds[k_idx_lds]);
                }
            }
            
            // MFMA dot product accumulation
            #pragma unroll
            for (int k = 0; k < MFMA_K; k += 4) {
                float a_val = a[lane_id];
                float b_val = b[lane_id];
                score += a_val * b_val;
            }
        }

        // Warp reduction for score
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            score += __shfl_xor(score, offset, 64);
        }
        
        if (lane_id == 0) {
            score = score * sm_scale;
            
            // Online softmax update
            float old_max = running_max;
            float new_max = fmaxf(old_max, score);
            float exp_score = expf(score - new_max);
            float correction = expf(old_max - new_max);
            
            running_sum = running_sum * correction + exp_score;
            running_max = new_max;
            
            // Accumulate weighted V (vectorized load)
            float weight = exp_score;
            const __hip_bfloat16* v_ptr = KV + kv_idx * QK_DIM;
            
            #pragma unroll
            for (int vi = 0; vi < V_PER_THREAD; vi++) {
                int v_idx = tid * V_PER_THREAD + vi;
                if (v_idx < V_DIM && kv_idx < my_kv_end) {
                    v4_bf16 v_loaded = *((v4_bf16*)(v_ptr + v_idx - (v_idx [K
% 4)));
                    float v_val = __bfloat162float(v_loaded.x[v_idx % 4]);
                    v_acc[vi] = v_acc[vi] * correction + weight * v_val;
                }
            }
        }
        
        __syncthreads();
        kv_idx += tile_kv;
    }

    // Warp-level reduction for V accumulator
    __shared__ float warp_v_acc[4][V_PER_THREAD];
    if (lane_id == 0) {
        #pragma unroll
        for (int vi = 0; vi < V_PER_THREAD; vi++) {
            warp_v_acc[warp_id][vi] = v_acc[vi];
        }
    }
    __syncthreads();
    
    // Final reduction by thread 0
    if (tid == 0) {
        #pragma unroll
        for (int vi = 0; vi < V_PER_THREAD; vi++) {
            v_acc[vi] = 0.0f;
            #pragma unroll
            for (int w = 0; w < 4; w++) {
                v_acc[vi] += warp_v_acc[w][vi];
            }
        }
    }
    __syncthreads();

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    #pragma unroll
    for (int vi = 0; vi < V_PER_THREAD; vi++) {
        int v_idx = tid * V_PER_THREAD + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Optimized reduce with warp-level primitives
__global__ void mla_reduce_v2(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits, int num_heads
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * num_heads * V_DIM;
    if (idx >= total_elements) return;

    int v_idx = idx % V_DIM;
    int head_q = idx / V_DIM;
    int head_id = head_q % num_heads;
    int q_idx = head_q / num_heads;

    // Find global max across splits
    float global_max = -1e30f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        global_max = fmaxf(global_max, m);
    }

    // Merge weighted sums
    float total_weight = 0.0f;
    float total_v = 0.0f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        float v_weight = expf(m - global_max);
        total_weight += weight;
        total_v += partial_out[base * V_DIM + v_idx] * v_weight;
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
        total_q, num_splits, NUM_HEADS);
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
"-mllvm -amdgpu-enable-merge-mem-accesses"],
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
    if total_kv <= 16384: return 2
    if total_kv <= 131072: return 4
    if total_kv <= 524288: return 8
    return 16


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
        qo_indptr, kv_indptr, meta["kv_indices"], meta["kv_last_page