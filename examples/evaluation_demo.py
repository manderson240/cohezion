#!/usr/bin/env python3
"""Demo: Cohezion evaluation systems for agentic AI.

Shows the evaluation pipeline that measures agent capability through
continuous trajectory analysis rather than pass/fail benchmarks:

1. Journey tracking in 12D manifold space
2. Coherence-based quality scoring (phi score)
3. Degradation detection and anomaly flagging
4. Request alignment analysis

Usage:
    uv run python examples/evaluation_demo.py
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.journey_tracker import JourneyTrackerFactory


def main() -> None:
    # --- Journey Tracking ---
    # Track agent execution as trajectory in 12D projected space
    tracker = JourneyTrackerFactory.create(seed=42)
    print("=== Journey Tracking (12D Holographic Projection) ===\n")

    # Simulate a sequence of agent executions
    from cohezion.compound.executor import ExecutionResult

    operations = [
        ("research", "Analyze quantum coherence patterns"),
        ("generate", "Synthesize stability report"),
        ("analyze", "Evaluate manifold topology"),
        ("test", "Validate coherence invariants"),
        ("deploy", "Publish results to knowledge graph"),
    ]

    points = []
    for op_type, description in operations:
        # Create a mock execution result
        result = ExecutionResult(
            success=True,
            output=f"Completed: {description}",
            metrics={"coherence": 0.5 + np.random.normal(0, 0.05)},
            duration_seconds=1.2,
        )

        point = tracker.track_execution(
            execution_result=result,
            task_description=description,
            operation_type=op_type,
        )
        points.append(point)

        print(f"  [{op_type:>10}] {description}")
        print(
            f"             12D coords (first 4): [{', '.join(f'{d:.3f}' for d in point.dimensions[:4])}...]"
        )
        print(f"             phi_score={point.metadata.get('phi_score', 0):.3f}")
        print()

    # --- Trajectory Quality Analysis ---
    print("=== Trajectory Quality Analysis ===\n")
    quality = tracker.compute_trajectory_quality(points)
    for key, value in quality.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # --- Degradation Detection ---
    print("\n=== Degradation Detection ===\n")
    from cohezion.compound.degradation_detector import DegradationDetector

    detector = DegradationDetector()

    # Feed a healthy coherence sequence
    healthy_sequence = [0.48, 0.51, 0.49, 0.52, 0.50]
    for c in healthy_sequence:
        detector.record_coherence(c)

    status = detector.get_status()
    print(f"  Healthy sequence {healthy_sequence}")
    print(f"  Status: {status}")

    # Feed a degrading sequence
    degrading_sequence = [0.45, 0.38, 0.30, 0.22, 0.15]
    for c in degrading_sequence:
        detector.record_coherence(c)

    status = detector.get_status()
    print(f"\n  Degrading sequence {degrading_sequence}")
    print(f"  Status: {status}")

    # --- Request Alignment ---
    print("\n=== Request Alignment Analysis ===\n")
    from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

    _ = RequestAlignmentAnalyzer()
    print("  Alignment analysis assesses coherence between request,")
    print("  skills, and agent context before execution begins —")
    print("  preventing wasted compute on misaligned tasks.")
    print("  See: src/cohezion/compound/request_alignment_analyzer.py")


if __name__ == "__main__":
    main()
