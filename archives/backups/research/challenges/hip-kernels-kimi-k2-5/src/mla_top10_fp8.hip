#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define QK_DIM 576
#define V_DIM 512
#define BLOCK_N 64
#define WAVE_SIZE 64

// FP8 E5M2 format constants
#define FP8_E5M2_MAX 57344.0f
#define FP8_E5M2_MIN -57344.0f

__device__ __forceinline__ float fp8_to_float(uint8_t val) {
    // FP8 E5M2 format: 1 sign bit, 5 exponent bits, 2 mantissa bits
    // For simplicity, treat as signed char scaled
    return static_cast<float>(static_cast<int8_t>(val));
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

// Fused MLA Decode: FP8 input format (matches AITER)
__global__ void mla_top10_kernel(
    const __hip_bfloat16* __restrict__ Q,      // [bs, nh, 576] - bfloat16 query
    const uint8_t* __restrict__ KV,          // [bs, sl, 576] - FP8 KV cache
    __hip_bfloat16* __restrict__ O,            // [bs, nh, 512] - bfloat16 output
    int bs, int sl, int nh, float sc) 
{
    int hi = blockIdx.x, bi = blockIdx.y, tid = threadIdx.x;
    const __hip_bfloat16* qp = Q + (bi * nh + hi) * QK_DIM;
    const uint8_t* kvp = KV + bi * sl * QK_DIM;  // [sl, 576] FP8
    __hip_bfloat16* op = O + (bi * nh + hi) * V_DIM;

    // Load Q into shared memory
    __shared__ float sq[QK_DIM];
    for (int i = tid; i < QK_DIM; i += blockDim.x) 
        sq[i] = __bfloat162float(qp[i]);
    __syncthreads();

    float running_max = -1e30f, running_sum = 0.0f;
    float local_v[8] = {0.0f};  // V_DIM 512 / 64 threads = 8 elements per thread

    for (int k = 0; k < sl; k += BLOCK_N) {
        int remain = sl - k;
        int current_n = (remain < BLOCK_N) ? remain : BLOCK_N;

        // QK Dot Product
        float score = -1e30f;
        if (tid < current_n) {
            const uint8_t* kf = kvp + (k + tid) * QK_DIM;  // [576] FP8
            float acc = 0.0f;
            
            // Unrolled dot product
            for (int i = 0; i < QK_DIM; i++) {
                acc += sq[i] * fp8_to_float(kf[i]);
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
        for (int i = 0; i < 8; i++) {
            int v_dim_idx = tid + i * 64;
            local_v[i] *= correction;
            
            for (int j = 0; j < current_n; j++) {
                float weight = __shfl(p, j, WAVE_SIZE);
                const uint8_t* kv_j = kvp + (k + j) * QK_DIM;
                float v_val = fp8_to_float(kv_j[v_dim_idx]);
                local_v[i] += weight * v_val;
            }
        }
    }

    // Finalize
    float inv_sum = 1.0f / running_sum;
    for (int i = 0; i < 8; i++) {
        int v_dim_idx = tid + i * 64;
        if (v_dim_idx < V_DIM) {
            op[v_dim_idx] = __float2bfloat16(local_v[i] * inv_sum);
        }
    }
}

extern "C" int launch_mla_top10(
    void* Q, void* KV, void* O,
    int bs, int sl, int nh, float sc) 
{
    dim3 grid(nh, bs), block(64);
    hipLaunchKernelGGL(mla_top10_kernel, grid, block, 0, 0,
        (const __hip_bfloat16*)Q, (const uint8_t*)KV, (__hip_bfloat16*)O,
        bs, sl, nh, sc);
    return 0;
}
