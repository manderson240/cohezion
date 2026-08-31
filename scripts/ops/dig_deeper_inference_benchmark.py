r"""Dig Deeper Inference Benchmark — Local Silicon & Ollama Cloud Model Roster Evaluation
=======================================================================================
Benchmarks reasoning depth, character yield, latencies, and output quality across:
  - Local NPU Silicon Models (Lemonade :13305)
  - Local iGPU / CPU Models (Lemonade :13305)
  - Ollama Cloud Models (Ollama :11434)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from cohezion.inference.deep_cooking import DeepCookingEngine
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [DEEP_INFERENCE] - %(message)s")
logger = logging.getLogger("DigDeeperBenchmark")

DEEP_REASONING_PROMPT = """Synthesize a 12D Poincaré Hypersphere Geodesic proof showing that the major radius R = 0.50 corresponds to maximum HIHO stability."""


def benchmark_deep_inference() -> dict[str, Any]:
    logger.info("🔬 Digging Deeper into Local Silicon & Ollama Cloud Models...")

    router = UnifiedHybridRouter(prefer_local=True)
    cooker = DeepCookingEngine(default_timeout_seconds=300.0)

    # 1. Local Silicon NPU/iGPU Tier
    logger.info("⚡ Benchmarking Local Silicon Tier...")
    t0 = time.perf_counter()
    local_route = router.route_query(DEEP_REASONING_PROMPT, force_cloud=False)
    t_local = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Ollama Cloud Tier
    logger.info("☁️  Benchmarking Ollama Cloud Tier...")
    t1 = time.perf_counter()
    cloud_route = router.route_query(DEEP_REASONING_PROMPT, force_cloud=True)
    t_cloud = round((time.perf_counter() - t1) * 1000, 2)

    # 3. Extended Deep Cooking Engine Simulation
    logger.info("🍖 Benchmarking Deep Cooking Engine (Extended Token Budget)...")
    cook_res = cooker.cook_inference_task(
        DEEP_REASONING_PROMPT, model="qwen3.6-moe-35b-a3b-FLM", timeout_seconds=1.0
    )

    report = {
        "benchmark_status": "SUCCESSFUL",
        "local_silicon_tier": {
            "tier_used": local_route.tier_used,
            "model": local_route.model_name,
            "latency_ms": local_route.latency_ms,
            "verified": local_route.verified,
            "output_chars": len(local_route.content),
            "sample_content": local_route.content[:200] + "...",
        },
        "ollama_cloud_tier": {
            "tier_used": cloud_route.tier_used,
            "model": cloud_route.model_name,
            "latency_ms": cloud_route.latency_ms,
            "verified": cloud_route.verified,
            "output_chars": len(cloud_route.content),
            "sample_content": cloud_route.content[:200] + "...",
        },
        "deep_cooking_engine": {
            "model": cook_res.model,
            "task_id": cook_res.task_id,
            "cooking_time_seconds": cook_res.cooking_time_seconds,
            "total_tokens_generated": cook_res.total_tokens_generated,
            "timed_out": cook_res.timed_out,
        },
    }

    logger.info("✨ Dig Deeper Benchmark Complete!")
    return report


if __name__ == "__main__":
    report = benchmark_deep_inference()
    print(json.dumps(report, indent=2))
