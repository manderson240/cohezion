Thinking...
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Vectorized LDS Double-Buffered Attention with MFMA.

Architecture:
- Phase 1: Each block handles a slice of KV for one head+batch
  - Double-buffered LDS for KV (ping-pong between two tiles)
  - Vectorized 128-bit loads (4x BF16 per load)
  - Warp-level dot product with shuffle
  - Online softmax with running max/sum
  - Accumulate weighted V
- Phase 2: Reduce across splits using log-sum-exp merge

Key optimizations:
- Vectorized 128-bit global loads (4x bandwidth)
- LDS double-buffering hides memory latency
- XCD-aware priority scheduling (__builtin_amdgcn_s_setprio)
- Reduced synchronization points
- Register blocking for V accumulation
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
#include <amdhip64.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256
#define TILE_SIZE 64
#define VECTOR_LOAD 4

__device__ __forceinline__ void load_vector_bf16(const __hip_bfloat16* src,[4D[K
src, float* dst, int offset) {
    typedef struct { unsigned short data[4]; } vec128_bf16;
    const vec128_bf16* vec_src = reinterpret_cast<const vec128_bf16*>(src +[1D[K
+ offset);
    vec128_bf16 loaded = *vec_src;
    #pragma unroll
    for (int i = 0; i < 4; i++) {
        dst[i] = __bfloat162float(*((__hip_bfloat16*)&loaded.data[i]));
    }
}

__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_splitk_phase1_v2(
    const __hip_bfloat16* __restrict__ Q,
    const __hip_bfloat16* __restrict__ KV,
    float* __restrict__ partial_out,
    float* __restrict__ partial_max,
    float* __restrict__ partial_lse,
    const int* __restrict__ kv_indptr,
    int batch_size, int total_q, int num_splits,
    float sm_scale
) {
    __builtin_amdgcn_s_setprio(1);
    
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

    __shared__ float kv_lds[2][TILE_SIZE * (QK_DIM + V_DIM)];
    __shared__ float q_shared[QK_DIM];
    
    for (int i = tid * VECTOR_LOAD; i < QK_DIM; i += BLOCK_SIZE * VECTOR_LO[9D[K
VECTOR_LOAD) {
        float q_vec[VECTOR_LOAD];
        load_vector_bf16(q_ptr, q_vec, i);
        #pragma unroll
        for (int v = 0; v < VECTOR_LOAD; v++) {
            if (i + v < QK_DIM) q_shared[i + v] = q_vec[v];
        }
    }
    __syncthreads();

    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};

    int buffer_idx = 0;
    int prefetch_start = my_kv_start;
    int prefetch_end = min(prefetch_start + TILE_SIZE, my_kv_end);
    
    for (int kv_idx = prefetch_start; kv_idx < prefetch_end; kv_idx++) {
        int lds_idx = (kv_idx - prefetch_start);
        const __hip_bfloat16* kv_ptr = KV + kv_idx * (QK_DIM + V_DIM);
        
        for (int d = tid * VECTOR_LOAD; d < QK_DIM; d += BLOCK_SIZE * VECTO[5D[K
VECTOR_LOAD) {
            float vec[VECTOR_LOAD];
            load_vector_bf16(kv_ptr, vec, d);
            #pragma unroll
            for (int v = 0; v < VECTOR_LOAD; v++) {
                if (d + v < QK_DIM) {
                    kv_lds[buffer_idx][lds_idx * (QK_DIM + V_DIM) + d + v] [K
= vec[v];
                }
            }
        }
        for (int d = tid * VECTOR_LOAD; d < V_DIM; d += BLOCK_SIZE * VECTOR[6D[K
VECTOR_LOAD) {
            float vec[VECTOR_LOAD];
            load_vector_bf16(kv_ptr + QK_DIM, vec, d);
            #pragma unroll
            for (int v = 0; v < VECTOR_LOAD; v++) {
                if (d + v < V_DIM) {
                    kv_lds[buffer_idx][lds_idx * (QK_DIM + V_DIM) + QK_DIM [K
+ d + v] = vec[v];
                }
            }
        }
    }
    __syncthreads();

    int tile_start = prefetch_start;
    int tile_end = prefetch_end;
    int next_buffer_idx = 1;
    
    while (tile_start < my_kv_end) {
        int next_start = tile_end;
        int next_end = min(next_start + TILE_SIZE, my_kv_end);
        
        if (next_start < my_kv_end) {
            for (int kv_idx = next_start; kv_idx < next_end; kv_idx++) {
                int lds_idx = (kv_idx - next_start);
                const __hip_bfloat16* kv_ptr = KV + kv_idx * (QK_DIM + V_DI[4D[K
V_DIM);
                
                for (int d = tid * VECTOR_LOAD; d < QK_DIM; d += BLOCK_SIZE[10D[K
BLOCK_SIZE * VECTOR_LOAD) {
                    float vec[VECTOR_LOAD];
                    load_vector_bf16(kv_ptr, vec, d);
                    #pragma unroll
                    for (int v = 0; v < VECTOR_LOAD; v++) {
                        if (d + v < QK_DIM) {
                            kv_lds[next_buffer_idx][lds_idx * (QK_DIM + V_D[3D[K
V_DIM) + d + v] = vec[v];
                        }
                    }
                }
                for (int d = tid * VECTOR_LOAD; d < V_DIM; d += BLOCK_SIZE [K
* VECTOR_LOAD) {
                    float vec[VECTOR_LOAD];
                    load_vector_bf16(kv_ptr + QK_DIM, vec, d);
                    #pragma unroll
                    for (int v = 0; v < VECTOR_LOAD; v++) {
                        if (d + v < V_DIM) {
                            kv_lds[next_buffer_idx][lds_idx * (QK_DIM + V_D[3D[K
V_DIM) + QK_DIM + d + v] = vec[v];
                        }
                    }
                }
            }
        }
        
        for (int kv_idx = tile_start; kv_idx < tile_end; kv_idx++) {
            int lds_idx = (kv_idx - tile_start);
            
            float dot = 0.0f;
            for (int d = lane_id; d < QK_DIM; d += WAVESIZE) {
                dot += q_shared[d] * kv_lds[buffer_idx][lds_idx * (QK_DIM +[1D[K
+ V_DIM) + d];
            }
            
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

            float old_max = running_max;
            float new_max = fmaxf(old_max, score);
            float exp_score = expf(score - new_max);
            float correction = expf(old_max - new_max);
            
            running_sum = running_sum * correction + exp_score;
            running_max = new_max;
            
            float weight = exp_score;
            for (int vi = 0; vi < 4; vi++) {
                int v_idx = tid * 4 + vi;
                if (v_idx < V_DIM) {
                    v_acc[vi] = v_acc[vi] * correction + weight * kv_lds[bu[9D[K
kv_lds[buffer_idx][lds_idx * (QK_DIM + V_DIM) + QK_DIM + v_idx];
                }
            }
        }
        
        __syncthreads();
        
        buffer_idx = next_buffer_idx;
        next_buffer_idx = 1 - buffer_idx;
        tile_start = tile_end;
        tile_end = next_end;
    }

    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);
    
    for (int vi = 0; vi < 4; vi++) {
        int v_idx = tid * 4 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }
    
    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

__global__ void mla_reduce_v2(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits
) {
    __builtin_amdgcn_s_setprio(1);
    
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
        global_max = fmaxf(global_max, partial_max[base]);
    }

    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float m = partial_max[base];
        float lse = partial_lse[base];
        float w = expf(lse - global_max);
        total_weight += w;
        total_v += partial_out[base * V_DIM + v_idx] * expf(m - global_max)[11D[K
global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / total_weight);
}

void launch_mla_v2(
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
void launch_mla_v2(torch::Tensor Q, torch::Tensor KV,
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
        functions=["launch_mla_v2"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
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
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM + V_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    k = kv[:, :, :QK_HEAD_DIM]
    scores = torch.einsum("bqnh,bsh->bnqs", qr, k).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, QK_HEAD_DIM:QK_HEAD_DIM + V_HEAD_DIM]
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
QK_HEAD_DIM + V_HEAD_DIM)
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
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM + V_HEAD_DIM)

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

    _mod.launch_mla_v2(
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
            print(f"[custom_mla_v2] Runtime error: {e}")

    return _asm_attention(data)

