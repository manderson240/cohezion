/**
 * Iteration 5: MFMA Tile Tuning
 * 
 * Experiments with optimal BLOCK_M, BLOCK_N, BLOCK_K configurations.
 * AMD blog: 256×256_t512 optimal for large GEMM, 128×128 for small.
 * Expected: 10.8 µs (vs 11.2 µs direct LDS, -4% improvement)
 */

#include <hip/hip_runtime.h>
#include <hip/hip_bfloat16.h>
#include <stdint.h>
#include <math.h>

// ─── Tuned Tile Configs ───────────────────────────────────────────────────────
constexpr int WARP_SIZE = 64;

// Shape-dependent tile selection
__device__ __forceinline__ int get_block_m(int M, int N, int K) {
    if (M <= 16) return 64;
    if (M <= 64) return 128;
    return 256;
}

__device__ __forceinline__ int get_block_n(int M, int N, int K) {
    if (N <= 1024) return 64;
    if (N <= 2048) return 128;
    return 256;
}

__device__ __forceinline__ int get_block_k(int K) {
    return (K >= 2048) ? 256 : 128;
}

constexpr float FP4_MAX = 6.0f;

// ─── FP4 Quantization ─────────────────────────────────────────────────────────
__device__ __forceinline__ void quantize_bf16_to_fp4(
    hip_bfloat16 val,
    uint8_t& scale_exp,
    uint8_t& fp4_val
) {
    float f = __bfloat162float(val);
    float abs_f = fabsf(f);
    
    if (abs_f > 0.0f) {
        uint32_t bits = __float_as_uint(abs_f);
        uint32_t rounded = (bits + 0x200000u) & 0xFF800000u;
        int exp_biased = (rounded >> 23) & 0xFF;
        scale_exp = exp_biased - 2;
        
        float quant_scale = exp2f(129.0f - (float)scale_exp);
        float qx = abs_f * quant_scale;
        
        if (qx >= FP4_MAX) {
            fp4_val = 0x7;
        } else if (qx < 1.0f) {
            fp4_val = (uint8_t)(qx * 8.0f);
        } else {
            fp4_val = (uint8_t)qx;
        }
        
        if (f < 0.0f) {
            fp4_val |= 0x8;
        }
    }
}

// ─── LDS Swizzle ──────────────────────────────────────────────────────────────
__device__ __forceinline__ int swizzle_col(int row, int col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    const int mask = perm << 4;
    return col ^ mask;
}

// ─── Scheduling ───────────────────────────────────────────────────────────────
__device__ __forceinline__ void wave_barrier() {
    __builtin_amdgcn_s_barrier();
}

__device__ __forceinline__ void set_priority(int prio) {
    __builtin_amdgcn_s_setprio(prio);
}

__device__ __forceinline__ float unpack_fp4(uint8_t val) {
    float sign = ((val >> 3) & 0x1) ? -1.0f : 1.0f;
    float exp = (val >> 2) & 0x1;
    float mant = val & 0x3;
    return exp ? sign * (1.0f + mant * 0.5f) : sign * mant * 0.125f;
}

// ─── Kernel: Shape-Adaptive Tile Tuning ───────────────────────────────────────
__global__ __launch_bounds__(512, 1)
void fused_mxfp4_gemm_v5(
    const hip_bfloat16* A,
    const uint8_t* B_fp4,
    const uint8_t* B_scale,
    hip_bfloat16* C,
    int M, int N, int K
) {
    // Dynamic tile selection
    const int BLOCK_M = get_block_m(M, N, K);
    const int BLOCK_N = get_block_n(M, N, K);
    const int BLOCK_K = get_block_k(K);
    
    __shared__ uint8_t lds_A[2][BLOCK_M * BLOCK_K];
    __shared__ uint8_t lds_B[BLOCK_N * BLOCK_K];
    __shared__ float acc[BLOCK_M * BLOCK_N];
    
    const int tid = threadIdx.x;
    const int wave_id = tid / WARP_SIZE;
    const int lane_id = tid % WARP_SIZE;
    const int wave_m = wave_id / 4;
    const int wave_n = wave_id % 4;
    
    const int m_start = blockIdx.y * BLOCK_M;
    const int n_start = blockIdx.x * BLOCK_N;
    
    for (int i = tid; i < BLOCK_M * BLOCK_N; i += 512) {
        acc[i] = 0.0f;
    }
    __syncthreads();
    
    int tic = 0;
    
    for (int k0 = 0; k0 < K; k0 += BLOCK_K) {
        // Memory waves load LDS with swizzle
        if (wave_id < 4) {
            for (int i = lane_id; i < BLOCK_M * BLOCK_K; i += WARP_SIZE) {
                int row = i / BLOCK_K;
                int col = i % BLOCK_K;
                int m_idx = m_start + row;
                int k_idx = k0 + col;
                
                if (m_idx < M && k_idx < K) {
                    uint8_t scale_exp, fp4_val;
                    quantize_bf16_to_fp4(A[m_idx * K + k_idx], scale_exp, fp4_val);
                    int swizzled = swizzle_col(row, col);
                    lds_A[tic][row * BLOCK_K + swizzled] = fp4_val;
                }
            }
            
            for (int i = lane_id; i < BLOCK_N * BLOCK_K; i += WARP_SIZE) {
                int row = i / BLOCK_K;
                int col = i % BLOCK_K;
                int n_idx = n_start + row;
                int k_idx = k0 + col;
                
                if (n_idx < N && k_idx < K) {
                    int fp4_idx = (n_idx * (K/2)) + (k_idx / 2);
                    uint8_t packed = B_fp4[fp4_idx];
                    uint8_t fp4_val = (k_idx % 2 == 0) ? (packed & 0x0F) : (packed >> 4);
                    int swizzled = swizzle_col(row, col);
                    lds_B[row * BLOCK_K + swizzled] = fp4_val;
                }
            }
        }
        
        __syncthreads();
        
        // Compute waves MFMA
        if (wave_id >= 4) {
            float c_frag[4] = {0};
            set_priority(1);
            
            for (int k_frag = 0; k_frag < BLOCK_K / 128; k_frag++) {
                int a_row = wave_m * 16 + lane_id;
                int a_col = k_frag * 128;
                int swizzled_a = swizzle_col(a_row, a_col);
                uint8_t a_val = lds_A[tic][a_row * BLOCK_K + swizzled_a];
                
                int b_row = wave_n * 16 + lane_id;
                int b_col = k_frag * 128;
                int swizzled_b = swizzle_col(b_row, b_col);
                uint8_t b_val = lds_B[b_row * BLOCK_K + swizzled_b];
                
                c_frag[0] += unpack_fp4(a_val) * unpack_fp4(b_val);
                wave_barrier();
            }
            
            set_priority(0);
            
            for (int i = 0; i < 4; i++) {
                int m_out = m_start + (wave_m * 16) + (i * 4);
                int n_out = n_start + (wave_n * 16) + lane_id;
                if (m_out < M && n_out < N) {
                    atomicAdd(&acc[(m_out - m_start) * BLOCK_N + (n_out - n_start)], c_frag[i]);
                }
            }
        }
        
        tic ^= 1;
        wave_barrier();
    }
    
    for (int i = tid; i < BLOCK_M * BLOCK_N; i += 512) {
        int m_out = m_start + (i / BLOCK_N);
        int n_out = n_start + (i % BLOCK_N);
        if (m_out < M && n_out < N) {
            C[m_out * N + n_out] = __float2bfloat16(acc[i]);
        }
    }
}
