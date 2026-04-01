"""
Smoke test for direct CK kernel dispatch approach.

This tests whether we can:
1. Call moe_cktile2stages_gemm1/2 directly with explicit kernel_name
2. Verify correctness against reference

NOTE: This test may fail if the kernel names are not registered in the lookup table.
"""

import os
import sys


# Add aiter to path if available
try:
    import aiter
    from aiter import ActivationType, QuantType, dtypes
    from aiter.ops.moe_op import moe_cktile2stages_gemm1, moe_cktile2stages_gemm2
    from aiter.ops.shuffle import shuffle_weight
    from aiter.utility import fp4_utils
    HAS_AITER = True
except ImportError as e:
    print(f"aiter not available: {e}")
    HAS_AITER = False

# Path setup
KERNEL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KERNEL_DIR)

import reference


def build_kernel_name_gemm1(block_m, has_bias=False, act="silu"):
    """
    Build kernel name for gemm1 following the naming convention.
    
    From moe_cktile2stages_common.py kernelInstance.name property:
    moe_cktile2stages_gemm{stage}_{BLOCK_SIZE}x{MPerBlock}x{NPerBlock}x{KPerBlock}_{WAVE_MAP_M}x{WAVE_MAP_N}_{WAVE_TILE_M}x{WAVE_TILE_N}x{WAVE_TILE_K}_{BlockPerCU}perCU_{QuantType}_{ActOP}{MulRoutedWeight}{HasBias}{SplitK}
    """
    # For a16w4 on gfx950 with block_m=32
    # Kernel 1: kernelInstance(stage=1, BLOCK_SIZE=256, MPerBlock=32, NPerBlock=256, KPerBlock=256, WAVE_TILE_M=16, WAVE_TILE_N=16, WAVE_TILE_K=32, WAVE_MAP_M=1, WAVE_MAP_N=4, Block_Per_CU=2)
    if block_m == 32:
        name = "moe_cktile2stages_gemm1_256x32x256_1x4_16x16x32_2perCU_per_tensor"
        if has_bias:
            name += "_HasBias"
        if act and act != "no":
            name += f"_{act}"
        return name
    elif block_m == 64:
        name = "moe_cktile2stages_gemm1_256x64x256_1x4_16x16x32_1perCU_per_tensor"
        if has_bias:
            name += "_HasBias"
        if act and act != "no":
            name += f"_{act}"
        return name
    elif block_m == 16:
        name = "moe_cktile2stages_gemm1_256x16x128_1x4_16x16x32_2perCU_per_tensor"
        if has_bias:
            name += "_HasBias"
        if act and act != "no":
            name += f"_{act}"
        return name
    else:
        return ""


def build_kernel_name_gemm2(block_m, has_bias=True):
    """
    Build kernel name for gemm2 following the naming convention.
    
    gemm2 always has MulRoutedWeight=True, no activation (act="no" for stage 2)
    """
    if block_m == 32:
        name = "moe_cktile2stages_gemm2_256x32x256_1x4_16x16x32_2perCU_per_tensor_MulRoutedWeight"
        if has_bias:
            name += "_HasBias"
        return name
    elif block_m == 64:
        name = "moe_cktile2stages_gemm2_256x64x256_1x4_16x16x32_1perCU_per_tensor_MulRoutedWeight"
        if has_bias:
            name += "_HasBias"
        return name
    elif block_m == 16:
        name = "moe_cktile2stages_gemm2_256x16x128_1x4_16x16x32_2perCU_per_tensor_MulRoutedWeight"
        if has_bias:
            name += "_HasBias"
        return name
    else:
        return ""


def test_kernel_name_discovery():
    """Test if we can discover available kernel names by trying different block sizes."""
    if not HAS_AITER:
        print("SKIP: aiter not available")
        return
    
    print("Testing kernel name discovery...")
    
    # Try different kernel names
    kernel_names_to_try = [
        build_kernel_name_gemm1(32),
        build_kernel_name_gemm1(64),
        build_kernel_name_gemm2(32),
        build_kernel_name_gemm2(64),
    ]
    
    for kname in kernel_names_to_try:
        print(f"  Kernel name: {kname}")
    
    print("Kernel name discovery test complete")


def test_direct_dispatch_correctness():
    """Test that direct dispatch produces correct results."""
    if not HAS_AITER:
        print("SKIP: aiter not available")
        return
    
    print("\nTesting direct dispatch correctness...")
    
    # Generate test input
    test_case = {
        "dhidden": 4096,
        "dexpert": 1024,
        "nroutedexperts": 256,
        "nexpertspertoken": 8,
        "nsharedexperts": 1,
        "bs": 8,
        "seed": 9371,
    }
    
    data = reference.generate_input(**test_case)
    
    # Run reference
    ref_output = reference.ref_kernel(data)
    print(f"  Reference output shape: {ref_output.shape}")
    print(f"  Reference output mean: {ref_output.abs().mean().item():.6f}")
    
    # The direct dispatch test is complex because we'd need to:
    # 1. Manually sort tokens by expert
    # 2. Call gemm1 then gemm2 with proper tensor shapes
    # 3. Handle the routing reduction
    
    # For now, just verify the approach is feasible
    print("  Direct dispatch correctness test requires more implementation")
    print("  (Need to implement token sorting and reduction manually)")


def test_env_vars():
    """Test that environment variables are properly set."""
    print("\nTesting environment variables...")
    
    # Set USE_NT
    os.environ["AITER_USE_NT"] = "1"
    print(f"  AITER_USE_NT = {os.environ.get('AITER_USE_NT', 'NOT SET')}")
    
    print("Environment variables test complete")


if __name__ == "__main__":
    print("=" * 60)
    print("Direct CK Dispatch Test")
    print("=" * 60)
    
    test_env_vars()
    test_kernel_name_discovery()
    test_direct_dispatch_correctness()
    
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)
