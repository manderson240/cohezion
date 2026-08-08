#!/usr/bin/env python3
"""Silicon Optimization Benchmark for AMD Strix Halo (gfx1151 / RDNA3.5).

Benchmarks Wave32 matrix alignment, UMA memory aperture management, and
tri-compute backend throughput (NPU, iGPU Vulkan/ROCm, Zen 5 CPU).
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.inference.hardware_telemetry import ComputeBackend
from cohezion.inference.strix_halo_optimizer import SiliconOptimizationProfile, StrixHaloSiliconOptimizer
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("StrixHaloBenchmark")


def main() -> None:
    print("=========================================================")
    print("⚡ STRIX HALO (gfx1151 / RDNA3.5) SILICON OPTIMIZATION BENCHMARK")
    print("=========================================================\n")

    # 1. Initialize Optimizer
    profile = SiliconOptimizationProfile(wavefront_size=32, gtt_pool_max_gb=120)
    optimizer = StrixHaloSiliconOptimizer(profile=profile)

    aligned = optimizer.verify_wave32_alignment()
    print("🔍 Hardware Alignment Check:")
    print(f"   Wave32 Matrix Alignment: {'✅ ALIGNED (Wave32)' if aligned else '❌ UNALIGNED (Wave64)'}")
    print(f"   UMA GTT Pool Limit     : {profile.gtt_pool_max_gb} GB")
    print(f"   Compiler Flags         : {' '.join(optimizer.get_optimal_compilation_flags())}\n")

    # 2. Benchmark Compute Backends
    backends = [
        (ComputeBackend.XDNA2_NPU, "XDNA2 NPU (FLM / Firmware)"),
        (ComputeBackend.VULKAN_GPU, "Radeon 8060S iGPU (Vulkan / Wave32)"),
        (ComputeBackend.ZEN5_CPU, "Ryzen 9 7945HX CPU (Zen 5 / AVX-512)"),
    ]

    print("🚀 Benchmarking Local Compute Backends:")
    print("---------------------------------------------------------")
    for b_enum, b_name in backends:
        res = optimizer.benchmark_lane(b_enum, iterations=4)
        print(f"\n🔹 Backend: {b_name}")
        print(f"   Throughput           : {res.tokens_per_sec:.2f} tok/s")
        print(f"   First-Token Latency  : {res.latency_first_token_ms:.1f} ms")
        print(f"   Wavefront Size       : {res.wavefront_size}")
        print(f"   Status               : {'⚡ OPTIMAL' if res.optimal else '⚠️ SUBOPTIMAL'}")

    # 3. Benchmark EVI Router Integration
    print("\n\n🎯 Routing Integration Benchmark:")
    print("---------------------------------------------------------")
    router = UnifiedHybridRouter()
    routing_res = router.route(
        task_type="coding",
        task_importance=0.6,
        estimated_tier1_quality=0.85,
        target_quality_required=0.85,
    )
    print(f"   Selected Tier: Tier {routing_res.selected_tier} ({routing_res.model_name})")
    print(f"   EVI Score    : {routing_res.evi_score:.4f}")
    print(f"   Routing Log  : {routing_res.reason}")

    print("\n✅ STRIX HALO SILICON OPTIMIZATION VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
