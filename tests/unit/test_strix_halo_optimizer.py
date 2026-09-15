"""Unit tests for StrixHaloSiliconOptimizer."""

import os

from cohezion.inference.hardware_telemetry import ComputeBackend
from cohezion.inference.strix_halo_optimizer import (
    SiliconOptimizationProfile,
    StrixHaloSiliconOptimizer,
)


def test_strix_halo_optimizer_init_environment() -> None:
    profile = SiliconOptimizationProfile(wavefront_size=32, gtt_pool_max_gb=120)
    optimizer = StrixHaloSiliconOptimizer(profile=profile)

    assert optimizer.verify_wave32_alignment() is True
    assert os.environ.get("ROCM_WAVEFRONT_SIZE") == "32"
    assert os.environ.get("HIP_FORCE_WAVE32") == "1"
    assert os.environ.get("GGML_VULKAN_WAVE_SIZE") == "32"
    assert os.environ.get("PYTORCH_ROCM_ARCH") == "gfx1151"


def test_strix_halo_compilation_flags() -> None:
    optimizer = StrixHaloSiliconOptimizer()
    flags = optimizer.get_optimal_compilation_flags()
    assert "-mwavefrontsize32" in flags
    assert "-O3" in flags


def test_benchmark_lane_execution() -> None:
    optimizer = StrixHaloSiliconOptimizer()
    res = optimizer.benchmark_lane(ComputeBackend.VULKAN_GPU, iterations=2)
    assert res.backend == "vulkan_gpu"
    assert res.tokens_per_sec > 0
    assert res.wavefront_size == 32
    assert res.optimal is True


def test_max_safe_token_budget() -> None:
    optimizer = StrixHaloSiliconOptimizer()
    # 20GB model weight
    weight_bytes = 20 * (1024**3)
    safe_budget = optimizer.compute_max_safe_token_budget(weight_bytes=weight_bytes)
    assert safe_budget >= 32768


def test_strix_halo_topology() -> None:
    optimizer = StrixHaloSiliconOptimizer()
    topology = optimizer.get_strix_halo_topology()
    assert topology.cpu_cores == 16
    assert topology.cpu_threads == 32
    assert "8060S" in topology.gpu_model
    assert "XDNA 2" in topology.npu_model
    assert topology.npu_port == 8002
    assert topology.igpu_small_port == 8003
    assert topology.igpu_heavy_port == 8006
    assert topology.safe_memory_floor_gb == 20.0


def test_enforce_wave32_environment() -> None:
    optimizer = StrixHaloSiliconOptimizer()
    env = optimizer.enforce_wave32_environment()
    assert env["ROCM_WAVEFRONT_SIZE"] == "32"
    assert env["HIP_FORCE_WAVE32"] == "1"
    assert env["GGML_VULKAN_WAVE_SIZE"] == "32"
    assert env["PYTORCH_ROCM_ARCH"] == "gfx1151"


def test_probe_strix_halo_lanes() -> None:
    optimizer = StrixHaloSiliconOptimizer()
    lanes = optimizer.probe_strix_halo_lanes(timeout_s=0.5)
    assert 8002 in lanes
    assert 8003 in lanes
    assert 8005 in lanes
    assert 8006 in lanes
    assert 13305 in lanes
    assert 11434 in lanes
    # Port 8002 NPU FastFlowLM should be responsive
    assert lanes[8002].port == 8002
    assert lanes[8002].lane_name == "XDNA2 NPU FastFlowLM"
