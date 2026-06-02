#!/usr/bin/env python3
"""Script to verify and demonstrate calibration profile loading at runtime."""

import sys
from pathlib import Path


# Ensure src/ is in the python path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir / "src"))

import cohezion.inference.task_classifier as tc  # noqa: E402
from cohezion.cache.semantic_cache import SemanticCache  # noqa: E402


def main():
    print("=== Cohezion Calibration Integration Verification ===")

    # 1. Semantic Cache Threshold
    print("\n1. Verifying Semantic Cache Dynamic Load:")
    cache = SemanticCache()
    print(f"  * Calibrated similarity_threshold active at runtime: {cache.similarity_threshold}")

    # 2. Task Classifier Overrides
    print("\n2. Verifying Task Classifier Routing Overrides:")
    # Run a classification to trigger lazy load
    tc.classify("hello")
    overrides = tc._calibrated_overrides
    print(f"  * Calibrated parameters loaded: {overrides}")

    # 3. Classify sample prompts
    print("\n3. Classifying Sample Prompts:")
    prompts = [
        "Are we on the newest version?",  # short status question (<=90 chars) -> NPU
        "fix the bot in fleet.py to use get_circuit()",  # engineering command -> GPU
        "what is a latent state vector?",  # short definitional question -> NPU
    ]
    for prompt in prompts:
        dec = tc.classify(prompt)
        print(f"  * Prompt: '{prompt}'")
        print(f"    -> Routed to: {dec.node.upper()} ({dec.output_type}) | Reason: {dec.reason}")


if __name__ == "__main__":
    main()
