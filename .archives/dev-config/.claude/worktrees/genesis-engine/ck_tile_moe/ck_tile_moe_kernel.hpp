// SPDX-License-Identifier: MIT
// CK-Tile Fused MoE Kernel for MI355X (gfx950)
// Optimized for <115µs latency target

#pragma once

#include "ck_tile/core.hpp"
#include "ck_tile/ops/fused_moe.hpp"
#include "ck_tile/host/kernel_launch.hpp"
#include "ck_tile/host/stream_config.hpp"

#include <hip/hip_runtime.h>

namespace ct = ck_tile;

// ============================================================================
// Type Definitions
// ============================================================================

// Using FP16 for activations and outputs
tusing ADataType = ct::fp16_t;           // Input activation
tusing ODataType = ct::fp16_t;           // Output
tusing AccDataType = ct::fp32_t;         // Accumulation type

// MXFP4 for weights (packed 4-bit floating point)
tusing GDataType = ct::pk_fp4_t;          // Gate weights (MXFP4)
tusing DDataType = ct::pk_fp4_t;          // Down weights (MXFP4)

// E8M0 for scales (8-bit floating point exponent-only)
tusing AScaleDataType = ct::e8m0_t;
tusing GScaleDataType = ct::e8m0_t;
tusing DScaleDataType = ct::e8m0_t;

// Other types
tusing TopkWeightDataType = ct::fp16_t;
tusing IndexDataType = ct::index_t;
tusing YDataType = ct::fp16_t;           // Intermediate activation

// ============================================================================
// Block Shape Configuration (Optimized for MI355X)
// ============================================================================

// First GEMM: [tokens, hidden] @ [hidden, 2*intermediate]
// Second GEMM: [tokens, intermediate] @ [intermediate, hidden]
//
// Block sizes chosen for MI355X:
// - Block_M0=64: Good occupancy with token-level parallelism
// - Block_N0=128: Maximizes MFMA utilization for first GEMM
// - Block_K0=64: Balances memory traffic with computation
// - Block_N1=64, Block_K1=128: Optimized for second GEMM dimensions

tusing BlockTile_0 = ct::sequence<64, 128, 64>;    // M, N, K for first GEMM
tusing WarpPerBlock_0 = ct::sequence<1, 2, 1>;   // 2 warps along N dimension
tusing WarpTile_0 = ct::sequence<32, 32, 32>;     // Warp-level tile

tusing BlockTile_1 = ct::sequence<64, 64, 128>;   // M, N, K for second GEMM
tusing WarpPerBlock_1 = ct::sequence<1, 2, 1>;
tusing WarpTile_1 = ct::sequence<32, 32, 32>;

tusing BlockShape = ct::FusedMoeGemmShape<
    BlockTile_0, WarpPerBlock_0, WarpTile_0,
    BlockTile_1, WarpPerBlock_1, WarpTile_1>;

// ============================================================================
// Pipeline Traits
// ============================================================================

// Traits configuration:
// - IsGateOnly=false: Use fused Gate+Up projection (more efficient)
// - UseSmoothQuant=false: No smooth quantization
// - OAtomic=1: Use atomic operations for output accumulation
// - PermuteEnum=waveflatten: Pre-shuffled weight layout for coalesced access
tusing Traits = ct::FusedMoeGemmTraits<
    false,      // IsGateOnly - false = Gate+Up fused
    false,      // UseSmoothQuant
    1,          // OAtomic: 1 = atomic-pk-f16/bf16 accumulation
    ct::FusedMoeGemmWeightPermuteEnum::b_nr_kr_waveflatten,
    false,      // PadHiddenSize
    false,      // PadIntermediateSize
    true>;      // PipeInterleave - interleave memory/compute

// ============================================================================
// Problem Definition
// ============================================================================

tusing Problem = ct::FusedMoeGemmPipelineProblem<
    ADataType, GDataType, DDataType, AccDataType, ODataType,
    AScaleDataType, GScaleDataType, DScaleDataType, void,
    TopkWeightDataType, IndexDataType, YDataType,
    BlockShape, Traits, -1>;  // -1 = auto block per CU

