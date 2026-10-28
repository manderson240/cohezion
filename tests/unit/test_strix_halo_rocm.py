"""Unit tests for Strix Halo (gfx1151) ROCm & Silicon Optimizations."""

from __future__ import annotations

import shutil
import subprocess

from cohezion.inference.hardware_telemetry import ComputeBackend, HardwareTelemetry
from cohezion.inference.quark_quantizer import QuarkModelQuantizer, QuarkQuantizerConfig
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer


def test_rocm_cli_binary_available() -> None:
    """Verify rocm-cli binary is installed and executable."""
    rocm_bin = shutil.which("rocm")
    assert rocm_bin is not None, "rocm-cli binary should be located on PATH (~/.local/bin/rocm)"

    res = subprocess.run([rocm_bin, "--version"], capture_output=True, text=True, check=True)
    assert "rocm-cli" in res.stdout, f"Unexpected version output: {res.stdout}"


def test_amd_smi_telemetry_capture() -> None:
    """Verify HardwareTelemetry extracts live ROCm GPU telemetry via amd-smi."""
    telemetry = HardwareTelemetry(ComputeBackend.ROCM_GPU)
    snapshot = telemetry.snapshot()

    assert snapshot.backend == ComputeBackend.ROCM_GPU
    # Temperature should be populated if amd-smi is online
    if telemetry.has_amd_smi:
        assert snapshot.temperature_c > 0.0, "Expected non-zero GPU temperature"
        assert snapshot.memory_total_mb > 0, "Expected non-zero total GTT memory"


def test_amd_quark_quantizer() -> None:
    """Verify AMD Quark quantizer module detects v0.13 and calculates UMA recipe."""
    config = QuarkQuantizerConfig(target_precision="w4a16", export_format="gguf")
    quantizer = QuarkModelQuantizer(config)

    assert quantizer.is_available, "amd-quark should be installed and importable"
    version = quantizer.get_version()
    assert version.startswith("0.13"), f"Expected Quark v0.13, got {version}"

    # Test recipe generation for a 35B model (70 GB BF16)
    recipe = quantizer.generate_quantization_recipe("Qwen3.6-35B-A3B", input_size_gb=70.0)
    assert recipe["precision"] == "w4a16"
    assert recipe["estimated_output_size_gb"] <= 22.0  # 70 * 0.30 = 21.0 GB
    assert recipe["fits_in_uma_aperture"] is True
    assert recipe["recommended_runtime"] == "lemonade"

    export_res = quantizer.export_quantized_model("Qwen3.6-35B-A3B", recipe, dry_run=True)
    assert export_res["status"] == "dry_run_ready"
    assert "w4a16.gguf" in export_res["output_path"]


def test_strix_halo_optimizer_wave32() -> None:
    """Verify StrixHaloSiliconOptimizer enforces Wave32 alignment for gfx1151."""
    optimizer = StrixHaloSiliconOptimizer()
    assert optimizer.verify_wave32_alignment() is True
    flags = optimizer.get_optimal_compilation_flags()
    assert "-mwavefrontsize32" in flags
