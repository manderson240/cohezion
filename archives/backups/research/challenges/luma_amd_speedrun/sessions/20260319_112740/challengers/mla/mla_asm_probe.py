#!/usr/bin/env python3
"""
MLA-ASM-Probe Agent for Luma AMD Speedrun Competition
Purpose: Profile and explore AITER MLA implementation to identify optimization paths

NOTE: This script uses only public/documented APIs. Performance gaps may stem from:
- Algorithmic differences (not just kernel implementation)
- Precision settings (FP8 vs FP16 vs BF16)
- Memory layout optimizations
- Batch size and sequence length configurations
- Hardware-specific tuning parameters

The 4.3µs leader performance likely uses fundamentally different approach,
not just hidden kernel names.
"""

import logging
import os
import time
from typing import Any

import torch


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MLAProbeAgent:
    """
    Probes AITER MLA implementation through legitimate channels.
    Focuses on configuration exploration, not undocumented internals.
    """

    def __init__(self, device: str = "cuda"):
        self.device = device
        self.discoveries: dict[str, Any] = {}
        self.performance_log: list = []

    def probe_module_structure(self, module_name: str = "aiter") -> dict[str, Any]:
        """
        Explore module structure through public introspection.
        Does NOT access private/undocumented attributes.
        """
        logger.info(f"Probing module: {module_name}")

        try:
            import importlib

            module = importlib.import_module(module_name)

            structure = {
                "name": module_name,
                "file": getattr(module, "__file__", "N/A"),
                "public_attrs": [],
                "functions": [],
                "classes": [],
            }

            # Only inspect public attributes (no leading underscore)
            for attr_name in dir(module):
                if not attr_name.startswith("_"):
                    attr = getattr(module, attr_name)
                    if callable(attr):
                        structure["functions"].append(attr_name)
                    elif isinstance(attr, type):
                        structure["classes"].append(attr_name)
                    else:
                        structure["public_attrs"].append(attr_name)

            self.discoveries["module_structure"] = structure
            logger.info(f"Found {len(structure['functions'])} public functions")

            return structure

        except ImportError as e:
            logger.error(f"Module {module_name} not available: {e}")
            return {}

    def benchmark_mla_variant(self, variant_name: str, **kwargs) -> float:
        """
        Benchmark different MLA configurations through public API.
        Records latency for comparison.
        """
        logger.info(f"Benchmarking variant: {variant_name}")

        # Warmup
        for _ in range(5):
            self._run_mla_test(**kwargs)

        # Timed run
        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            self._run_mla_test(**kwargs)
            if self.device == "cuda":
                torch.cuda.synchronize()
            end = time.perf_counter()
            latencies.append((end - start) * 1e6)  # Convert to µs

        avg_latency = sum(latencies) / len(latencies)
        self.performance_log.append(
            {"variant": variant_name, "latency_us": avg_latency, "kwargs": kwargs}
        )

        logger.info(f"{variant_name}: {avg_latency:.2f}µs")
        return avg_latency

    def _run_mla_test(
        self,
        batch_size: int = 1,
        seq_len: int = 128,
        hidden_dim: int = 512,
        dtype: torch.dtype = torch.float16,
        **kwargs,
    ) -> torch.Tensor:
        """
        Run a standard MLA computation test.
        Uses public PyTorch APIs only.
        """
        # Create test tensors
        q = torch.randn(batch_size, seq_len, hidden_dim, dtype=dtype, device=self.device)
        k = torch.randn(batch_size, seq_len, hidden_dim, dtype=dtype, device=self.device)
        v = torch.randn(batch_size, seq_len, hidden_dim, dtype=dtype, device=self.device)

        # Standard attention computation
        if kwargs.get("use_fused", False):
            # Try fused attention if available
            try:
                import torch.nn.functional as F

                attn_out = F.scaled_dot_product_attention(q, k, v)
            except:
                attn_out = self._manual_attention(q, k, v)
        else:
            attn_out = self._manual_attention(q, k, v)

        return attn_out

    def _manual_attention(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
        """Manual attention implementation for baseline comparison."""
        scale = q.shape[-1] ** -0.5
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * scale
        attn_weights = torch.softmax(attn_weights, dim=-1)
        return torch.matmul(attn_weights, v)

    def explore_env_variables(self) -> dict[str, str]:
        """
        Log relevant environment variables that might affect performance.
        Only reads variables, does not set undocumented ones.
        """
        relevant_vars = [
            "CUDA_VISIBLE_DEVICES",
            "PYTORCH_CUDA_ALLOC_CONF",
            "HIP_VISIBLE_DEVICES",  # For AMD
            "ROCM_PATH",
            "AITER_*",  # Pattern match for AITER vars
        ]

        env_vars = {}
        for key, value in os.environ.items():
            if any(pattern.replace("*", "") in key for pattern in relevant_vars):
                env_vars[key] = value

        self.discoveries["env_vars"] = env_vars
        logger.info(f"Found {len(env_vars)} relevant env vars")
        return env_vars

    def try_aiter_import(self) -> bool:
        """
        Attempt to import AITER through public API.
        Falls back gracefully if not available.
        """
        try:
            import aiter

            logger.info("AITER module imported successfully")
            self.discoveries["aiter_available"] = True
            return True
        except ImportError:
            logger.warning("AITER not available, using PyTorch fallback")
            self.discoveries["aiter_available"] = False
            return False

    def generate_report(self) -> str:
        """
        Generate summary report of discoveries.
        """
        report = []
        report.append("=" * 60)
        report.append("MLA PROBE AGENT DISCOVERY REPORT")
        report.append("=" * 60)

        report.append(f"\nDevice: {self.device}")
        report.append(f"AITER Available: {self.discoveries.get('aiter_available', False)}")

        if self.performance_log:
            report.append("\nPerformance Benchmarks:")
            for entry in self.performance_log:
                report.append(f"  {entry['variant']}: {entry['latency_us']:.2f}µs")

        if "env_vars" in self.discoveries:
            report.append("\nEnvironment Variables:")
            for key, value in self.discoveries["env_vars"].items():
                report.append(f"  {key}={value}")

        report.append("\nNOTE: 4.3µs leader performance likely requires:")
        report.append("  - Algorithmic optimization (not just kernel tuning)")
        report.append("  - Hardware-specific ASM kernels (vendor-provided)")
        report.append("  - Memory layout optimizations (persistent caching)")
        report.append("  - Precision reduction (FP8/INT8 if supported)")

        return "\n".join(report)

    def run_full_probe(self) -> dict[str, Any]:
        """
        Execute complete probing sequence.
        """
        logger.info("Starting MLA Probe Agent...")

        # 1. Check environment
        self.explore_env_variables()

        # 2. Try AITER import
        aiter_available = self.try_aiter_import()

        # 3. Probe module structure if available
        if aiter_available:
            self.probe_module_structure("aiter")

        # 4. Benchmark variants
        variants = [
            ("baseline", {"use_fused": False}),
            ("fused", {"use_fused": True}),
            ("fp16", {"dtype": torch.float16}),
            ("bf16", {"dtype": torch.bfloat16}),
        ]

        for variant_name, kwargs in variants:
            try:
                self.benchmark_mla_variant(variant_name, **kwargs)
            except Exception as e:
                logger.error(f"Variant {variant_name} failed: {e}")

        # 5. Generate report
        report = self.generate_report()
        print(report)

        return self.discoveries


def main():
    """
    Main entry point for MLA Probe Agent.
    """
    # Detect device (AMD vs NVIDIA)
    if torch.cuda.is_available():
        device = "cuda"
        logger.info("CUDA available")
    elif torch.backends.mps.is_available():
        device = "mps"
        logger.info("MPS available")
    else:
        device = "cpu"
        logger.warning("No GPU available, using CPU")

    # Initialize probe agent
    agent = MLAProbeAgent(device=device)

    # Run full probe sequence
    discoveries = agent.run_full_probe()

    # Output summary
    print("\n" + "=" * 60)
    print("PROBE COMPLETE")
    print("=" * 60)
    print(f"Best measured latency: {min([p['latency_us'] for p in agent.performance_log]):.2f}µs")
    print("Leader target: 4.3µs")
    print(f"Gap: {min([p['latency_us'] for p in agent.performance_log]) / 4.3:.1f}x")
    print("\nRecommendation: Contact library maintainers for optimized kernel access")
    print("or explore algorithmic optimizations beyond kernel implementation.")

    return discoveries


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Probe agent failed: {e}")
        # Fallback: basic PyTorch attention benchmark
        print("FALLBACK: Running basic PyTorch attention benchmark...")
        import time

        import torch

        q = torch.randn(
            1, 128, 512, dtype=torch.float16, device="cuda" if torch.cuda.is_available() else "cpu"
        )
        k = torch.randn(
            1, 128, 512, dtype=torch.float16, device="cuda" if torch.cuda.is_available() else "cpu"
        )
        v = torch.randn(
            1, 128, 512, dtype=torch.float16, device="cuda" if torch.cuda.is_available() else "cpu"
        )

        for _ in range(10):
            start = time.perf_counter()
            attn = torch.nn.functional.scaled_dot_product_attention(q, k, v)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            end = time.perf_counter()
            print(f"Latency: {(end - start) * 1e6:.2f}µs")
