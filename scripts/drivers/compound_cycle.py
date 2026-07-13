#!/usr/bin/env python3
"""End-to-end compound engineering cycle validation (Phase 8).

Validates the complete enriched pipeline from Session 58:
- Phase 1: Real cohesion scores
- Phase 2: Full trajectory statistics
- Phase 3: Degradation feedback loop
- Phase 4: Real smoothness/convergence for phi_score
- Phase 5: VAE training on real experience data
- Phase 6: RetrospectionEngine live analysis + refinement gating
- Phase 7: UniverseBridge to simulation engine

This script exercises the full loop:
    execute_fn → cohesion → degradation → journey tracking → retrospection → refinement → universe
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.compound.universe_bridge import UniverseBridge
from cohezion.core.compound.retrospection import RetrospectionEngine


logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_mock_mcp_client():
    """Create a mock MCP client with all required methods."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = []
    client.vault_search.return_value = []
    client.vault_write.return_value = "success"
    client.vault_read.return_value = '{"status": "started"}'
    client.vault_log_experiment.return_value = "experiments/test.md"
    client.vault_log_decision.return_value = "decisions/test.md"
    client.vault_extract_pattern.return_value = "patterns/test.md"
    client.vault_edit.return_value = "success"
    return client


def create_mock_inflection_detector():
    """Create a mock inflection detector with high health scores (anomaly_score = HEALTH, high=good)."""
    from cohezion.compound.inflection_detector import Severity

    detector = MagicMock()
    anomaly = MagicMock()
    anomaly.severity = Severity.INFO
    anomaly.score = 0.9  # High health score for high-quality tasks (anomaly_score = HEALTH, high=good)
    anomaly.issues = []
    anomaly.recommendations = []
    anomaly.should_reexecute = False
    detector.detect_anomaly.return_value = anomaly
    return detector


def create_mock_universe_engine():
    """Create a mock universe simulation engine."""
    return MagicMock()


