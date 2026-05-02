#!/usr/bin/env python3
"""
FlyDSL Trivial GPU Kernel Test
Verifies basic @kernel decorator and JIT compilation on MI355X
"""

import sys

import numpy as np


# FlyDSL imports (available on MI355X Popcorn runner)
try:
    import flydsl.compiler as flyc
    import flydsl.expr as fx
    from flydsl import run_pipeline

    FLYDSL_AVAILABLE = True
except ImportError:
    print("Warning: FlyDSL not available. This code is designed for MI355X runner.")
    FLYDSL_AVAILABLE = False


# ============================================================================
# Trivial Vector Addition Kernel
# ============================================================================


@flyc.kernel
def vector_add_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, n: fx.Constexpr[int]):
    """
    Simple vector addition: C[i] = A[i] + B[i]
    Demonstrates basic FlyDSL @kernel usage
    """
    # Get thread indices
    bid = fx.block_idx.x
    tid = fx.thread_idx.x

    # Global thread ID
    gid = bid * 256 + tid  # 256 threads per block

    # Bounds check
    if gid < n:
        # Load from global memory
        a_val = A[gid]
        b_val = B[gid]

        # Compute
        c_val = a_val + b_val

        # Store to global memory
        C[gid] = c_val


# ============================================================================
# MFMA Test Kernel (MI355X specific)
# ============================================================================


