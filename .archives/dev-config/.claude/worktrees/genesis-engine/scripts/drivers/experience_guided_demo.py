#!/usr/bin/env python3
"""Demonstration of Phase 9: Experience-Guided Execution Loop.

Shows how the compound learning loop works:
1. Execute task → Track trajectory
2. Store in ExperienceCollector
3. Query similar past trajectories
4. Guide next execution with insights
5. Better trajectory → Loop again

This creates exponential learning: every execution improves future executions.
"""

import logging
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from unittest.mock import MagicMock

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.inflection_detector import Severity
from cohezion.compound.journey_tracker import JourneyTracker


logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_mock_mcp():
    """Create mock MCP client."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = []
    client.vault_search.return_value = []
    client.vault_write.return_value = "success"
    client.vault_read.return_value = "{}"
    return client


def create_mock_inflection(anomaly_score=0.1):
    """Create mock inflection detector."""
    detector = MagicMock()
    anomaly = MagicMock()
    anomaly.severity = Severity.INFO
    anomaly.score = anomaly_score
    anomaly.issues = []
    anomaly.recommendations = []
    anomaly.should_reexecute = False
    detector.detect_anomaly.return_value = anomaly
    return detector


def run_experience_guided_demo():
    """Run demonstration of experience-guided execution."""
    logger.info("=" * 80)
    logger.info("Phase 9: Experience-Guided Execution Loop Demo")
    logger.info("=" * 80)

    # Step 1: Initialize components
    logger.info("\n[1/5] Initializing components...")
    mock_mcp = create_mock_mcp()
    journey_tracker = JourneyTracker(seed=42)
    executor = CompoundExecutor(
        mock_mcp,
        enable_guardrails=False,
        inflection_detector=create_mock_inflection(0.1),
        journey_tracker=journey_tracker,
    )
    logger.info("✓ Executor initialized")

    # Step 2: Execute first task (no prior experience)
    logger.info("\n[2/5] Executing first task (cold start - no prior experience)...")

    def high_quality_task_1(guidance):
        logger.info(f"Task 1 guidance: {guidance.get('confidence', 0.0):.2f} confidence")
        return "High quality output", {"quality": 0.9}

    result1 = executor.execute_task(
        task_description="Generate creative solution",
        skill_name="creative_generation",
        operation_type="generate",
        execute_fn=high_quality_task_1,
    )

    logger.info(f"✓ Task 1 complete: coherence={result1.metrics.get('coherence', 0.0):.3f}")

    # Step 3: Execute similar task (should get guidance from first task)
    logger.info("\n[3/5] Executing similar task (should receive guidance)...")

    guidance_received = {"confidence": 0.0}

    def high_quality_task_2(guidance):
        guidance_received["confidence"] = guidance.get("confidence", 0.0)
        recs = guidance.get("recommendations", [])
        warns = guidance.get("warnings", [])

        logger.info(f"Task 2 guidance: {guidance_received['confidence']:.2f} confidence")
        if recs:
            logger.info(f"  Recommendations: {len(recs)}")
            for rec in recs:
                logger.info(f"    - {rec[:80]}...")
        if warns:
            logger.info(f"  Warnings: {len(warns)}")

        return "High quality output", {"quality": 0.9}

    result2 = executor.execute_task(
        task_description="Generate another creative solution",
        skill_name="creative_generation",
        operation_type="generate",
        execute_fn=high_quality_task_2,
    )

    logger.info(f"✓ Task 2 complete: coherence={result2.metrics.get('coherence', 0.0):.3f}")

    # Step 4: Execute low-quality task (creates negative experience)
    logger.info("\n[4/5] Executing low-quality task (creates warning for future)...")

    def low_quality_task(guidance):
        logger.info(f"Low quality task guidance: {guidance.get('confidence', 0.0):.2f} confidence")
        return "", {}  # Poor output

    executor_low = CompoundExecutor(
        mock_mcp,
        enable_guardrails=False,
        inflection_detector=create_mock_inflection(0.8),  # High anomaly
        journey_tracker=journey_tracker,
    )

    result3 = executor_low.execute_task(
        task_description="Generate risky solution",
        skill_name="risky_generation",
        operation_type="generate",
        execute_fn=low_quality_task,
    )

    logger.info(f"✓ Task 3 complete: coherence={result3.metrics.get('coherence', 0.0):.3f} (low)")

    # Step 5: Execute similar risky task (should get warning)
    logger.info("\n[5/5] Executing similar risky task (should receive warnings)...")

    warnings_received = []

    def risky_task_2(guidance):
        warnings_received.extend(guidance.get("warnings", []))
        logger.info(f"Risky task guidance: {guidance.get('confidence', 0.0):.2f} confidence")
        if warnings_received:
            logger.info(f"  Warnings received: {len(warnings_received)}")
            for warn in warnings_received:
                logger.info(f"    ⚠ {warn[:80]}...")

        return "Cautious output", {"quality": 0.5}

    result4 = executor_low.execute_task(
        task_description="Generate another risky solution",
        skill_name="risky_generation",
        operation_type="generate",
        execute_fn=risky_task_2,
    )

    logger.info(f"✓ Task 4 complete: coherence={result4.metrics.get('coherence', 0.0):.3f}")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("EXPERIENCE-GUIDED LEARNING DEMONSTRATION")
    logger.info("=" * 80)
    logger.info(f"Task 1: Cold start (no guidance) → coherence={result1.metrics.get('coherence', 0.0):.3f}")
    logger.info(
        f"Task 2: Guided by Task 1 (confidence={guidance_received['confidence']:.2f}) → coherence={result2.metrics.get('coherence', 0.0):.3f}"
    )
    logger.info(f"Task 3: Low quality execution → coherence={result3.metrics.get('coherence', 0.0):.3f}")
    logger.info(
        f"Task 4: Warned by Task 3 ({len(warnings_received)} warnings) → coherence={result4.metrics.get('coherence', 0.0):.3f}"
    )
    logger.info("\n✓ Experience-Guided Execution Loop demonstrated!")
    logger.info("Every execution improves guidance for future executions (exponential learning)")

    return True


def main():
    """Entry point."""
    try:
        success = run_experience_guided_demo()
        sys.exit(0 if success else 1)
    except Exception:
        logger.exception("Demo failed:")
        sys.exit(1)


if __name__ == "__main__":
    main()