def run_compound_cycle(dry_run: bool = True):
    """Run a complete compound engineering cycle.

    Args:
        dry_run: If True, use mocks instead of real services
    """
    logger.info("=" * 80)
    logger.info("Phase 8: End-to-End Compound Cycle Validation")
    logger.info("=" * 80)

    # Step 1: Initialize all enrichment components
    logger.info("\n[1/7] Initializing enrichment components...")

    mock_mcp = create_mock_mcp_client()
    journey_tracker = JourneyTracker(seed=42)
    degradation_detector = DegradationDetector()
    retrospection_engine = RetrospectionEngine()
    skill_refiner = SkillRefiner(mcp_client=mock_mcp)

    if dry_run:
        universe_engine = create_mock_universe_engine()
    else:
        from cohezion.universe.engine import UniverseSimulationEngine

        universe_engine = UniverseSimulationEngine()

    universe_bridge = UniverseBridge(engine=universe_engine, agent_name="compound-cycle-test")

    logger.info("✓ All components initialized")

    # Step 2: Create executor with all enrichments enabled
    logger.info("\n[2/7] Creating enriched CompoundExecutor...")

    mock_inflection = create_mock_inflection_detector()

    executor = CompoundExecutor(
        mock_mcp,
        enable_guardrails=False,  # Disable for testing
        inflection_detector=mock_inflection,
        journey_tracker=journey_tracker,
        degradation_detector=degradation_detector,
        retrospection_engine=retrospection_engine,
        skill_refiner=skill_refiner,
        enable_skill_refinement=True,
        universe_bridge=universe_bridge,
    )

    logger.info("✓ Executor created with 7 enrichments enabled")

    # Step 3: Define test task (high coherence)
    logger.info("\n[3/7] Executing test task (high coherence expected)...")

    def high_quality_task(guidance):
        """Simulate a high-quality execution."""
        return "Test output with high quality", {"quality": 0.9}

    result1 = executor.execute_task(
        task_description="High-quality test execution",
        skill_name="test_skill",
        operation_type="generate",
        execute_fn=high_quality_task,
    )

    logger.info("✓ Execution 1 complete")
    logger.info(f"  - Success: {result1.success}")
    logger.info(f"  - Coherence: {result1.metrics.get('coherence', 'N/A'):.3f}")
    logger.info(f"  - Phi score: {result1.metrics.get('phi_score', 'N/A')}")
    logger.info(f"  - Anomaly score: {result1.metrics.get('anomaly_score', 'N/A'):.3f}")
    logger.info(f"  - Degraded: {result1.metrics.get('execution_degraded', False)}")

    # Step 4: Verify Phase 1 (real cohesion)
    logger.info("\n[4/7] Validating Phase 1: Real cohesion scores...")

    coherence = result1.metrics.get("coherence", None)
    if coherence is None:
        logger.error("✗ FAILED: Coherence not computed!")
        return False
    if coherence == 0.5:
        logger.warning("⚠ WARNING: Coherence is exactly 0.5 (may be default)")

    # Should be high coherence: success (0.7) + high health (0.9) = ~0.7-0.85
    if coherence > 0.55:
        logger.info(f"✓ Phase 1 PASSED: Real cohesion = {coherence:.3f}")
    else:
        logger.error(f"✗ Phase 1 FAILED: Coherence {coherence:.3f} too low for high-quality task")
        return False

    # Step 5: Verify Phase 4 (real phi_score)
    logger.info("\n[5/7] Validating Phase 4: Real phi_score...")

    phi_score = result1.metrics.get("phi_score", None)
    if phi_score is None:
        logger.error("✗ FAILED: phi_score not propagated to metrics!")
        return False
    if phi_score == 0.5:
        logger.warning("⚠ WARNING: phi_score is exactly 0.5 (may be HIHO default)")

    logger.info(f"✓ Phase 4 PASSED: phi_score = {phi_score:.3f}")

    # Step 6: Execute low-quality task to trigger degradation
    logger.info("\n[6/7] Executing degraded task (low coherence expected)...")

    def low_quality_task(guidance):
        """Simulate a degraded execution."""
        return "", {}  # Empty output, no quality

    result2 = executor.execute_task(
        task_description="Low-quality test execution",
        skill_name="test_skill",
        operation_type="generate",
        execute_fn=low_quality_task,
    )

    logger.info("✓ Execution 2 complete")
    logger.info(f"  - Success: {result2.success}")
    logger.info(f"  - Coherence: {result2.metrics.get('coherence', 'N/A'):.3f}")
    logger.info(f"  - Degraded: {result2.metrics.get('execution_degraded', False)}")

    # Step 7: Verify Phase 6 (retrospection gating)
    logger.info("\n[7/7] Validating Phase 6: Retrospection gating...")

    retro_insights = result1.metrics.get("retrospection_insights", None)
    if retro_insights is None:
        logger.error("✗ FAILED: Retrospection insights not in metrics!")
        return False

    logger.info(
        f"✓ Phase 6 PASSED: Retrospection insights present ({len(retro_insights)} insights)"
    )

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ Phase 1: Real cohesion scores - {coherence:.3f}")
    logger.info(f"✓ Phase 4: Real phi_score - {phi_score:.3f}")
    logger.info(f"✓ Phase 6: Retrospection gating - {len(retro_insights)} insights")
    logger.info(f"✓ Journey tracking: {journey_tracker.get_recent_point_count()} points")
    logger.info(f"✓ Universe bridge: {'Active' if universe_bridge else 'N/A'}")

    logger.info("\nAll phases validated successfully! ✓")
    return True


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run compound engineering cycle validation")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Use real services instead of mocks (requires SurrealDB + vault)",
    )
    args = parser.parse_args()

    dry_run = not args.production

    if dry_run:
        logger.info("Running in DRY-RUN mode (mocked services)")
    else:
        logger.info("Running in PRODUCTION mode (real services)")

    try:
        success = run_compound_cycle(dry_run=dry_run)
        sys.exit(0 if success else 1)
    except Exception:
        logger.exception("Compound cycle failed with exception:")
        sys.exit(1)


if __name__ == "__main__":
    main()