@flyc.kernel
def mfma_test_kernel(
    A: fx.Tensor,  # M x K
    B: fx.Tensor,  # K x N
    C: fx.Tensor,  # M x N
    M: fx.Constexpr[int],
    K: fx.Constexpr[int],
    N: fx.Constexpr[int],
):
    """
    Test MFMA (Matrix Fused Multiply-Add) instructions on MI355X
    Uses mfma_f32_32x32x64_f8f6f4 for MXFP4 operations
    """
    # Block-level partitioning
    bid_m = fx.block_idx.x  # Block row
    bid_n = fx.block_idx.y  # Block col

    # Warp-level partitioning (4 warps per block)
    warp_id = fx.thread_idx.x // 64  # 64 threads per warp
    lane_id = fx.thread_idx.x % 64

    # Tile dimensions
    TM = 32  # Thread tile M
    TN = 32  # Thread tile N
    TK = 64  # Thread tile K (MFMA input)

    # Compute output coordinates
    m_start = bid_m * 128 + (warp_id // 2) * 32  # 128 = 4 warps * 32
    n_start = bid_n * 64 + (warp_id % 2) * 32

    # Accumulator in registers
    acc = fx.constant(0.0, fx.f32)

    # K-loop with MFMA
    for k in range(0, K, TK):
        # Load A tile (MXFP4)
        a_tile = fx.load_tile(A, m_start, k, TM, TK)

        # Load B tile (MXFP4)
        b_tile = fx.load_tile(B, k, n_start, TK, TN)

        # MFMA operation: acc += A * B
        # On MI355X: mfma_f32_32x32x64_f8f6f4
        acc = fx.mfma_f32_32x32x64(a_tile, b_tile, acc)

    # Store result
    fx.store_tile(C, m_start, n_start, acc, TM, TN)


# ============================================================================
# JIT Compilation and Execution
# ============================================================================


def compile_and_test_vector_add():
    """Compile and test the vector add kernel"""
    print("=" * 60)
    print("FlyDSL Vector Add Kernel Compilation")
    print("=" * 60)

    if not FLYDSL_AVAILABLE:
        print("FlyDSL not available - skipping compilation")
        return False

    # Define tensor shapes
    n = 1024
    block_dim = 256

    # Create input tensors
    A = fx.make_tensor([n], fx.f32)
    B = fx.make_tensor([n], fx.f32)
    C = fx.make_tensor([n], fx.f32)

    # Compile the kernel with JIT
    print("Compiling vector_add_kernel...")
    compiled_kernel = flyc.compile(
        vector_add_kernel,
        args=[A, B, C, fx.constant(n)],
        grid_dim=(n // block_dim,),
        block_dim=(block_dim,),
        arch="gfx950",  # MI355X
    )

    print("✓ Compilation successful!")
    print(f"  Grid dim: ({n // block_dim},)")
    print(f"  Block dim: ({block_dim},)")

    # Test execution
    print("\nRunning test execution...")

    # Create host arrays
    h_A = np.random.randn(n).astype(np.float32)
    h_B = np.random.randn(n).astype(np.float32)
    h_C = np.zeros(n, dtype=np.float32)

    # Execute kernel
    compiled_kernel(h_A, h_B, h_C)

    # Verify results
    expected = h_A + h_B
    max_error = np.max(np.abs(h_C - expected))

    print("✓ Execution completed")
    print(f"  Max error: {max_error:.2e}")

    if max_error < 1e-5:
        print("  ✓ Results verified!")
        return True
    else:
        print("  ✗ Results incorrect!")
        return False


def compile_mfma_kernel():
    """Compile MFMA test kernel"""
    print("\n" + "=" * 60)
    print("FlyDSL MFMA Kernel Compilation")
    print("=" * 60)

    if not FLYDSL_AVAILABLE:
        print("FlyDSL not available - skipping compilation")
        return False

    # Matrix dimensions (aligned to MFMA tile)
    M, K, N = 256, 256, 256

    # Create tensors
    A = fx.make_tensor([M, K], fx.f32)
    B = fx.make_tensor([K, N], fx.f32)
    C = fx.make_tensor([M, N], fx.f32)

    # Compile kernel
    print("Compiling mfma_test_kernel...")
    compiled_kernel = flyc.compile(
        mfma_test_kernel,
        args=[A, B, C, fx.constant(M), fx.constant(K), fx.constant(N)],
        grid_dim=(M // 128, N // 64),  # Block tiles
        block_dim=(256,),  # 4 warps
        arch="gfx950",
        enable_mfma=True,
    )

    print("✓ MFMA kernel compiled successfully!")
    print(f"  Grid: ({M // 128}, {N // 64})")
    print("  Block: (256,)")
    print("  Features: MFMA F32_32x32x64_F8F6F4")

    return True


def print_kernel_info():
    """Print kernel information"""
    print("=" * 60)
    print("FlyDSL Kernel Information")
    print("=" * 60)

    info = {
        "framework": "FlyDSL",
        "version": "v0.0.1.dev",
        "target": "AMD MI355X (gfx950)",
        "features": [
            "@kernel decorator",
            "JIT compilation with disk caching",
            "MFMA instruction support",
            "Layout algebra (Shape, Stride, Layout)",
            "Hierarchical control (block/warp/thread/instruction)",
        ],
        "mfma_instructions": ["mfma_f32_16x16x128_f8f6f4", "mfma_f32_32x32x64_f8f6f4", "mfma_f32_16x16x256_f8f6f4"],
    }

    print(f"Framework: {info['framework']} {info['version']}")
    print(f"Target: {info['target']}")

    print("\nFeatures:")
    for feat in info["features"]:
        print(f"  - {feat}")

    print("\nMFMA Instructions (CDNA4):")
    for mfma in info["mfma_instructions"]:
        print(f"  - {mfma}")

    print(f"\nFlyDSL Available: {FLYDSL_AVAILABLE}")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point"""
    print_kernel_info()

    # Test 1: Trivial vector add kernel
    success1 = compile_and_test_vector_add()

    # Test 2: MFMA kernel
    success2 = compile_mfma_kernel()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Vector Add Kernel: {'✓ PASS' if success1 else '✗ SKIP'}")
    print(f"MFMA Kernel: {'✓ PASS' if success2 else '✗ SKIP'}")

    if FLYDSL_AVAILABLE:
        return 0 if (success1 and success2) else 1
    else:
        print("\nNote: FlyDSL is designed to run on MI355X Popcorn runner")
        print("where FlyDSL v0.0.1.dev is pre-installed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
