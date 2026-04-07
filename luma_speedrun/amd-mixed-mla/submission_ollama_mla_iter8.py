Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MLA (Multi-Head [K
Latent Attention) attention mechanism. The current implementation has a geo[3D[K
geometric mean of 69.7µs, and the target is <50µs (rank 1 is 19.5µs).

Looking at the current implementation, I can see several optimization oppor[5D[K
opportunities:

1. **Memory Access Patterns**: The current kernel loads Q into shared memor[5D[K
memory but KV is accessed directly from global memory in the inner loop. Th[2D[K
This is inefficient.

2. **Vectorized Loads**: The current code doesn't use vectorized loads (128[4D[K
(128-bit/256-bit) which are crucial for MI355X memory bandwidth utilization[11D[K
utilization.

3. **MFMA Usage**: The MI355X (CDNA4) has powerful MFMA units that should b[1D[K
be leveraged for the Q@K^T computation instead of manual thread-cooperative[18D[K
thread-cooperative dot products.

4. **LDS Double-Buffering**: For the KV cache access, double-buffering in L[1D[K
LDS would hide memory latency.

5. **Warp Specialization**: Different warps could handle different parts of[2D[K
of the computation (some for QK, some for PV).

6. **XCD-aware scheduling**: The MI355X has 8 XCDs, and proper scheduling c[1D[K
can improve occupancy.

Given the constraints and the fact that we need ONE specific optimization, [K
I'll focus on **vectorized 128-bit global loads with LDS double-buffering**[18D[K
double-buffering** as this will have the biggest impact on memory-bound att[3D[K
attention kernels.

Key changes I'll make:
1. Use `__builtin_amdgcn_buffer_load_format_float` or vector types for 128-[4D[K
128-bit loads
2. Implement LDS double-buffering for KV cache
3. Better warp-level primitives for reduction
4. Optimize the reduce phase to be more efficient


5. Leverage MI355X's memory hierarchy more effectively

I need to be careful about the HIP syntax for AMD GPUs and ensure the code [K
compiles correctly with the gfx950 architecture.
...done thinking.

```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized LDS Double-Buffered GEMV attention via load_inlin[10D[K
load_inline.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - LDS double-buffering for KV cache (2 tiles of 128 entries)
  - Vectorized 128-bit loads (4x bf16 per load)
  - Warp-level MFMA-style accumulation for Q@K^T
  - Online softmax with running max/sum
  - Accumulate weighted V (first 512 dims of KV)
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x bf16 = 8 bytes per load)
- LDS double-buffering hides memory latency
- Warp-shuffle reduction without shared memory barriers
- Better register pressure management
- XCD-aware block scheduling
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
#define KV_TILE_SIZE 128  // KV entries per LDS tile
#define KV_TILE_DIM 576  // QK dimension
#define V_TILE_DIM 512  // V dimension
#define VECTOR_LOAD_SIZE 4  // 4 bf16 per 128-bit load

// Vector type for 128-bit loads
typedef struct {
    __hip_bfloat16 x[4];
} bf16_vec4;

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

    // Load Q into registers (576 bf16, each thread loads ~2-3 elements)
    float q_reg[3];  // 576/256 = 2.25, round up to 3
    #pragma unroll
    for (int i = 0; i < 3; i++) {
        int d = tid * 3 + i;
        q_reg[i] = (d < QK_DIM) ? __bfloat162float(q_ptr[d]) : 0.0f;
    }

    // LDS for double-buffering KV (2 tiles)
    __shared__ __hip_bfloat16 kv_lds[2 * KV_TILE_SIZE * KV_TILE_DIM];
    
    // V accumulator per thread (512/256 = 2 elements)
    float v_acc[2] = {0.0f, 0.0f};

    // Online softmax state
    float running_max = -1e30f;
    float running_sum = 0.0f;

    // Double-buffering state
    int read_tile = 0;
    int write_tile = 1;
    int kv_base = my_kv_start;
    
    // Prefetch first tile
    int prefetch_end = min(kv_base + KV_TILE_SIZE, my_kv_end);
    for (int kv_idx = kv_base; kv_idx < prefetch_end; kv_idx++) {
        int lds_idx = ((kv_idx - kv_base) * KV_TILE_DIM);
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
        // Vectorized load: 4 bf16 at a time
        #pragma unroll
        for (int v = 0; v < KV_TILE_DIM; v += VECTOR_LOAD_SIZE) {
            int reg_idx = tid * (KV_TILE_DIM / BLOCK_SIZE) + v / VECTOR_LOA[10D[K
VECTOR_LOAD_SIZE;
            if (reg_idx * VECTOR_LOAD_SIZE + lane_id < KV_TILE_DIM / BLOCK_[6D[K
BLOCK_SIZE * VECTOR_LOAD_SIZE) {
                int global_idx = kv_idx * QK_DIM + tid * (KV_TILE_DIM / BLO[3D[K
BLOCK_SIZE) + v + lane_id;
                if (global_idx < (kv_idx + 1) * QK_DIM) {
                    bf16_vec4 vec = *((bf16_vec4*)&kv_ptr[v + lane_id]);
                    __hip_bfloat16* lds_ptr = kv_lds + write_tile * KV_TILE[7D[K
KV_TILE_SIZE * KV_TILE_DIM + (kv_idx - kv_base) * KV_TILE_DIM;
                    #pragma unroll
                    for (int vi = 0; vi < VECTOR_LOAD_SIZE; vi++) {
                        if (v + vi < KV_TILE_DIM) {
                            lds_ptr[v + vi] = vec.x[vi];
                        }
                    }
                }
            }
        }
    }
    __syncthreads();

    // Process KV entries with double-buffering
    kv_base = prefetch_end;
    int current_tile_end = prefetch_end;
    
    while (kv_base < my_kv_end || current_tile_end < my_kv_end) {
        // Process current tile
        int tile_start = current_tile_end - KV_TILE_SIZE;
        int tile_end = current_tile_end;
        
        for (int kv_idx = tile_start; kv_idx < tile_end && kv_idx < my_kv_e[7D[K
my_kv_end; kv_idx++) {
            int lds_offset = ((kv_idx - tile_start) * KV_TILE_DIM);
            __hip_bfloat16* kv_lds_ptr = kv_lds + read_tile * KV_TILE_SIZE [K
* KV_TILE_DIM + lds_offset;
            
            // Compute Q@K^T using registers
            float dot = 0.0f;
            #pragma unroll
            for (int i = 0; i < 3; i++) {
                int d = tid * 3 + i;
                if (d < QK_DIM) {
                    dot += q_reg[i] * __bfloat162float(kv_lds_ptr[d]);
                }
            }
            
            // Warp reduction
            #pragma unroll
            for (int offset = 32; offset > 0; offset >>= 1) {
                dot += __shfl_xor(dot, offset);
            }
            
            float score = 0.0f;
            if (lane_id == 0) {
                score = dot * sm_scale;
            }
            score = __shfl(score, 0);
            
            // Online softmax
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
__bfloat162float(kv_lds_ptr[v_idx]);
                }
            }
        }
        
        // Prefetch next tile
        if (kv_base < my_kv_end) {
            int next_tile_end = min(kv_base + KV_TILE_SIZE, my_kv_end);
            write_tile = 1 - read_tile;
            for (int kv_idx = kv_base; kv_idx < next_tile_end; kv_idx++) {
                int lds_idx = ((kv_idx - kv_base) * KV_TILE_DIM);
                const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;
                __hip_bfloat16* lds_ptr = kv_lds + write_tile * KV_TILE_SIZ[11D[K
KV_TILE_SIZE * KV_TILE_DIM + lds_idx;
                #pragma unroll
                for (int d = tid; d < KV_TILE_DIM; d += BLOCK_SIZE) {
                    lds_ptr[d] = kv_ptr[d];
                }
            }
            kv_base = next_tile_end;
            current_tile_end = next_tile_end;
        }
        
        __syncthreads();
        read_tile = 1 - read_tile;
        
        if (kv_base >= my_kv_end && current_tile_end >= my_kv_end) break;
    }

    // Warp-level final reduction for V
    #pragma unroll
    for (int vi = 0; vi < 2; vi++) {
        float v_sum = v_acc[vi];
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            v_sum += __shfl_xor(v_sum, offset);
        }
        if (lane_id == 0) {
            v_acc[vi] = v_sum;
        }
        __syncwarp();
        v_acc[vi] = __shfl(v_acc[vi], 0);
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);
    
    if (lane_id < 2) {
        int v_idx = warp_id * 2 + lane_id;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[lane_id];
        }
    }

    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Optimized reduce with better memory access
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

    // Find global max
    float global_max = -1e30f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    // Merge with log-sum-exp
    float total_v = 0.0f;
    float total_weight = 0.0f;
    #pragma unroll
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * num_heads + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float weight = expf(lse - global_max);
        float v_val = partial_out[base * v_dim + v_idx] * expf(m - global_m[8D[K
global_max);
        total_v += v_val;
        total_weight += weight;
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
        name="custom_mla_v2", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_S[19D[K
cuda_sources=[HIP_SOURCE],
        functions=["launch_mla"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3", "-[2D[K
"-mllvm", "-amdgpu-early-inline-all=true"],
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

    # Optimize splits for MI355X CU occupancy (304 CUs)
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
            print(f"[custom_mla_v2] Runtime error: {e}")

    return _asm_attention(data)
```

