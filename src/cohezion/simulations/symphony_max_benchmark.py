"""Symphony Max Live-Hardware Benchmark.
Validates the full Sensing -> Synthesis -> Steering pipeline on target hardware
with real-time telemetry and latency tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict
import numpy as np
import aiohttp

from cohezion.swarm.providers.gemma4_provider import Gemma4Provider
from cohezion.flume.manifolds.translator import ManifoldTranslator
from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.flume.spectral_encoder import SpectralEncoder
from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop
from cohezion.compound.executor import CompoundExecutor
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class SymphonyMaxBenchmark:
    def __init__(self):
        # Real provider for hardware telemetry (not mock)
        self.provider = Gemma4Provider()
        self.encoder = FlumeVAEEncoder()
        self.spectral_encoder = SpectralEncoder(encoder=self.encoder)
        self.translator = ManifoldTranslator(encoder=self.encoder)
        self.agent = EcoResilienceAgent(
            provider=self.provider,
            translator=self.translator,
            spectral_encoder=self.spectral_encoder,
            model_name="gemma4:26b",
        )

        self.guard = HIHOStabilityGuard(threshold=0.5)
        self.mock_mcp = MagicMock()
        self.executor = CompoundExecutor(mcp_client=self.mock_mcp)
        self.loop = EcoResilienceCompoundLoop(
            agent=self.agent, executor=self.executor, guard=self.guard
        )

        self.metrics = {"regimes": {}, "total_latency": 0.0, "stability_curve": []}

    async def _check_connectivity(self):
        """Pings NPU and GPU endpoints to ensure Lemonade is active."""
        endpoints = {
            "NPU": "http://localhost:11435/api/tags",
            "GPU": "http://localhost:11434/api/tags",
        }
        results = {}
        async with aiohttp.ClientSession() as session:
            for name, url in endpoints.items():
                try:
                    async with session.get(url, timeout=2) as resp:
                        results[name] = resp.status == 200
                except Exception:
                    results[name] = False
        return results

    async def benchmark_pipeline(self, scenario: str):
        logger.info("🚀 STARTING SYMPHONY MAX LIVE-HARDWARE BENCHMARK")
        logger.info("=" * 60)

        # Connectivity Guard
        connectivity = await self._check_connectivity()
        if not connectivity["GPU"]:
            logger.error(f"❌ Critical Hardware Failure: GPU (11434) is offline. Cannot benchmark.")
            return

        if not connectivity["NPU"]:
            logger.warning(
                f"⚠️ NPU (11435) is offline. Falling back to GPU-SOTA mode for proxy data."
            )
            logger.info("Note: Final submission must be validated on NPU for 'Symphony Max' claim.")

        # --- BENCHMARK COMPARISON SETS ---

        # --- BENCHMARK COMPARISON SETS ---
        # We compare 'SOTA' (MXFP4 + Pruning) vs 'Standard' (FP16/None)
        configs = {
            "SOTA (MXFP4_Optimized)": {"mxfp4": True, "pruning": True},
            "Standard (Baseline)": {"mxfp4": False, "pruning": False},
        }

        all_results = {}

        for config_name, settings in configs.items():
            logger.info(f"Running mode: {config_name}...")

            # We need to communicate the setting to the provider.
            # Since the loop internally calls generate, we can set a global override
            # or pass it through the agent. For the benchmark, we'll inject it into the provider's config.
            self.provider.config["benchmark_mxfp4"] = settings["mxfp4"]
            self.provider.config["benchmark_pruning"] = settings["pruning"]

            start_time = time.perf_counter()
            try:
                # We force benchmark_mode=True to avoid multiple iterations and timeouts
                result = await self.loop.run_stable_simulation(scenario, benchmark_mode=True)
                end_time = time.perf_counter()

                all_results[config_name] = {
                    "latency": end_time - start_time,
                    "stability": result.stability_score,
                    "iterations": result.iterations,
                }
            except Exception as e:
                logger.exception(f"Benchmark failed for {config_name}: {e}")

        # Calculate Delta
        if "SOTA (MXFP4_Optimized)" in all_results and "Standard (Baseline)" in all_results:
            sota = all_results["SOTA (MXFP4_Optimized)"]["latency"]
            std = all_results["Standard (Baseline)"]["latency"]
            improvement = ((std - sota) / std) * 100

            logger.info("\n" + "═" * 60)
            logger.info("📊 SYMPHONY MAX COMPARATIVE TELEMETRY")
            logger.info("═" * 60)
            logger.info(f"Standard Latency:  {std:.4f}s")
            logger.info(f"SOTA Latency:      {sota:.4f}s")
            logger.info(f"Performance Gain:   {improvement:.2f}% 🚀")
            logger.info("═" * 60)

        return all_results


async def main():
    benchmark = SymphonyMaxBenchmark()
    scenario = (
        "FIELD REPORT - SUNDARBANS: Significant salt-water intrusion. "
        "Tigers migrating inland. Traditional knowledge suggests 'Sabu-Sabu' la-phase."
    )
    await benchmark.benchmark_pipeline(scenario)


if __name__ == "__main__":
    asyncio.run(main())
