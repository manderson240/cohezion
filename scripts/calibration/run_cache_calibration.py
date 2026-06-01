#!/usr/bin/env python3
"""Semantic Cache Threshold Calibration Script (ID-3).

Sweeps L2 cosine thresholds to maximize near-duplicate hit rate while preventing
false positive semantic collisions, utilizing the Unified Calibration Harness.
"""

import asyncio
import contextlib
import logging
import sys
from pathlib import Path


# Ensure src/ is in the python path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from cohezion.cache.semantic_cache import SemanticCache  # noqa: E402
from cohezion.validation.calibration_harness import (  # noqa: E402
    load_local_logs,
    run_parameter_sweep,
    save_calibration_profile,
)


def jaccard_similarity(s1: str, s2: str) -> float:
    """Compute word-level Jaccard similarity between two strings."""
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 and not w2:
        return 1.0
    return len(w1 & w2) / len(w1 | w2)


async def evaluate_cache_threshold(samples: list[dict], candidate: dict) -> dict:
    """Evaluates the cache hit and collision rates for a given threshold."""
    threshold = candidate["similarity_threshold"]

    # Temporarily set the environment variable to bypass loading the profile we're writing
    import os

    os.environ["COHEZION_IGNORE_CALIBRATION_PROFILE"] = "1"

    # Initialize a clean cache instance for this run
    cache = SemanticCache(similarity_threshold=threshold, enable_adaptive_threshold=False)

    total_lookups = 0
    hits = 0
    collisions = 0  # Hits where text is radically different (Jaccard < 0.25)
    valid_hits = 0

    # Ingest and check sequentially
    for sample in samples:
        prompt = sample["prompt"]
        response = sample["response"] or "dummy_response"

        # 1. Check lookup
        match = await cache.get(prompt)
        total_lookups += 1

        if match is not None:
            hits += 1
            # Check for semantic collision
            jacc = jaccard_similarity(prompt, match)
            if jacc < 0.25:
                collisions += 1
            else:
                valid_hits += 1
        else:
            # 2. Ingest on miss
            with contextlib.suppress(Exception):
                await cache.put(prompt, response)

    hit_rate = (hits / total_lookups) * 100 if total_lookups > 0 else 0
    collision_rate = (collisions / hits) * 100 if hits > 0 else 0
    valid_hit_rate = (valid_hits / total_lookups) * 100 if total_lookups > 0 else 0

    return {
        "total_lookups": total_lookups,
        "hits": hits,
        "valid_hits": valid_hits,
        "collisions": collisions,
        "hit_rate_pct": round(hit_rate, 2),
        "collision_rate_pct": round(collision_rate, 2),
        "valid_hit_rate_pct": round(valid_hit_rate, 2),
    }


async def main():
    logger.info("Starting Semantic Cache Threshold Calibration...")

    # Load local logs (sanitized & PII-redacted)
    samples = list(load_local_logs(min_len=50))
    if not samples:
        logger.error("No prompt logs found to sweep. Exiting.")
        sys.exit(1)

    logger.info("Loaded %d prompt samples for sweep.", len(samples))

    # Define candidate parameter grid
    thresholds = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    param_grid = [{"similarity_threshold": t} for t in thresholds]

    # Run parameter sweep securely under OOM guardrails
    try:
        sweep_results = await run_parameter_sweep(
            samples, evaluate_cache_threshold, param_grid, min_ram_mb=12288
        )
    except Exception as e:
        logger.error("Sweep execution failed: %s", e)
        sys.exit(1)

    # Print markdown results table
    print("\n# Semantic Cache Threshold Sweep Report\n")
    print(
        "| Threshold | Total Lookups | Hits | Valid Hits | Collisions | Hit Rate | Collision Rate | Valid Hit Rate |"
    )
    print("|---|---|---|---|---|---|---|---|")

    optimal_threshold = 0.80
    best_valid_hit_rate = -1.0

    for res in sweep_results:
        cand = res["candidate"]
        metrics = res["metrics"]
        t = cand["similarity_threshold"]

        if "error" in metrics:
            print(f"| {t:.2f} | ERROR: {metrics['error']} |")
            continue

        print(
            f"| {t:.2f} | {metrics['total_lookups']} | {metrics['hits']} | "
            f"{metrics['valid_hits']} | {metrics['collisions']} | "
            f"{metrics['hit_rate_pct']}% | {metrics['collision_rate_pct']}% | {metrics['valid_hit_rate_pct']}% |"
        )

        # Optimization Criteria: Maximize valid hit rate, keeping collision rate below 5%
        # (Zero false positives / near-dup collisions threshold)
        if (
            metrics["collision_rate_pct"] <= 5.0
            and metrics["valid_hit_rate_pct"] > best_valid_hit_rate
        ):
            best_valid_hit_rate = metrics["valid_hit_rate_pct"]
            optimal_threshold = t

    print(f"\n**Recommended Optimal Similarity Threshold:** {optimal_threshold:.2f}")

    # Save to configuration profile atomically
    logger.info("Saving optimized parameters for semantic_cache...")
    save_calibration_profile("semantic_cache", {"similarity_threshold": optimal_threshold})
    logger.info("Calibrated parameters successfully saved.")


if __name__ == "__main__":
    asyncio.run(main())
