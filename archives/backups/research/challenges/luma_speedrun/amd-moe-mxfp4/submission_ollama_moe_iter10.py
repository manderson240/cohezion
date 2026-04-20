#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) inference. The current submission achieves 154.2µs and the target [K
is <110µs, with the best rank at 70.5µs. 

Let me analyze the current state:
1. Current code uses `fused_moe` from `aiter` with shape-aware KSPLIT
2. The issue mentions MFMA 32x32x64 FP4 intrinsic is working
3. B_q is standard FP4 packed, B_shuffle is CK-specific format
4. Need to load inline HIP kernels that compile and run
5. The constraints mention: "aiter API parameters (KSPLIT, block_size) are [K
EXHAUSTED" - meaning we can't just tune those anymore, need to go lower lev[3D[K
level with inline HIP kernels.

The prompt asks for ONE specific optimization from the list:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Given the context of MI355X (CDNA4) and MFMA 32x32x64 FP4, and the fact tha[3D[K
that we need significant speedup (154µs -> 110µs or better), I should imple[5D[K
implement an inline HIP kernel.

The most impactful optimization for tiny GEMMs (which are mentioned as the [K
problem - "tiny GEMMs" with M=4,8,16 etc) would be:
- Shape-specialized dispatch with proper tile sizes
- Vectorized loads (128-bit)
- LDS double buffering
- MFMA 32x32x64 for FP4

Since the current code is using high-level `fused_moe`, and we need to inje[4D[K
inject inline HIP code, I need to write a custom kernel that handles the Mo[2D[K
MoE logic directly using HIP inline assembly or inline kernel.

Given that MFMA 32x32x64 is mentioned as verified working for FP4, and the [K
shapes include very small M (bs=16 with topk=8 means M could be as small as[2D[K
as 1-2 tokens per expert on average), we need:
1. Special handling for small M (M=4, 16, etc.) vs larger M
2. Vectorized 128-bit loads to maximize bandwidth
3. Double buffering to hide latency
4. XCD-aware scheduling (MI355X has 8 XCDs)

Actually, looking at the constraints more carefully: "aiter API parameters [K
(KSPLIT, block_size) are EXHAUSTED" - this suggests we cannot get more gain[4D[K
gains from tuning those parameters, so we need a custom HIP kernel.

Let me propose a solution that combines:
- Shape-specialized dispatch with custom tile sizes
- Vectorized 128-bit loads
- XCD-aware scheduling
- MFMA 32x32x64 for FP4 computation

The kernel needs to handle:
- FP4 weights (packed)
- FP16/BF16 activations
- Top-k routing
- Two GEMMs: hidden -> intermediate (gate_up), then intermediate -> hidden [K
(down)

Given the small sizes mentioned (d_expert=256, n_routed=256, bs=16), we hav[3D[K
have tiny GEMMs where M is small.

For MI355X (CDNA4), we have:
- Wave32 mode
- MFMA 32x32x64 for FP4
- LDS capacity is larger than previous gen

Let me write a custom HIP kernel that gets loaded inline. The kernel should[6D[K
should:
1. Use 128-bit vector loads for weights (since FP4, we can load 32 elements[8D[K
elements per thread)
2. Use double buffering in LDS
3. Use shape-specific dispatch
4. Set priorities for XCD-aware scheduling

Actually, given the complexity of MoE kernels, I'll focus on a specific opt[3D[K
optimization: **Shape-specialized dispatch with vectorized 128-bit loads an[2D[K
and XCD-aware scheduling**.

The code structure should:
1. Keep the high-level structure
2. Add a custom Triton-like or HIP kernel for the critical path
3. Use `torch.utils.cpp_extension.load_inline` or similar to compile HIP co[2D[K
code

Wait, the prompt says "load_inline HIP kernels COMPILE AND RUN on the runne[5D[K
runner", so I need to provide the full submission.py with inline HIP kernel[6D[K
kernel loading.

Let me write a kernel that specializes for the small M cases (which are the[3D[K
the bottleneck) using MFMA instructions and proper vectorization.

For FP4 MFMA 32x32x64:
- A matrix: 32x64 FP16/BF16
- B matrix: 64x32 FP4 (packed as 64x8 bytes effectively, or specific layout[6D[K
layout)
- C matrix: 32x32 FP32

But B is in FP4, so we need to handle the packing.

Actually, looking at the existing code, it uses `aiter` library's `fused_mo[9D[K
`fused_moe` with shuffled weights. The shuffled format is likely the CK (Co[3D[K
(Composed Kernel) specific format for FP4.

For a custom kernel to beat the aiter implementation, I need to:
1. Handle the small M cases (M=4,8,16) efficiently - these are memory bound[5D[K
bound
2. Use vectorized loads (128-bit)
3. Use LDS double buffering
4. Use XCD-aware scheduling

Let me write a kernel that uses these techniques. Since the prompt asks for[3D[K
for ONE specific optimization, I'll focus on **Shape-specialized dispatch w[1D[K
with vectorized 128-bit loads and XCD-aware scheduling for the tiny GEMM ca[2D[K
cases**.

The kernel will be written in HIP and loaded via `load_inline`.

Structure:
- Detect if we're in a tiny shape (M <= 64 or specific d_expert)
- Dispatch to custom kernel for those cases
- Use 128-bit loads (float4 or uint4)
- Use __builtin_amdgcn_s_setprio for XCD scheduling
- Use double buffering

Actually, for MI355X and the specific constraints, I think the best optimiz[7D[K
optimization is to implement a specialized kernel for the small M cases tha[3D[K
that uses:
1. Vectorized 128-bit global loads (4x FP32 or 8x FP16 at once)
2. MFMA 32x32x64 for the compute
3. Software pipelining with double buffering
4. XCD-aware wave scheduling

Let me write the code:

```python
import torch
from torch.utils.cpp_extension import load_inline

# Define the HIP kernel
hip_code = '''
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bf16.h>

// FP4 packing helpers
typedef unsigned char uchar;
typedef unsigned int uint;
typedef unsigned long long uint64_t;

// MFMA intrinsic for FP4
// CDNA4 supports mfma_f32_32x32x64_f16 or specialized FP4 variants
// Actually, for FP4 we use mfma_scale_f32_32x32x64_f8f6f4 or similar
// But since the prompt says MFMA 32x32x64 FP4 is verified, let's use the r[1D[K
right intrinsic

// For MI355X CDNA4: mfma_f32_32x32x64_fp4_fp4
// Syntax: dst[8] = mfma_f32_32x32x64_fp4_fp4(a[2], b[2], c[8], cbsz, abid,[5D[K
abid, blgp)
// where a is 32x64 FP4 (packed), b is 64x32 FP4 (packed)

extern "C" __device__ __attribute__((const)) float4 __builtin_amdgcn_mfma_f[23D[K
__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4(
    uint64_t a, uint64_t b, float4 c, int cbsz, int abid, int blgp);

// XCD scheduling
extern "C" __device__ void __builtin_amdgcn_s_setprio(int);

// Vector types
typedef __attribute__((ext_vector_type(4))) float float4_vec;
typedef __attribute__((ext_vector_type(2))) uint uint2;
typedef __attribute__((ext_vector_type(4))) uint uint4;
typedef __attribute__((ext_vector_type(8))) ushort ushort8;
typedef __attribute__((ext_vector_type(4))) ushort ushort4;

// Double buffer state
template<int N>
struct DoubleBuffer {
    float* data[2];
    int toggle;
    
    __device__ __forceinline__ float* read() { return data[toggle]; }
    __device__ __forceinline__ float* write() { return data[toggle ^ 1]; }
    __device__ __forceinline__ void swap() { toggle ^= 1; }
};

// Main kernel for small M MoE with FP4
// Specialized for M in [4, 16, 32, 64]
template <int BM, int BN, int BK, int NUM_WARPS>
__global__ __attribute__((amdgpu_num_vgpr(64))) __attribute__((amdgpu_num_s[27D[K
__attribute__((amdgpu_num_sgpr(32)))
void moe_small_gemm_fp4_kernel(
    const at::Half* __restrict__ A,  // [M, K] FP16
    const uchar* __restrict__ B,     // [K/2, N] FP4 packed (2 nibbles per [K
byte)
    at::Half* __restrict__ C,        // [M, N] FP16
    const float* __restrict__ w_scale, // [N] scale per 32 channels
    int M, int N, int K,
    int stride_a_m, int stride_a_k,
    int stride_b_k, int stride_b_n,
    int stride_c_m, int stride_c_n) {
    
    // XCD-aware scheduling: set priority based on XCD
    int xcd_id = blockIdx.x % 8; // Assuming 8 XCDs
    __builtin_amdgcn_s_setprio(xcd_id < 4 ? 1 : 0);
    
    // Warp organization: each warp handles 32x32 output
    int warp_id = threadIdx.x / 32;
    int lane_id = threadIdx.x % 32;
    
    // Cooperative tile loading
    int m_tile = blockIdx.y * BM;
    int n_tile = blockIdx.x * BN;
    
    // LDS allocation for double buffering
    __shared__ __attribute__((aligned(128))) float lds_a[2][BM * BK]; // Do[2D[K
Double buffered
    __shared__ __attribute__((aligned(128))) uchar lds_b[2][BK * BN / 2]; /[1D[K
// FP4 packed
    
    // Accumulators in registers for MFMA
    // For 32x32x64: each thread holds 8 floats
    float accum[8] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
    
    // Loop over K with double buffering
    int num_k_tiles = (K + BK - 1) / BK;
    
    // Preload first tile
    // Vectorized 128-bit loads (4 uints = 128 bits)
    #pragma unroll
    for (int i = threadIdx.x; i < BM * BK / 8; i += blockDim.x) {
        // Load A tile: BM x BK FP16 -> 128-bit vectors
        int row = i / (BK / 8);
        int col = (i % (BK / 8)) * 8;
        int g_row = m_tile + row;
        int g_col = 0 * BK + col; // First K tile
        
        if (g_row < M && g_col < K) {
            // Load 8 FP16 = 128 bits
            uint4 data = *(const uint4*)(A + g_row * stride_a_m + g_col * s[1D[K
stride_a_k);
            *(uint4*)&lds_a[0][row * BK + col] = data;
        } else {
            *(uint4*)&lds_a[0][row * BK + col] = make_uint4(0, 0, 0, 0);
        }
    }
    
    #pragma unroll
    for (int i = threadIdx.x; i < BK * BN / 2 / 16; i += blockDim.x) {
        // Load B tile: BK x BN FP4 packed -> 128-bit vectors (16 bytes)
        int row = i / (BN / 32);
        int col = (i % (BN / 32)) * 32; // 32 nibbles = 16 bytes
        int g_row = 0 * BK + row;
        int g_col = n_tile + col;
        
        if (g_row < K/2 && g_col < N) {
            uint4 data = *(const uint4*)(B + g_row * stride_b_k + g_col / 2[1D[K
2);
            *(uint4*)&lds_b[0][row * BN / 2 + col / 2] = data;
        } else {
            *(uint4*)&lds_b[0][row * BN / 2 + col / 2] = make_uint4(0, 0, 0[1D[K
0, 0);
        }
    }
    
    __syncthreads();
    
    int buf_idx = 0;
    
    // Main loop
    for (int kt = 0; kt < num_k_tiles; ++kt) {
        int next_kt = kt + 1;
        bool has_next = next_kt < num_k_tiles;
        
        // Compute current tile using MFMA
        // Each warp computes 32x32
        // For FP4 MFMA: we need to load A and B in specific format
        
        // Load A from LDS (FP16 -> need to convert or use directly)
        // For MFMA 32x32x64 FP4: A is 32x64 FP4, but we have FP16 input
        // Actually, we need to quantize on the fly or load quantized
        
        // Wait, the activation A is FP16, weights B is FP4
        // The MFMA does FP4 x FP4 -> FP32, or mixed?
        // CDNA4 supports mixed: FP16 x FP4 -> FP32 via mfma
        
        // Actually, let's use the correct MFMA for mixed precision
        // mfma_f32_32x32x64_f16_f4 or similar extension
        
        // For now, simplified: process 64 K dim per step
        #pragma unroll
        for (int k_step = 0; k_step < BK; k_step += 64) {
            // Load A fragment: 2 uint64_t for 32x64 FP4 (but A is FP16, ne[2D[K
need conversion)
            // Actually, we should keep A in FP16 and use FP16xFP4 MFMA if [K
available
            // Or quantize A to FP4 on the fly (expensive)
            
            // Alternative: use existing MFMA path but optimized
            uint64_t a_frag = *(uint64_t*)&lds_a[buf_idx][warp_id * 32 * BK[2D[K
BK + k_step + lane_id * 2];
            uint64_t b_frag = *(uint64_t*)&lds_b[buf_idx][k_step * BN / 2 +[1D[K
+ (warp_id % 4) * 32];
            
            // MFMA call
            float4 c_frag = make_float4(accum[0], accum[1], accum[2], accum[5D[K
accum[3]);
            float4 result = __builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4(
                a_frag, b_frag, c_frag, 0, 0, 0);
            accum[0] = result.x; accum[1] = result.y; accum[2] = result.z; [K
accum[3] = result.w;
            
            float4 c_frag2 = make_float4(accum[4], accum[5], accum[6], accu[4D[K
accum[7]);
            float4 result2 = __builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4(
                a_frag, b_frag, c_frag2, 0, 0, 0);
            accum[4] = result2.x; accum[5] = result2.y; accum[6] = result2.[8D[K
result2.z; accum[7] = result2.w;
        }
        
        // Load next tile while computing
        if (has_next) {
            __syncthreads();
            int next_buf = buf_idx ^ 1;
            
            // Vectorized load of next A tile
            #pragma unroll
            for (int i = threadIdx.x; i < BM * BK / 8; i += blockDim.x) {
                int row = i / (BK / 8);
                int col = (i % (BK / 8)) * 8;
                int g_row = m_tile + row;
                int g_col = next_kt * BK + col;
                
                if (g_row < M && g_col < K) {
                    uint4 data = *(const uint4*)(A + g_row * stride_a_m + g[1D[K
g_col * stride_a_k);
                    *(uint4*)&lds_a[next_buf][row * BK + col] = data;
                }
            }
            
            // Vectorized load of next B tile
            #pragma unroll
            for (int i = threadIdx.x; i < BK * BN / 2 / 16; i += blockDim.x[10D[K
blockDim.x) {
                int row = i / (BN / 32);
                int col = (i % (BN / 32)) * 32;
                int g_row = next_kt * BK + row;
                int g_col = n_tile + col;
                
                if (g_row < K/2 && g_col < N) {
                    uint4 data = *(const uint4*)(B + g_row * stride_b_k + g[1D[K
g_col / 2);
                    *(uint4*)&lds_b[next_buf][row * BN / 2 + col / 2] = dat[3D[K
data;
                }
            }
            buf_idx = next_buf;
        }
        
        __syncthreads();
    }
    
    // Store output with vectorized writes
    // Apply scales and convert to FP16
    #pragma unroll
    for (int i = 0; i < 8; ++i) {
        int local_row = (warp_id / 2) * 16 + (i / 4) * 8 + (lane_id / 4);
        int local_col = (warp_id % 2) * 16 + (i % 4) * 4 + (lane_id % 4);
        
        if (m_tile + local_row < M && n_tile + local_col < N) {
            float val = accum[i] * w_scale[n_tile + local_col];
            C[(m_tile + local_row) * stride_c_m + (n_tile + local_col) * st[2D[K
stride_c_n] = __float2half(val);
        }
    }
}

// Wrapper to dispatch based on shape
torch::Tensor moe_gemm_fp4_dispatch(torch::Tensor A, torch::Tensor B, torch[5D[K
torch::Tensor scales, int M, int N, int K) {
    auto C = torch::empty({M, N}, A.options());
    
    dim3 blocks;
    dim3 threads(256); // 8 warps
    
    if (M <= 16) {
        // Very small M: use 4x32 tile
        blocks = dim3((N + 32 - 1) / 32, (M + 4 - 1) / 4);
        moe_small_gemm_fp4_kernel<4, 32, 64, 8><<<blocks, threads>>>(
            A.data_ptr<at::Half>(), 
            (const uchar*)B.data_ptr(),
            C.data_ptr<at::Half>(),
            scales.data_ptr<float>(),
            M, N, K,
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            C.stride(0), C.stride(1));
    } else if (M <= 64) {
        // Medium M: use 16x64 tile  
        blocks = dim3((N + 64 - 1) / 64, (M + 16 - 1) / 16);
        moe_small_gemm_fp4_kernel<16, 64, 64, 8><<<blocks, threads>>>(
            A.data_ptr<at::Half>(),
            (const uchar*)B.data_ptr(),
            C.data_ptr<at::Half>(),
            scales.data_ptr<float>(),
            M, N, K,
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            C.stride(0), C.stride(1));
    } else {
        // Large M: use 32x128 tile
        blocks = dim3((N + 128 - 1) / 128, (M + 32 - 1) / 32);
        moe_small_gemm_fp4_kernel<32, 128, 64, 8><<<blocks, threads>>>(
            A.data_ptr<at::Half>(),
            (const uchar*)B.data_ptr(),
            C.data_ptr<at::Half>(),
            scales.data_ptr<float>(),
            M, N, K,
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            C.stride(0), C.stride(1));
    }
    
    return C;
}
'''

# Then load it
```

Wait, I need to be careful. The MFMA 32x32x64 for FP4 expects FP4 inputs, b[1D[K
but activations are FP16. We need to either:
1. Convert FP16 to FP4 on the fly (lossy but fast with lookup)
2. Use mixed precision MFMA if available (FP16 x FP4)

For MI355X/CDNA4, there should be support for mixed precision MFMA. Let me [K
adjust the kernel to use the correct intrinsic.

Actually, looking at the constraints again, the user says "MFMA 32x32x64 FP[2D[K
FP4 intrinsic is VERIFIED working". This suggests the intrinsic is availabl[8D[K
available.

For the inline kernel approach to work, I need to use `torch.utils.cpp_exte[21D[K
`torch.utils.cpp_extension.load_inline`.

Let me reconsider the optimization strategy. The current best is 154µs, tar[3D[K
target is 110µs, rank 1 is 70µs. The gap is significant. The main issue is [K
the tiny GEMMs (M=4,8,16).

For tiny GEMMs on GPU:
- Overhead of kernel launch is high
- Memory coalescing is poor
- We need to fuse everything and use vectorized loads

The best optimization would be:
1. **Shape-specialized dispatch** with inline assembly for the critical pat[3D[K
path
2. **Vectorized 128-bit loads** to maximize memory bandwidth
3. **XCD-aware scheduling** to ensure even distribution across XCDs

I will write a kernel that:
- Uses `__builtin_amdgcn_s_setprio` for XCD load balancing
- Uses `uint4` (128-bit) vector loads for weights
- Uses shape-specific tile sizes (M=4, M=16, M=64, etc.)
- Double buffers in LDS

Let me refine the HIP code to be compilable and correct:

```python
hip_source = """
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>

typedef __attribute__((ext_vector_type(4))) unsigned int uint4_vec;
typedef __attribute__((ext_vector_type(4))) float float4_vec;

// MFMA FP4 intrinsic (32x32x64)
extern "C" __device__ __attribute__((const)) float4_vec __builtin_amdgcn_mf[19D[K
__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4(
    unsigned long long a, unsigned long long b, float4_vec c, int cbsz, int[3D[K
int abid, int blgp);

__device__ __forceinline__ uint4_vec load_global128(const void* addr) {
    return *(const uint4_vec*)addr;
}

__device__ __forceinline__ void store_global128(void* addr, uint4_vec val) [K
{
    *(uint4_vec*)addr = val;
}

template<int TM, int TN, int TK>
__global__ __launch_bounds__(256, 2) void moe_gemm_small_fp4(
    const at::Half* __restrict__ A,
    const uint8_t* __restrict__ B,
    at::Half* __restrict__ C,
    const float* __restrict__ scales,
    int M, int N, int K,
    int num_experts, int topk) {
    
    // XCD-aware priority setting (8 XCDs on MI355X)
    int xcd_id = blockIdx.x % 8;
    __builtin_amdgcn_s_setprio(xcd_id < 4 ? 1 : 0);
    
    int m_tile = blockIdx.y * TM;
    int n_tile = blockIdx.x * TN;
    
    // LDS double buffer: 2 * TM * TK for A, 2 * TK * TN/2 for B (FP4)
    extern __shared__ uint8_t smem[];
    at::Half* lds_a[2] = {(at::Half*)smem, (at::Half*)(smem + TM * TK * siz[3D[K
sizeof(at::Half))};
    uint8_t* lds_b[2] = {
        smem + 2 * TM * TK * sizeof(at::Half),
        smem + 2 * TM * TK * sizeof(at::Half) + TK * TN / 2
    };
    
    int tid = threadIdx.x;
    int wid = tid / 32;
    int lid = tid % 32;
    
    float accum[8] = {0};
    
    int n_k_tiles = (K + TK - 1) / TK;
    
    // Preload first tile with vectorized 128-bit loads
    for (int i = tid; i < TM * TK / 8; i += blockDim.x) {
        int row = i / (TK / 8);
        int col = (i % (TK / 8)) * 8;
        int g_m = m_tile + row;
        int g_k = col;
        
        if (g_m < M) {
            uint4_vec val = load_global128(&A[g_m * K + g_k]);
            *(uint4_vec*)&lds_a[0][row * TK + col] = val;
        }
    }
    
    for (int i = tid; i < TK * TN / 2 / 16; i += blockDim.x) {
        int row = i / (TN / 32);
        int col = (i % (TN / 32)) * 32;
        int g_k = row;
        int g_n = n_tile + col;
        
        if (g_k < K && g_n < N) {
            uint4_vec val = load_global128(&B[g_k * N + g_n]);
            *(uint4_vec*)&lds_b[0][row * TN / 2 + col / 2] = val;
        }
    }
    
    __syncthreads();
    
    int buf = 0;
    
    #pragma unroll 2
    for (int kt = 0; kt < n_k_tiles; ++kt) {
        int g_k_base = kt * TK;
        
        // Compute tile
        #pragma unroll
        for (int k = 0; k < TK; k += 64) {
            // Load A fragment (convert from FP16 to FP4 on-the-fly or use [K
FP16)
            // For now, assume we have a path
            
            // Each thread loads for MFMA
            unsigned long long a_frag = 0; // Pack from LDS
            unsigned long long b_frag = 0; // Pack from LDS
            
            // Call MFMA
            float4_vec c_old = {accum[0], accum[1], accum[2], accum[3]};
            float4_vec c_new = __builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4(
                a_frag, b_frag, c_old, 0, 0, 0);
            accum[0] = c_new.x; accum[1] = c_new.y; accum[2] = c_new.z; acc[3D[K
accum[3] = c_new.w;
        }
        
        // Load next tile
        if (kt + 1 < n_k_tiles) {
            __syncthreads();
            int next_buf = buf ^ 1;
            int next_k = (kt + 1) * TK;
            
            for (int i = tid; i < TM * TK / 8; i += blockDim.x) {
                int row = i / (TK / 8);
                int col = (i % (TK / 8)) * 8;
                int g_m = m_tile + row;
                
                if (g_m < M) {
                    uint4_vec val = load_global128(&A[g_m * K + next_k + co[2D[K
col]);
                    *(uint4_vec*)&lds_a[next_buf][row * TK + col] = val;
                }
            }
            
            for (int i = tid; i < TK * TN / 2 / 16; i += blockDim.x) {
                int row = i / (TN / 32);
                int col = (i % (TN / 32)) * 32;
                
                if (next_k + row < K && n_tile + col < N) {
                    uint4_vec val = load_global128(&B[(next_k + row) * N + [K
n_tile + col]);
                    *(uint4_vec*)&lds_b[next_buf][row * TN / 2 + col / 2] =[1D[K
= val;
                }
            }
            buf = next_buf;
        }
        __syncthreads();
    }
    
    // Store with vectorized 128-bit
    for (int i = tid; i < TM * TN / 8; i += blockDim.x) {
        int row = i / (TN / 8);
        int col = (i % (TN / 8)) * 8;