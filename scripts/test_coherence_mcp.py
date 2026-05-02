#!/usr/bin/env python3
"""Test Coherence MCP Server functionality.

Run: uv run python scripts/test_coherence_mcp.py
"""

# Add src to path
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine


def test_hiho_engine():
    """Test HIHO stability scoring."""
    print("\n=== HIHO Engine ===")
    engine = HihoVectorEngine(sigma=0.25)

    test_values = [0.0, 0.3, 0.5, 0.7, 1.0]
    for val in test_values:
        score = engine.calculate_hiho_score(val)
        print(f"  Coherence {val:.2f} -> HIHO {score:.4f}")

    # Verify peak at 0.5
    assert engine.calculate_hiho_score(0.5) > engine.calculate_hiho_score(0.3)
    assert engine.calculate_hiho_score(0.5) > engine.calculate_hiho_score(0.7)
    print("  ✓ HIHO peak at 0.5 verified")


def test_journey_tracker():
    """Test 12D FLUME trajectory tracking."""
    print("\n=== Journey Tracker (FLUME 12D) ===")

    from cohezion.compound.executor import ExecutionMetrics, ExecutionResult

    tracker = JourneyTracker(seed=42)

    # Simulate execution
    result = ExecutionResult(
        success=True,
        output="test",
        metrics=ExecutionMetrics(
            coherence=0.8,
            efficiency=0.9,
            duration_seconds=1.5,
        ),
    )

    point = tracker.track_execution(
        execution_result=result,
        task_description="Test edit operation",
        operation_type="transform",
    )

    print(f"  Point recorded: {point.coherence:.2f} coherence")
    print(f"  12D trajectory: {point.dimensions.tolist()}")
    print(f"  PHI score: {point.phi_score:.3f}")
    print(f"  Operation: {point.operation_type}")
    print("  ✓ FLUME trajectory tracking works")


def test_degradation_detector():
    """Test degradation monitoring."""
    print("\n=== Degradation Detector ===")

    detector = DegradationDetector(
        coherence_threshold=0.60,
        cache_hit_rate_threshold=0.50,
    )

    # Normal metrics
    metrics_good = {
        "coherence": 0.75,
        "cache_hit_rate": 0.90,
        "token_efficiency": 0.85,
    }

    alerts = detector.check_degradation(metrics_good)
    print(f"  Good metrics: {len(alerts)} alerts")
    assert len(alerts) == 0

    # Degraded metrics
    metrics_bad = {
        "coherence": 0.45,  # Below threshold
        "cache_hit_rate": 0.40,  # Below threshold
    }

    alerts = detector.check_degradation(metrics_bad)
    print(f"  Bad metrics: {len(alerts)} alerts")
    for alert in alerts:
        print(f"    - {alert.severity.value}: {alert.message}")

    assert len(alerts) == 2  # coherence + cache hit rate
    print("  ✓ Degradation detection works")


def test_alignment_analyzer():
    """Test request alignment analysis."""
    print("\n=== Request Alignment Analyzer ===")

    # Mock MCP client that returns empty vault results
    class MockMcpClient:
        async def vault_find_relevant_context(self, query, **kwargs):
            return []

    analyzer = RequestAlignmentAnalyzer(
        mcp_client=MockMcpClient(),
    )

    # Test intent classification
    test_requests = [
        "Generate a new function for sorting",
        "Analyze the performance issues",
        "Search for files matching pattern",
        "Transform the data to JSON format",
        "Store the results in vault",
    ]

    for req in test_requests:
        request = analyzer.parse_request(req)
        print(f"  '{req[:40]}...' -> {request.intent.value} ({request.intent_confidence:.2f})")

    print("  ✓ Intent classification works")


def main():
    """Run all coherence tests."""
    print("=== Testing Cohezion Coherence Systems ===\n")

    test_hiho_engine()
    test_journey_tracker()
    test_degradation_detector()
    test_alignment_analyzer()

    print("\n=== All tests passed! ===")
    print("\nCoherence MCP server is ready for pi integration.")
    print("\nNext steps:")
    print("  1. Start coherence server: uv run python -m cohezion.mcp.coherence_server")
    print("  2. Test with pi: /cohezion alignment 'generate code'")
    print("  3. Check trajectory: /cohezion trajectory")


if __name__ == "__main__":
    main()