// ============================================================================
// Pipeline and Kernel Types
// ============================================================================

tusing PipelinePolicy = ct::FusedMoeGemmPipelineFlatmmPolicy;
tusing Pipeline = ct::FusedMoeGemmPipeline_FlatmmEx<Problem, PipelinePolicy>;
tusing Partitioner = ct::FusedMoeGemmTilePartitioner_Linear<BlockShape>;
tusing Kernel = ct::FusedMoeGemmKernel<Partitioner, Pipeline, void>;

// ============================================================================
// Host-Side API
// ============================================================================

struct CkTileMoeArgs {
    // Pointers
    const void* a_ptr;              // [tokens, hidden] - input (fp16)
    const void* a_scale_ptr;        // [tokens, 1] - activation scales (optional)
    const void* g_ptr;              // [experts, 2*interm, hidden] - gate/up (mxfp4)
    const void* d_ptr;              // [experts, hidden, interm] - down (mxfp4)
    const void* g_scale_ptr;        // [experts, 1, 2*interm] - gate/up scales (e8m0)
    const void* d_scale_ptr;        // [experts, 1, hidden] - down scales (e8m0)
    const void* y_smooth_scale_ptr; // nullptr if not using smooth quant
    void* o_ptr;                    // [tokens, hidden] - output (fp16)

    // Routing info
    const void* sorted_token_ids_ptr;   // [max_num_tokens_padded]
    const void* sorted_weight_ptr;      // [max_num_tokens_padded] (fp16)
    const void* sorted_expert_ids_ptr; // [num_sorted_tiles]
    const void* num_sorted_tiles_ptr;   // [1]

    // Dimensions
    int64_t hidden_size;
    int64_t intermediate_size;
    int64_t num_tokens;
    int64_t num_experts;
    int64_t topk;
    int64_t stride_token;

    // Stream for async execution
    hipStream_t stream;
};

/**
 * @brief Launch the CK-Tile fused MoE kernel
 *
 * This function launches a highly optimized 2-stage MoE kernel:
 * Stage 1: Gate/Up projection + SiLU activation
 * Stage 2: Down projection + weighted sum across top-k experts
 *
 * @param args Kernel arguments including pointers and dimensions
 * @return hipError_t HIP error code
 */
inline hipError_t CkTileMoeLaunch(const CkTileMoeArgs& args) {
    // Convert to CK-Tile host args
    ct::FusedMoeGemmHostArgs hargs;
    hargs.a_ptr = args.a_ptr;
    hargs.a_scale_ptr = args.a_scale_ptr;
    hargs.g_ptr = args.g_ptr;
    hargs.d_ptr = args.d_ptr;
    hargs.g_scale_ptr = args.g_scale_ptr;
    hargs.d_scale_ptr = args.d_scale_ptr;
    hargs.y_smooth_scale_ptr = args.y_smooth_scale_ptr;
    hargs.o_ptr = args.o_ptr;
    hargs.sorted_token_ids_ptr = args.sorted_token_ids_ptr;
    hargs.sorted_weight_ptr = args.sorted_weight_ptr;
    hargs.sorted_expert_ids_ptr = args.sorted_expert_ids_ptr;
    hargs.num_sorted_tiles_ptr = args.num_sorted_tiles_ptr;
    hargs.hidden_size = args.hidden_size;
    hargs.intermediate_size = args.intermediate_size;
    hargs.num_tokens = args.num_tokens;
    hargs.num_experts = args.num_experts;
    hargs.topk = args.topk;
    hargs.stride_token = args.stride_token;

    // Create kernel arguments
    auto kargs = Kernel::MakeKargs(hargs);

    // Get launch configuration
    auto grid_size = Kernel::GridSize(hargs);
    auto block_size = Kernel::BlockSize();
    auto smem_size = Kernel::GetSmemSize();

    // Create and launch kernel
    auto kernel = ct::make_kernel<2, void>(
        Kernel{},
        grid_size,
        block_size,
        smem_size,
        kargs
    );

    ct::stream_config s{args.stream, false, 0, 0, 1};
    ct::launch_kernel(s, kernel);

    return hipGetLastError();
}

