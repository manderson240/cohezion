#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define QK_DIM 576
#define V_DIM 512
#define BLOCK_N 64
#define WAVE_SIZE 64

__constant__ float FP4_LUT[16] = {
    0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
   -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
};

__device__ __forceinline__ float d_fp4(unsigned char v, unsigned char s) {
    return FP4_LUT[v] * __uint_as_float((unsigned int)s << 23);
}

__device__ __forceinline__ float wave_max(float val) {
    for (int offset = WAVE_SIZE / 2; offset > 0; offset /= 2)
        val = fmaxf(val, __shfl_xor(val, offset, WAVE_SIZE));
    return val;
}

__device__ __forceinline__ float wave_sum(float val) {
    for (int offset = WAVE_SIZE / 2; offset > 0; offset /= 2)
        val += __shfl_xor(val, offset, WAVE_SIZE);
    return val;
}

// Fused MLA Decode: Persistent Kernel + Wave Shuffle + MXFP4 LUT
__global__ void mla_top10_kernel(
    const __hip_bfloat16* __restrict__ Q,      // [bs, nh, 576]
    const uint8_t* __restrict__ KV,            // [bs, sl, 288]
    const uint8_t* __restrict__ KS,            // [bs, sl, 24]
    __hip_bfloat16* __restrict__ O,            // [bs, nh, 512]
    int bs, int sl, int nh, float sc) 
{
    int hi = blockIdx.x, bi = blockIdx.y, tid = threadIdx.x;
    const __hip_bfloat16* qp = Q + (bi * nh + hi) * QK_DIM;
    const uint8_t* kvp = KV + bi * sl * 288;
    const uint8_t* ksp = KS + bi * sl * 24;
    __hip_bfloat16* op = O + (bi * nh + hi) * V_DIM;

    // Load Q once into shared memory per head
    __shared__ float sq[QK_DIM];
    for (int i = tid; i < QK_DIM; i += blockDim.x) 
        sq[i] = __bfloat162float(qp[i]);
    __syncthreads();

    float running_max = -1e30f, running_sum = 0.0f;
    float local_v[8] = {0.0f}; // V_DIM (512) / BLOCK_SIZE (64) = 8 elements per thread

    for (int k = 0; k < sl; k += BLOCK_N) {
        int remain = sl - k;
        int current_n = (remain < BLOCK_N) ? remain : BLOCK_N;

        // QK Dot Product (Score Calculation)
        float score = -1e30f;
        if (tid < current_n) {
            const uint8_t* kf = kvp + (k + tid) * 288;
            const uint8_t* ks = ksp + (k + tid) * 24;
            float acc = 0.0f;
            for (int g = 0; g < 18; g++) { // 576 / 32 groups
                uint8_t sv = ks[g];
                for (int i = 0; i < 16; i++) { // 32 / 2 elements per byte
                    uint8_t p = kf[g * 16 + i];
                    acc += sq[g * 32 + i * 2] * d_fp4(p & 0xF, sv);
                    acc += sq[g * 32 + i * 2 + 1] * d_fp4(p >> 4, sv);
                }
            }
            score = acc * sc;
        }

        // Online Softmax
        float block_max = wave_max(score);
        float old_max = running_max;
        running_max = fmaxf(old_max, block_max);
        
        float p = expf(score - running_max);
        float correction = expf(old_max - running_max);
        
        running_sum = running_sum * correction + wave_sum(tid < current_n ? p : 0.0f);

        // V Accumulation
        // V is the first 512 dims of the same KV cache
        for (int i = 0; i < 8; i++) {
            int v_dim_idx = tid + i * 64;
            local_v[i] *= correction;
            
            // Broadcast weight 'p' to all threads to multiply with their V slice
            for (int j = 0; j < current_n; j++) {
                float weight = __shfl(p, j, WAVE_SIZE);
                const uint8_t* kv_j = kvp + (k + j) * 288;
                const uint8_t* ks_j = ksp + (k + j) * 24;
                
                uint8_t sv = ks_j[v_dim_idx / 32];
                uint8_t pv = kv_j[(v_dim_idx / 32) * 16 + (v_dim_idx % 32) / 2];
                float v_val = (v_dim_idx % 2) ? d_fp4(pv >> 4, sv) : d_fp4(pv & 0xF, sv);
                local_v[i] += weight * v_val;
            }
        }
    }

    // Finalize and write output
    float inv_sum = 1.0f / running_sum;
    for (int i = 0; i < 8; i++) {
        int v_dim_idx = tid + i * 64;
        op[v_dim_idx] = __float2bfloat16(local_v[i] * inv_sum);
    }
}

extern "C" int launch_mla_top10(
    void* Q, void* KV, void* KS, void* O,
    int bs, int sl, int nh, float sc) 
{
    dim3 grid(nh, bs), block(64);
    hipLaunchKernelGGL(mla_top10_kernel, grid, block, 0, 0,
        (const __hip_bfloat16*)Q, (const uint8_t*)KV, (const uint8_t*)KS, (__hip_bfloat16*)O,
        bs, sl, nh, sc);
    return 0;
}
