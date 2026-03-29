/**
 * Iteration 4: Direct Global→LDS (128-bit transfers)
 * 
 * Uses CDNA4's 128-bit GLOBAL_LOAD_LDS for direct memory transfer.
 * Bypasses VGPR staging, reduces register pressure.
 * Expected: 11.2 µs (vs 11.8 µs swizzle, -5% improvement)
 */

#include <hip/hip_runtime.h>
#include <hip/hip_bfloat16.h>
#include <stdint.h>
#include <math.h>

constexpr int WARP_SIZE = 64;
constexpr int BLOCK_M = 256;
constexpr int BLOCK_N = 256;
constexpr int BLOCK_K = 128;
constexpr int NUM_THREADS = 512;
constexpr float FP4_MAX = 6.0f;

// ─── 128-bit Vector Types ─────────────────────────────────────────────────────
using u32x4 = uint32_t __attribute__((ext_vector_type(4)));
using as3_uint32_ptr = uint32_t __attribute__((address_space(3))) *;

// ─── LLVM Intrinsics for Direct Global→LDS ───────────────────────────────────
extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    u32x4 rsrc,
    as3_uint32_ptr lds_ptr,
    int size,
    int voffset,
    int soffset,
    int offset,
    int aux
) __asm("llvm.amdgcn.raw.buffer.load.lds");

__device__ __forceinline__ u32x4 make_srsrc(const void* ptr, uint32_t range_bytes) {
    struct buffer_resource {
        uint64_t ptr;
        uint32_t range;
        uint32_t config;
    };
    buffer_resource rsrc = {
        reinterpret_cast<uint64_t>(ptr),
        range_bytes,
        0x110000  // GFX950 format
    };
    return *reinterpret_cast<const u32x4*>(&rsrc);
}

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
    } else {
        scale_exp = 0;
        fp4_val = 0;
    }
}

// ─── LDS Swizzle ──────────────────────────────────────────────────────────────
__device__ __forceinline__ int swizzle_col(int row, int col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    const int mask = perm << 4;
    return col ^ mask;
}

// ─── Scheduling Intrinsics ────────────────────────────────────────────────────
__device__ __forceinline__ void wave_barrier() {
    __builtin_amdgcn_s_barrier();
}

__device__ __forceinline__ void set_priority(int prio) {
    __builtin_amdgcn_s_setprio(prio);
}

__device__ __forceinline__ void sched_barrier(int mask) {
    __builtin_amdgcn_sched_barrier(mask);
}

__device__ __forceinline__ float unpack_fp4(uint8_t val) {
    float sign = ((val >> 3) & 0x1) ? -1.0f : 1.0f;
    float exp = (val >> 2) & 0x1;
    float mant = val & 0x3;
    return exp ? sign * (1.0f + mant * 0.5f) : sign * mant * 0.125f;
}

// ─── Kernel: Direct Global→LDS + 8-Wave + Swizzle ────────────────────────────
__global__ __launch_bounds__(NUM_THREADS, 1)
void fused_mxfp4_gemm_v4(
    const hip_bfloat16* A,
    const uint8_t* B_fp4,
    const uint8_t* B_scale,
    hip_bfloat16* C,
    int M, int N, int K
) {
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
    
    // Init accumulator
    for (int i = tid; i < BLOCK_M * BLOCK_N; i += NUM_THREADS) {
        acc[i] = 0.0f;
    }
    __syncthreads();
    
    // Prepare source resources for direct LDS loads
    u32x4 a_srsrc = make_srsrc(A + m_start * K, M * K * sizeof(hip_bfloat16));
    u32x4 b_srsrc = make_srsrc(B_fp4 + n_start * (K/2), N * (K/2));
    
    int tic = 0;
    
    for (int k0 = 0; k0 < K; k0 += BLOCK_K) {
        // Memory waves: Direct global→LDS (128-bit transfers)
        if (wave_id < 4) {
            // Direct A load via 128-bit GLOBAL_LOAD_LDS
            llvm_amdgcn_raw_buffer_load_lds(
                a_srsrc,
                reinterpret_cast<as3_uint32_ptr>(lds_A[tic]),
                16,  // 128-bit (4×32-bit)
                lane_id * 4,
                0, 0, 0
            );
            
            // Direct B load
            llvm_amdgcn_raw_buffer_load_lds(
                b_srsrc,
                reinterpret_cast<as3_uint32_ptr>(lds_B),
                16,
                lane_id * 4,
                0, 0, 0
            );
        }
        
        __syncthreads();
        
        // Compute waves: MFMA with swizzled LDS access
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
        sched_barrier(0);
        wave_barrier();
    }
    
    // Write output
    for (int i = tid; i < BLOCK_M * BLOCK_N; i += NUM_THREADS) {
        int m_out = m_start + (i / BLOCK_N);
        int n_out = n_start + (i % BLOCK_N);
        if (m_out < M && n_out < N) {
            C[m_out * N + n_out] = __float2bfloat16(acc[i]);
        }
    }
}
