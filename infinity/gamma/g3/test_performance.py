"""
Performance Benchmark Tests for Integrated Submission

Benchmarks all three kernels (GEMM, MoE, MLA) and reports performance metrics.
"""

import sys
import os
import torch
import time
import numpy as np
from typing import List, Dict, Any

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


class PerformanceBenchmark:
    """Benchmarks kernel performance."""

    def __init__(self, warmup_iters: int = 3, bench_iters: int = 10):
        self.warmup_iters = warmup_iters
        self.bench_iters = bench_iters
        self.results = {}

    def _benchmark_kernel(self, kernel_fn, data, name: str) -> Dict[str, float]:
        """Benchmark a single kernel."""
        # Warmup
        for _ in range(self.warmup_iters):
            _ = kernel_fn(data)
        torch.cuda.synchronize()

        # Benchmark
        times = []
        for _ in range(self.bench_iters):
            torch.cuda.synchronize()
            start = time.perf_counter()
            _ = kernel_fn(data)
            torch.cuda.synchronize()
            end = time.perf_counter()
            times.append((end - start) * 1e6)  # µs

        return {
            "mean": np.mean(times),
            "std": np.std(times),
            "min": np.min(times),
            "max": np.max(times),
            "median": np.median(times),
        }

    def benchmark_gemm(self) -> Dict[str, Any]:
        """Benchmark GEMM kernel."""
        print("\n" + "=" * 60)
        print("GEMM Performance Benchmark")
        print("=" * 60)

        try:
            from reference import generate_input as gemm_generate_input

            # Benchmark shapes
            shapes = [
                (16, 64, 128),
                (64, 256, 512),
                (128, 512, 1024),
                (256, 1024, 2048),
                (512, 2048, 4096),
            ]

            results = {}
            for m, n, k in shapes:
                print(f"\nBenchmarking: M={m}, N={n}, K={k}")

                data = gemm_generate_input(m, n, k, seed=42)
                metrics = self._benchmark_kernel(gemm_kernel, data, f"GEMM_{m}x{n}x{k}")

                print(f"  Time: {metrics['mean']:.2f} ± {metrics['std']:.2f} µs")
                print(f"  Min/Max: {metrics['min']:.2f} / {metrics['max']:.2f} µs")

                # Calculate GFLOPS
                flops = 2 * m * n * k
                gflops = flops / (metrics["mean"] * 1e-6) / 1e9
                print(f"  Performance: {gflops:.2f} GFLOPS")

                results[f"{m}x{n}x{k}"] = {**metrics, "gflops": gflops}

            return results

        except ImportError as e:
            print(f"  ⚠ SKIPPED: {e}")
            return {}

    def benchmark_moe(self) -> Dict[str, Any]:
        """Benchmark MoE kernel."""
        print("\n" + "=" * 60)
        print("MoE Performance Benchmark")
        print("=" * 60)

        try:
            from reference import generate_input as moe_generate_input

            # Benchmark shapes from spec
            shapes = [
                (4, 257, 7168, 256, 9),
                (64, 257, 7168, 256, 9),
                (64, 33, 7168, 2048, 9),
                (256, 257, 7168, 256, 9),
            ]

            results = {}
            for bs, E, d_hidden, d_expert, top_k in shapes:
                print(f"\nBenchmarking: bs={bs}, E={E}, d_hidden={d_hidden}, d_expert={d_expert}")

                nrouted = E - 1
                nshared = 1
                npertoken = top_k - 1

                data = moe_generate_input(
                    dhidden=d_hidden,
                    dexpert=d_expert,
                    nroutedexperts=nrouted,
                    nexpertspertoken=npertoken,
                    nsharedexperts=nshared,
                    bs=bs,
                    seed=42,
                )

                metrics = self._benchmark_kernel(moe_kernel, data, f"MoE_bs{bs}_E{E}")

                print(f"  Time: {metrics['mean']:.2f} ± {metrics['std']:.2f} µs")
                print(f"  Min/Max: {metrics['min']:.2f} / {metrics['max']:.2f} µs")

                results[f"bs{bs}_E{E}"] = metrics

            return results

        except ImportError as e:
            print(f"  ⚠ SKIPPED: {e}")
            return {}

    def benchmark_mla(self) -> Dict[str, Any]:
        """Benchmark MLA kernel."""
        print("\n" + "=" * 60)
        print("MLA Performance Benchmark")
        print("=" * 60)

        try:
            from reference import generate_input as mla_generate_input

            # Test configurations
            configs = [
                {"batch_size": 1, "kv_seq_len": 1024, "q_seq_len": 1, "num_heads": 16},
                {"batch_size": 4, "kv_seq_len": 2048, "q_seq_len": 1, "num_heads": 16},
                {"batch_size": 16, "kv_seq_len": 4096, "q_seq_len": 1, "num_heads": 16},
            ]

            results = {}
            for config in configs:
                bs = config["batch_size"]
                kv_len = config["kv_seq_len"]
                print(f"\nBenchmarking: bs={bs}, kv_len={kv_len}")

                data = mla_generate_input(config)
                metrics = self._benchmark_kernel(mla_kernel, data, f"MLA_bs{bs}_kv{kv_len}")

                print(f"  Time: {metrics['mean']:.2f} ± {metrics['std']:.2f} µs")
                print(f"  Min/Max: {metrics['min']:.2f} / {metrics['max']:.2f} µs")

                results[f"bs{bs}_kv{kv_len}"] = metrics

            return results

        except ImportError as e:
            print(f"  ⚠ SKIPPED: {e}")
            return {}

    def generate_report(self) -> str:
        """Generate performance report."""
        report = []
        report.append("=" * 60)
        report.append("PERFORMANCE BENCHMARK REPORT")
        report.append("=" * 60)
        report.append(f"Warmup iterations: {self.warmup_iters}")
        report.append(f"Benchmark iterations: {self.bench_iters}")
        report.append("")

        gemm_results = self.benchmark_gemm()
        moe_results = self.benchmark_moe()
        mla_results = self.benchmark_mla()

        report.append("\n" + "=" * 60)
        report.append("SUMMARY")
        report.append("=" * 60)

        if gemm_results:
            report.append("\nGEMM Results:")
            for shape, metrics in gemm_results.items():
                report.append(
                    f"  {shape}: {metrics['mean']:.2f} ± {metrics['std']:.2f} µs ({metrics.get('gflops', 0):.2f} GFLOPS)"
                )

        if moe_results:
            report.append("\nMoE Results:")
            for shape, metrics in moe_results.items():
                report.append(f"  {shape}: {metrics['mean']:.2f} ± {metrics['std']:.2f} µs")

        if mla_results:
            report.append("\nMLA Results:")
            for shape, metrics in mla_results.items():
                report.append(f"  {shape}: {metrics['mean']:.2f} ± {metrics['std']:.2f} µs")

        return "\n".join(report)


def main():
    """Run performance benchmarks."""
    benchmark = PerformanceBenchmark(warmup_iters=3, bench_iters=10)
    report = benchmark.generate_report()
    print(report)

    # Save report
    report_path = "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/opencode_infinity/teams/gamma/agents/g3/performance_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