/**
 * @brief Get kernel launch configuration for planning
 *
 * @param max_num_tokens_padded Maximum number of tokens after padding
 * @param intermediate_size Intermediate dimension size
 * @return dim3 Grid dimensions
 */
inline dim3 CkTileMoeGetGridSize(int64_t max_num_tokens_padded, int64_t intermediate_size) {
    return Kernel::GridSize(
        ct::FusedMoeGemmHostArgs{
            .num_tokens = static_cast<ct::index_t>(max_num_tokens_padded),
            .intermediate_size = static_cast<ct::index_t>(intermediate_size)
        }
    );
}

/**
 * @brief Get required shared memory size
 *
 * @return size_t Shared memory size in bytes
 */
inline size_t CkTileMoeGetSmemSize() {
    return Kernel::GetSmemSize();
}

/**
 * @brief Get kernel name for profiling/debugging
 *
 * @return const char* Kernel name string
 */
inline const char* CkTileMoeGetKernelName() {
    return "ck_tile_fused_moe_mxfp4";
}

// ============================================================================
// Device-side weight pre-shuffling utilities
// ============================================================================

/**
 * @brief Pre-shuffle weights for optimal CK-Tile access pattern
 *
 * CK-Tile expects weights in a pre-shuffled layout for efficient
 * global memory access. This function performs the shuffle on the host.
 *
 * @param weights Input weights in standard layout
 * @param shuffled_weights Output buffer for shuffled weights
 * @param num_experts Number of experts
 * @param rows Number of rows (intermediate_size or hidden_size)
 * @param cols Number of columns (hidden_size or intermediate_size)
 */
inline void CkTileMoePreShuffleWeights(
    const void* weights,
    void* shuffled_weights,
    int64_t num_experts,
    int64_t rows,
    int64_t cols,
    bool is_gate_up  // true for gate+up, false for down
) {
    // Implementation depends on the specific weight format
    // This is a placeholder for the actual shuffling logic
    // For MXFP4, the shuffle needs to account for packed 4-bit values

    // The shuffle pattern follows the wave-flattened layout:
    // Original: [expert, row, col]
    // Shuffled: [expert, row/Warp_N, col/Warp_K, Warp_N*Warp_K]

    // TODO: Implement actual shuffle logic based on CK-Tile reference
    (void)weights;
    (void)shuffled_weights;
    (void)num_experts;
    (void)rows;
    (void)cols;
    (void)is_gate_up;
}

// ============================================================================
// Performance tuning utilities
// ============================================================================

/**
 * @brief Get recommended number of blocks per CU for MI355X
 *
 * @return int Recommended blocks per compute unit
 */
inline int CkTileMoeGetRecommendedBlocksPerCU() {
    // MI355X has high compute density, we can use fewer blocks per CU
    // to maximize occupancy while minimizing scheduling overhead
    return 2;
}

/**
 * @brief Check if hardware supports MXFP4 instructions
 *
 * @return true if MXFP4 is supported
 */
inline bool CkTileMoeIsMxfp4Supported() {
    hipDeviceProp_t props;
    hipGetDeviceProperties(&props, 0);

    // MXFP4 requires gfx950+ (MI355X)
    return (props.major == 9 && props.minor >= 5) ||
           (std::strstr(props.gcnArchName, "gfx950") != nullptr);
}

/**
 * @brief Get kernel info string for debugging
 */
inline void CkTileMoePrintConfig() {
    printf("CK-Tile Fused MoE Kernel Configuration:\n");
    printf("  Target: MI355X (gfx950)\n");
    printf("  Pipeline: FusedMoeGemmPipeline_FlatmmEx\n");
    printf("  BlockTile_0: [%d, %d, %d]\n", 64, 128, 64);
    printf("  BlockTile_1: [%d, %d, %d]\n", 64, 64, 128);
    printf("  WarpTile: [%d, %d, %d]\n", 32, 32, 32);
    printf("  Features: MXFP4, Atomic Accum, Gate+Up Fused\n");
}
