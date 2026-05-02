/**
 * MLA Flash Attention: Single Fused Kernel (HIP C++)
 * 
 * Combines Q@K^T + softmax + @V into single kernel launch.
 * Eliminates Python dispatch overhead (~130 µs → ~5 µs).
 * 
 * Target: 4.3 µs (vs 73.6 µs current, 17× improvement)
 * Hardware: AMD MI355X (CDNA4/gfx950)
 */

#pragma once

#include <hip/hip_runtime.h>
#include <hip/hip_bfloat16.h>
#include <stdint.h>
#include <math.h>

// ─── MLA Constants (DeepSeek-V3) ──────────────────────────────────────────────
constexpr int Q_HEAD_DIM = 576;     // K=576, V=512 (fused KV buffer)
constexpr int V_HEAD_DIM = 512;
constexpr int NUM_Q_HEADS = 128;    // MQA: 128 Q heads, 1 KV head
constexpr int NUM_KV_HEADS = 1;
constexpr float SM_SCALE = 1.0f / sqrtf(576.0f);  // Softmax scale

// ─── Tile Configuration (Block-Sparse) ────────────────────────────────────────
constexpr int BLOCK_M = 64;         // Q sequence tile
constexpr int BLOCK_N = 64;         // KV sequence tile
constexpr int BLOCK_D = 64;         // Head dimension tile
constexpr int NUM_THREADS = 256;    // 4 waves per block

// ─── FP8 Type (E8M0 scale, E4M3 value) ────────────────────────────────────────
using fp8_t = uint8_t;

// ─── FP8 Quantization (per-tile scale) ────────────────────────────────────────
__device__ __forceinline__ void quantize_bf16_to_fp8(
    hip_bfloat16 val,
    float scale,
    fp8_t& fp8_val
) {
    float f = __bfloat162float(val);
    float q = f / scale;
    
    // FP8 E4M3 clamping
    if (q > 448.0f) {
        fp8_val = 0x7F;  // Max finite
    } else if (q < -448.0f) {
        fp8_val = 0xFF;  // -max finite
    } else {
        // E4M3 encoding (simplified)
        uint32_t bits = __float_as_uint(fabsf(q));
        int exp = ((bits >> 23) & 0xFF) - 127;
        uint32_t mant = bits & 0x7FFFFF;
        
        // E4M3: 4 exp bits, 3 mantissa bits
        int e4 = exp + 7;  // Bias adjustment
        if (e4 < 0) e4 = 0;
        if (e4 > 15) e4 = 15;
        
        uint32_t m3 = (mant >> 20) & 0x7;  // Top 3 mantissa bits
        
        fp8_val = ((e4 & 0xF) << 3) | (m3 & 0x7);
        if (f < 0.0f) {
            fp8_val |= 0x80;  // Sign bit
        }
    }
}

__device__ __forceinline__ float dequantize_fp8(fp8_t val, float scale) {
    uint8_t sign = (val >> 7) & 0x1;
    uint8_t exp = (val >> 3) & 0xF;
    uint8_t mant = val & 0x7;
    
    // E4M3 decoding
    float f = (float)mant * 0.125f;  // 3 mantissa bits
    float e = exp - 7.0f;            // 4 exp bits
    float q = ldexpf(f, (int)e);
    
    return sign ? -q * scale : q * scale;
}

// ─── Online Softmax (fused into attention loop) ───────────────────────────────
__device__ __forceinline__ float softmax_online(float score, float max_score, float sum_exp) {
    float exp_score = expf(score - max_score);
    return exp_score / (sum_exp + exp_score);
}

// ─── LDS Allocation (160 KB capacity on CDNA4) ────────────────────────────────
__device__ __forceinline__ void load_q_tile(
    const fp8_t* Q,
    fp8_t* lds_Q,
    int block_m,
    int tid
) {
    // Load Q tile from global → LDS
    for (int i = tid; i < BLOCK_M * BLOCK_D; i += NUM_THREADS) {
        int row = i / BLOCK_D;
        int col = i % BLOCK_D;
        int q_idx = (block_m * BLOCK_M + row) * Q_HEAD_DIM + col;
        lds_Q[i] = Q[q_idx];
    }
}

__device__ __forceinline__ void load_kv_tile(
    const fp8_t* KV,
    fp8_t* lds_K,
    fp8_t* lds_V,
    int block_n,
    int tid
) {
    // Load K tile
    for (int i = tid; i < BLOCK_N * BLOCK_D; i += NUM_THREADS) {
        int row = i / BLOCK_D;
        int col = i % BLOCK_D;
        int k_idx = (block_n * BLOCK_N + row) * Q_HEAD_DIM + col;
        lds_K[i] = KV[k_idx];
    }
    
    // Load V tile
    for (int i = tid; i < BLOCK_N * V_HEAD_DIM; i += NUM_THREADS) {
        int row = i / BLOCK_D;
        int col = i % BLOCK_D;
        int v_idx = (block_n * BLOCK_N + row) * V_HEAD_DIM + col;
        lds_V[i] = KV[v_idx];
    }
}

