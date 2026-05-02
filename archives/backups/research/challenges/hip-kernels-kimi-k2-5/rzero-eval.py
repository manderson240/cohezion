#!/usr/bin/env python3
"""R-Zero Local Evaluation Framework for Luma AMD Speedrun.

Evaluates challengers against reference implementations locally.
"""

import sys
import time
from pathlib import Path

import torch


# Add kernel paths
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm"
)
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/moe-mxfp4"
)
sys.path.insert(
    0, "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mixed-mla"
)


def evaluate_gemm_challenger(challenger_path: str) -> tuple[float, bool, str]:
    """Evaluate a GEMM challenger.

    Returns:
        (speedup_ratio, is_correct, error_message)
    """
    try:
        # Import reference
        # Load challenger
        import importlib.util

        from reference import ref_kernel

        spec = importlib.util.spec_from_file_location("challenger", challenger_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        custom_kernel = module.custom_kernel

        # Test shapes from eval.py
        test_shapes = [
            (4, 2880, 512),
            (16, 2112, 7168),
            (32, 4096, 512),
            (64, 7168, 2048),
            (256, 3072, 1536),
        ]

        total_ref_time = 0
        total_chal_time = 0
        all_correct = True

        for m, n, k in test_shapes:
            # Generate input
            from reference import generate_input

            data = generate_input(m, n, k, seed=42)

            # Reference run
            torch.cuda.synchronize()
            start = time.perf_counter()
            ref_out = ref_kernel(data)
            torch.cuda.synchronize()
            ref_time = time.perf_counter() - start

            # Challenger run
            torch.cuda.synchronize()
            start = time.perf_counter()
            chal_out = custom_kernel(data)
            torch.cuda.synchronize()
            chal_time = time.perf_counter() - start

            # Check correctness
            try:
                torch.testing.assert_close(chal_out, ref_out, rtol=1e-2, atol=1e-2)
            except AssertionError as e:
                all_correct = False
                return 0.0, False, f"Shape ({m},{n},{k}) failed: {e}"

            total_ref_time += ref_time
            total_chal_time += chal_time

        speedup = total_ref_time / total_chal_time if total_chal_time > 0 else 0
        return speedup, all_correct, "PASS"

    except Exception as e:
        return 0.0, False, f"Error: {e!s}"


def main():
    """Evaluate all challengers in rzero-challengers/"""
    base_path = Path("/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/rzero-challengers")

    results = []

    # Evaluate GEMM challengers
    gemm_path = base_path / "gemm"
    if gemm_path.exists():
        for challenger_file in sorted(gemm_path.glob("challenger_*.py")):
            print(f"Evaluating {challenger_file.name}...", end=" ")
            speedup, is_correct, msg = evaluate_gemm_challenger(str(challenger_file))
            status = "✓" if is_correct else "✗"
            print(f"{status} speedup={speedup:.2f}x {msg}")
            results.append(
                {
                    "file": challenger_file.name,
                    "kernel": "gemm",
                    "speedup": speedup,
                    "correct": is_correct,
                    "message": msg,
                }
            )

    # Save results
    import json

    results_path = Path("/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/rzero-results")
    results_path.mkdir(exist_ok=True)
    with open(results_path / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nEvaluated {len(results)} challengers")
    print(f"Results saved to {results_path / 'results.json'}")


if __name__ == "__main__":
    main()
