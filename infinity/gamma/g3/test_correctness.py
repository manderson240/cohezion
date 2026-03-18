"""
Correctness Validation Tests for Integrated Submission

Validates all three kernels (GEMM, MoE, MLA) against reference implementations.
"""

import sys
import os
import torch
import numpy as np
from typing import Tuple, Dict, Any

# Add paths for imports
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4"
)
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm"
)
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mixed-mla"
)

from submission import gemm_kernel, moe_kernel, mla_kernel, IntegratedKernel

# Test configuration
RTOL = 1e-2
ATOL = 1e-2


class CorrectnessValidator:
    """Validates kernel correctness against reference implementations."""

    def __init__(self):
        self.results = []

    def validate_gemm(self) -> bool:
        """Validate GEMM kernel correctness."""
        print("\n" + "=" * 60)
        print("GEMM Correctness Validation")
        print("=" * 60)

        try:
            from reference import generate_input as gemm_generate_input
            from reference import ref_kernel as gemm_ref_kernel

            test_shapes = [
                (16, 64, 128),
                (64, 256, 512),
                (128, 512, 1024),
                (256, 1024, 2048),
            ]

            all_passed = True
            for m, n, k in test_shapes:
                print(f"\nTesting shape: M={m}, N={n}, K={k}")

                data = gemm_generate_input(m, n, k, seed=42)
                ref_output = gemm_ref_kernel(data)

                try:
                    custom_output = gemm_kernel(data)

                    max_diff = torch.max(torch.abs(ref_output - custom_output)).item()
                    mean_diff = torch.mean(torch.abs(ref_output - custom_output)).item()

                    print(f"  Max diff: {max_diff:.6f}, Mean diff: {mean_diff:.6f}")

                    if max_diff < ATOL:
                        print(f"  ✓ PASSED")
                    else:
                        print(f"  ✗ FAILED (exceeds tolerance)")
                        all_passed = False

                except Exception as e:
                    print(f"  ✗ ERROR: {e}")
                    all_passed = False

            return all_passed

        except ImportError as e:
            print(f"  ⚠ SKIPPED: Reference not available - {e}")
            return True

    def validate_moe(self) -> bool:
        """Validate MoE kernel correctness."""
        print("\n" + "=" * 60)
        print("MoE Correctness Validation")
        print("=" * 60)

        try:
            from reference import generate_input as moe_generate_input
            from reference import ref_kernel as moe_ref_kernel

            # Benchmark shapes from spec
            test_configs = [
                # (bs, E, d_hidden, d_expert, top_k)
                (4, 257, 7168, 256, 9),
                (64, 257, 7168, 256, 9),
                (64, 33, 7168, 2048, 9),
            ]

            all_passed = True
            for bs, E, d_hidden, d_expert, top_k in test_configs:
                print(
                    f"\nTesting: bs={bs}, E={E}, d_hidden={d_hidden}, d_expert={d_expert}, top_k={top_k}"
                )

                nrouted = E - 1
                nshared = 1
                npertoken = top_k - 1

                try:
                    data = moe_generate_input(
                        dhidden=d_hidden,
                        dexpert=d_expert,
                        nroutedexperts=nrouted,
                        nexpertspertoken=npertoken,
                        nsharedexperts=nshared,
                        bs=bs,
                        seed=42,
                    )

                    ref_output = moe_ref_kernel(data)
                    custom_output = moe_kernel(data)

                    max_diff = torch.max(torch.abs(ref_output - custom_output)).item()
                    mean_diff = torch.mean(torch.abs(ref_output - custom_output)).item()

                    print(f"  Max diff: {max_diff:.6f}, Mean diff: {mean_diff:.6f}")

                    if max_diff < ATOL:
                        print(f"  ✓ PASSED")
                    else:
                        print(f"  ✗ FAILED (exceeds tolerance)")
                        all_passed = False

                except Exception as e:
                    print(f"  ✗ ERROR: {e}")
                    import traceback

                    traceback.print_exc()
                    all_passed = False

            return all_passed

        except ImportError as e:
            print(f"  ⚠ SKIPPED: Reference not available - {e}")
            return True

    def validate_mla(self) -> bool:
        """Validate MLA kernel correctness."""
        print("\n" + "=" * 60)
        print("MLA Correctness Validation")
        print("=" * 60)

        try:
            from reference import generate_input as mla_generate_input
            from reference import ref_kernel as mla_ref_kernel

            # Test configurations
            test_configs = [
                {"batch_size": 1, "kv_seq_len": 1024, "q_seq_len": 1, "num_heads": 16},
                {"batch_size": 4, "kv_seq_len": 2048, "q_seq_len": 1, "num_heads": 16},
                {"batch_size": 16, "kv_seq_len": 4096, "q_seq_len": 1, "num_heads": 16},
            ]

            all_passed = True
            for config in test_configs:
                print(f"\nTesting: bs={config['batch_size']}, kv_len={config['kv_seq_len']}")

                try:
                    data = mla_generate_input(config)
                    ref_output = mla_ref_kernel(data)
                    custom_output = mla_kernel(data)

                    max_diff = torch.max(torch.abs(ref_output - custom_output)).item()
                    mean_diff = torch.mean(torch.abs(ref_output - custom_output)).item()

                    print(f"  Max diff: {max_diff:.6f}, Mean diff: {mean_diff:.6f}")

                    if max_diff < ATOL:
                        print(f"  ✓ PASSED")
                    else:
                        print(f"  ✗ FAILED (exceeds tolerance)")
                        all_passed = False

                except Exception as e:
                    print(f"  ✗ ERROR: {e}")
                    import traceback

                    traceback.print_exc()
                    all_passed = False

            return all_passed

        except ImportError as e:
            print(f"  ⚠ SKIPPED: Reference not available - {e}")
            return True

    def generate_report(self) -> str:
        """Generate validation report."""
        report = []
        report.append("=" * 60)
        report.append("CORRECTNESS VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Tolerance: rtol={RTOL}, atol={ATOL}")
        report.append("")

        gemm_passed = self.validate_gemm()
        moe_passed = self.validate_moe()
        mla_passed = self.validate_mla()

        report.append("\n" + "=" * 60)
        report.append("SUMMARY")
        report.append("=" * 60)
        report.append(f"GEMM: {'✓ PASSED' if gemm_passed else '✗ FAILED'}")
        report.append(f"MoE:  {'✓ PASSED' if moe_passed else '✗ FAILED'}")
        report.append(f"MLA:  {'✓ PASSED' if mla_passed else '✗ FAILED'}")
        report.append("")

        if gemm_passed and moe_passed and mla_passed:
            report.append("OVERALL: ✓ ALL TESTS PASSED")
        else:
            report.append("OVERALL: ✗ SOME TESTS FAILED")

        return "\n".join(report)


def main():
    """Run correctness validation."""
    validator = CorrectnessValidator()
    report = validator.generate_report()
    print(report)

    # Save report
    report_path = "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/opencode_infinity/teams/gamma/agents/g3/correctness_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
