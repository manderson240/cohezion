"""
Real-world Routing Classifier Harness (Task 2.2)

Ingests extracted real-world prompts and validates they classify cleanly
through the task classifier.
"""

import json
from pathlib import Path

import pytest

from cohezion.inference.task_classifier import RouteDecision, classify


def test_real_world_prompts_classification():
    """Verify that all extracted real-world prompts classify without exception."""
    path = Path("execution_traces/extracted_prompts.json")
    if not path.exists():
        pytest.skip("No extracted prompts file found. Run scripts/extract_real_prompts.py first.")

    with open(path, encoding="utf-8") as f:
        prompts = json.load(f)

    if not prompts:
        pytest.skip("Extracted prompts list is empty.")

    print(f"\nRunning task classification validation on {len(prompts)} real-world prompts...")
    for idx, prompt in enumerate(prompts):
        try:
            decision = classify(prompt)
            assert isinstance(decision, RouteDecision), (
                f"Expected RouteDecision, got {type(decision)}"
            )
            assert decision.node in ("npu", "gpu", "cpu", "cloud"), f"Invalid node: {decision.node}"
            assert decision.confidence >= 0.0, f"Negative confidence: {decision.confidence}"
        except Exception as e:
            pytest.fail(f"Prompt #{idx} failed classification. Prompt: {prompt!r} | Error: {e}")

    print("✅ All real-world prompts classified successfully.")
