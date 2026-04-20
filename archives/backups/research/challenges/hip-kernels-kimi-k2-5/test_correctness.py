"""Test script to verify correctness of custom HIP kernel submissions."""

import sys

import torch


# Add paths for kernel imports
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels")
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mixed-mla"
)
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm"
)

from utils import set_seed, verbose_allclose


def test_mla_submission():
    """Test MLA submission correctness."""
    print("\n" + "=" * 60)
    print("Testing MLA Submission")
    print("=" * 60)

    try:
        # Import reference and submission directly
        import importlib.util

        # Load reference module
        spec = importlib.util.spec_from_file_location(
            "mla_reference",
            "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mixed-mla/reference.py",
        )
        mla_reference = importlib.util.module_from_spec(spec)
        sys.modules["mla_reference"] = mla_reference
        spec.loader.exec_module(mla_reference)

        # Import the submission
        sys.path.insert(0, "/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/submissions")
        from mla_fp8_hip import custom_kernel

        generate_input = mla_reference.generate_input
        ref_kernel = mla_reference.ref_kernel

        # Test with small decode batch
        set_seed(42)
        batchsize, qseqlen, kvseqlen, tp = 2, 1, 64, 4

        data = generate_input(batchsize, qseqlen, kvseqlen, tp, seed=42)

        print(f"Test spec: bs={batchsize}, qseqlen={qseqlen}, kvseqlen={kvseqlen}, tp={tp}")

        # Get reference output
        expected = ref_kernel(data)
        print(f"Reference output shape: {expected.shape}")

        # Get submission output
        output = custom_kernel(data)
        print(f"Submission output shape: {output.shape}")

        # Compare
        good, reasons = verbose_allclose(output, expected, rtol=1e-02, atol=1e-02)

        if good:
            print("✓ MLA submission PASSED correctness check")
            return True
        else:
            print("✗ MLA submission FAILED correctness check:")
            print(reasons)
            return False

    except Exception as e:
        print(f"✗ MLA test error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_gemm_submission():
    """Test GEMM submission correctness."""
    print("\n" + "=" * 60)
    print("Testing GEMM Submission")
    print("=" * 60)

    try:
        # Import reference module directly
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "gemm_reference",
            "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm/reference.py",
        )
        gemm_reference = importlib.util.module_from_spec(spec)
        sys.modules["gemm_reference"] = gemm_reference
        spec.loader.exec_module(gemm_reference)

        # Import the submission
        from gemm_custom_hip import custom_kernel

        generate_input = gemm_reference.generate_input
        ref_kernel = gemm_reference.ref_kernel

        # Test with small shapes
        set_seed(42)
        m, n, k = 64, 64, 128

        data = generate_input(m, n, k, seed=42)

        print(f"Test spec: m={m}, n={n}, k={k}")

        # Get reference output
        expected = ref_kernel(data)
        print(f"Reference output shape: {expected.shape}")

        # Get submission output
        output = custom_kernel(data)
        print(f"Submission output shape: {output.shape}")

        # Compare
        good, reasons = verbose_allclose(output, expected, rtol=1e-02, atol=1e-02)

        if good:
            print("✓ GEMM submission PASSED correctness check")
            return True
        else:
            print("✗ GEMM submission FAILED correctness check:")
            print(reasons)
            return False

    except Exception as e:
        print(f"✗ GEMM test error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all correctness tests."""
    print("Starting correctness verification...")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("WARNING: CUDA not available, tests may fail")

    results = []

    # Test MLA
    mla_passed = test_mla_submission()
    results.append(("MLA", mla_passed))

    # Test GEMM
    gemm_passed = test_gemm_submission()
    results.append(("GEMM", gemm_passed))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")

    all_passed = all(passed for _, passed in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
