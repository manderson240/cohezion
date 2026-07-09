#!/usr/bin/env python3
"""Task Classifier Routing Calibration Script (ID-3).

Sweeps classifier length thresholds to minimize routing anomalies (false negatives
for code and false positives for simple prompts), utilizing the Unified Harness.
"""

import asyncio
import logging
import re
import sys
from pathlib import Path


# Ensure src/ is in the python path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

import cohezion.inference.task_classifier as task_classifier  # noqa: E402
from cohezion.inference.task_classifier import RouteDecision  # noqa: E402
from cohezion.validation.calibration_harness import (  # noqa: E402
    load_local_logs,
    run_parameter_sweep,
    save_calibration_profile,
)


def is_potential_misclassification(prompt: str, decision: RouteDecision) -> bool:
    """Detect heuristic indicators of routing anomalies (FN/FP)."""
    prompt_lower = prompt.lower()

    # 1. False Negatives (Should be GPU, but routed to NPU)
    if decision.node == "npu":
        if "```" in prompt:
            return True
        if re.search(
            r"(?:^|[\n\t])[ \t]*(def |class |import |from \w+ import |#include|func |fn )",
            prompt,
        ):
            return True
        code_verbs = r"\b(write|implement|create|generate|build|refactor|rewrite|debug|optimize)\b"
        code_nouns = r"\b(function|class|method|module|code|script|test|tests|endpoint|api|schema|pipeline)\b"
        if re.search(code_verbs, prompt_lower) and re.search(code_nouns, prompt_lower):
            return True
        if re.search(
            r"\b(unit|integration|e2e|smoke|regression|pytest|jest)\s+test\b", prompt_lower
        ):
            return True

    # 2. False Positives (Should be NPU, but routed to GPU)
    elif decision.node == "gpu":
        if re.search(
            r"\b(yes/no|yes or no|true or false|one word|one letter|multiple choice)\b",
            prompt_lower,
        ):
            return True
        if len(prompt) < 100 and "defaulting to GPU" in decision.reason:
            return True

    return False


def evaluate_routing_parameters(samples: list[dict], candidate: dict) -> dict:
    """Evaluates routing anomalies for a given candidate parameters dict."""
    # Inject overrides directly into the module's cached overrides state for this evaluation run
    import os

    os.environ["COHEZION_IGNORE_CALIBRATION_PROFILE"] = "1"
    task_classifier._calibrated_overrides = candidate
    task_classifier._overrides_loaded = True

    total = 0
    anomalies = 0
    gpu_count = 0
    npu_count = 0

    for sample in samples:
        prompt = sample["prompt"]
        decision = task_classifier.classify(prompt)
        total += 1

        if decision.node == "gpu":
            gpu_count += 1
        else:
            npu_count += 1

        if is_potential_misclassification(prompt, decision):
            anomalies += 1

    anomaly_rate = (anomalies / total) * 100 if total > 0 else 0
    gpu_pct = (gpu_count / total) * 100 if total > 0 else 0

    return {
        "total": total,
        "anomalies": anomalies,
        "anomaly_rate_pct": round(anomaly_rate, 2),
        "gpu_pct": round(gpu_pct, 2),
    }


async def main():
    logger.info("Starting Task Classifier Routing Calibration...")

    # Load local logs
    samples = list(load_local_logs(min_len=50))
    if not samples:
        logger.error("No prompt logs found to sweep. Exiting.")
        sys.exit(1)

    logger.info("Loaded %d prompt samples for sweep.", len(samples))

    # Grid of candidate configurations
    param_grid = [
        # Baseline
        {
            "status_question_max_len": 90,
            "short_what_is_max_len": 75,
            "how_does_max_len": 85,
            "fallback_short_max_len": 150,
            "fallback_medium_max_len": 400,
        },
        # Conservative (routes to NPU more aggressively)
        {
            "status_question_max_len": 110,
            "short_what_is_max_len": 90,
            "how_does_max_len": 100,
            "fallback_short_max_len": 180,
            "fallback_medium_max_len": 450,
        },
        # Aggressive GPU (lowers thresholds, routes to GPU earlier)
        {
            "status_question_max_len": 70,
            "short_what_is_max_len": 60,
            "how_does_max_len": 70,
            "fallback_short_max_len": 120,
            "fallback_medium_max_len": 300,
        },
        # Balanced Option 1
        {
            "status_question_max_len": 90,
            "short_what_is_max_len": 80,
            "how_does_max_len": 90,
            "fallback_short_max_len": 140,
            "fallback_medium_max_len": 350,
        },
        # Balanced Option 2
        {
            "status_question_max_len": 95,
            "short_what_is_max_len": 75,
            "how_does_max_len": 85,
            "fallback_short_max_len": 130,
            "fallback_medium_max_len": 380,
        },
    ]

    # Run parameter sweep securely under OOM guardrails (8GB RAM safe buffer for pure CPU regex checks)
    try:
        sweep_results = await run_parameter_sweep(
            samples, evaluate_routing_parameters, param_grid, min_ram_mb=8192
        )
    except Exception as e:
        logger.error("Sweep execution failed: %s", e)
        sys.exit(1)

    # Print markdown results table
    print("\n# Task Classifier Routing Sweep Report\n")
    print(
        "| Conf | Status Len | WhatIs Len | HowDoes Len | Short Len | Med Len | Anomalies | Anomaly Rate | GPU % |"
    )
    print("|---|---|---|---|---|---|---|---|---|")

    optimal_config = param_grid[0]
    best_anomaly_rate = 100.0

    for i, res in enumerate(sweep_results, 1):
        cand = res["candidate"]
        metrics = res["metrics"]

        if "error" in metrics:
            print(f"| C{i} | ERROR: {metrics['error']} |")
            continue

        print(
            f"| C{i} | {cand['status_question_max_len']} | {cand['short_what_is_max_len']} | "
            f"{cand['how_does_max_len']} | {cand['fallback_short_max_len']} | {cand['fallback_medium_max_len']} | "
            f"{metrics['anomalies']} | {metrics['anomaly_rate_pct']}% | {metrics['gpu_pct']}% |"
        )

        # Optimization Criteria: Minimize anomalies
        if metrics["anomaly_rate_pct"] < best_anomaly_rate:
            best_anomaly_rate = metrics["anomaly_rate_pct"]
            optimal_config = cand

    print("\n**Recommended Optimal Routing Config:**")
    for k, v in optimal_config.items():
        print(f"* **{k}:** {v}")

    # Save config profile atomically
    logger.info("Saving optimized parameters for task_classifier...")
    save_calibration_profile("task_classifier", optimal_config)
    logger.info("Calibrated parameters successfully saved.")


if __name__ == "__main__":
    asyncio.run(main())