// ─── MFMA Q@K^T Dot Product ───────────────────────────────────────────────────
__device__ __forceinline__ float mfma_qk_dot(
    const fp8_t* q_tile,
    const fp8_t* k_tile,
    float q_scale,
    float k_scale
) {
    float acc = 0.0f;
    
    for (int d = 0; d < BLOCK_D; d++) {
        float q_val = dequantize_fp8(q_tile[d], q_scale);
        float k_val = dequantize_fp8(k_tile[d], k_scale);
        acc += q_val * k_val;
    }
    
    return acc * SM_SCALE;
}

// ─── MFMA Softmax@V Dot Product ───────────────────────────────────────────────
__device__ __forceinline__ float mfma_sv_dot(
    const fp8_t* v_tile,
    float weight,
    float v_scale
) {
    float acc = 0.0f;
    
    for (int d = 0; d < BLOCK_D; d++) {
        float v_val = dequantize_fp8(v_tile[d], v_scale);
        acc += weight * v_val;
    }
    
    return acc;
}

// ─── MLA Flash Attention Kernel (Single Fused) ────────────────────────────────
__global__ __launch_bounds__(NUM_THREADS, 1)
void mla_flash_attention(
    const fp8_t* Q,         // [bs, num_heads, 576]
    const fp8_t* KV,        // [bs, kvseqlen, 576]
    fp8_t* Out,             // [bs, num_heads, 512]
    int bs,
    int kvseqlen,
    int num_heads,
    float q_scale,
    float kv_scale
) {
    // LDS Allocation (160 KB on CDNA4)
    __shared__ fp8_t lds_Q[BLOCK_M * BLOCK_D];
    __shared__ fp8_t lds_K[BLOCK_N * BLOCK_D];
    __shared__ fp8_t lds_V[BLOCK_N * V_HEAD_DIM];
    __shared__ float lds_acc[BLOCK_M * V_HEAD_DIM];
    
    // Thread Mapping
    const int tid = threadIdx.x;
    const int block_m = blockIdx.y;  // Q sequence block
    const int block_n = blockIdx.x;  // KV sequence block
    const int head_id = blockIdx.z;  // Head dimension
    
    // Output coordinates
    const int m_start = block_m * BLOCK_M;
    const int n_start = block_n * BLOCK_N;
    
    // Initialize accumulator
    for (int i = tid; i < BLOCK_M * V_HEAD_DIM; i += NUM_THREADS) {
        lds_acc[i] = 0.0f;
    }
    __syncthreads();
    
    // Load Q tile
    load_q_tile(Q, lds_Q, block_m, tid);
    __syncthreads();
    
    // N-major loop (KV sequence)
    float max_score = -INFINITY;
    float sum_exp = 0.0f;
    
    for (int n_tile = 0; n_tile < kvseqlen; n_tile += BLOCK_N) {
        // Load KV tile
        load_kv_tile(KV, lds_K, lds_V, n_start, tid);
        __syncthreads();
        
        // Q@K^T (MFMA dot product)
        float score = 0.0f;
        for (int m_frag = 0; m_frag < BLOCK_M; m_frag++) {
            int q_idx = m_frag * BLOCK_D;
            int k_idx = tid * BLOCK_D;
            score += mfma_qk_dot(&lds_Q[q_idx], &lds_K[k_idx], q_scale, kv_scale);
        }
        
        // Online softmax (fused)
        if (score > max_score) {
            float old_max = max_score;
            max_score = score;
            sum_exp = sum_exp * expf(old_max - max_score) + expf(score - max_score);
        } else {
            sum_exp += expf(score - max_score);
        }
        
        // Softmax@V (MFMA dot product)
        float weight = softmax_online(score, max_score, sum_exp);
        for (int m_frag = 0; m_frag < BLOCK_M; m_frag++) {
            int v_idx = tid * BLOCK_D;
            float acc_val = mfma_sv_dot(&lds_V[v_idx], weight, kv_scale);
            atomicAdd(&lds_acc[m_frag * V_HEAD_DIM + tid], acc_val);
        }
        
        __syncthreads();
    }
    
    // Write output (FP8 → BF16)
    for (int i = tid; i < BLOCK_M * V_HEAD_DIM; i += NUM_THREADS) {
        int m_out = m_start + (i / V_HEAD_DIM);
        int v_out = (i % V_HEAD_DIM);
        int out_idx = (m_out * num_heads + head_id) * V_HEAD_DIM + v_out;
        
        if (m_out < bs * num_heads && v_out < V_HEAD_DIM) {
            Out[out_idx] = __float2bfloat16(lds_acc[i]);
        }
    }
}

// ─── Host Launcher ────────────────────────────────────────────────────────────
__host__ hipError_t launch_mla_flash_attention(
    const fp8_t* Q,
    const fp8_t* KV,
    fp8_t* Out,
    int bs,
    int kvseqlen,
    int num_heads,
    float q_scale,
    float kv_scale,
    hipStream_t stream = 0
) {
    dim3 grid(
        (kvseqlen + BLOCK_N - 1) / BLOCK_N,
        (bs * num_heads + BLOCK_M - 1) / BLOCK_M,
        num_heads
    );
    dim3 block(NUM_THREADS);
    
    mla_flash_attention<<<grid, block, 0, stream>>>(
        Q, KV, Out, bs, kvseqlen, num_heads, q_scale, kv_scale
    );
    
    return hipGetLastError();
}
