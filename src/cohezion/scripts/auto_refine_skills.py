"""Auto-refine skills based on telemetry coherence thresholds.

Closes the compound engineering loop:
    Execute → Telemetry → Analysis → Refinement → Better Skills ↺

Usage:
    uv run python src/cohezion/scripts/auto_refine_skills.py
    uv run python src/cohezion/scripts/auto_refine_skills.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from cohezion.compound.telemetry import CompoundTelemetry
from cohezion.compound.journey_analyzer import JourneyAnalyzer

TELEMETRY_DIR = Path(".telemetry")
TELEMETRY_FILE = TELEMETRY_DIR / "analysis.json"
SKILLS_DIR = Path("src/cohezion/skills")

# HIHO-based thresholds
COHERENCE_OPTIMAL = 0.75   # Extract as canonical
COHERENCE_STABLE = 0.5     # Use as standard pattern
COHERENCE_CRITICAL = 0.4   # Monitor closely
COHERENCE_DEGRADED = 0.25  # Major rework required

logger = logging.getLogger(__name__)


def classify_skill(coherence: float, executions: int, success_rate: float, inflection_rate: float) -> str:
    """Classify skill based on HIHO thresholds."""
    if executions < 10:
        return "insufficient_data"
    
    if coherence >= COHERENCE_OPTIMAL and success_rate >= 0.9 and inflection_rate < 0.3:
        return "canonical"
    elif coherence >= COHERENCE_STABLE:
        return "stable"
    elif coherence >= COHERENCE_CRITICAL:
        return "critical"
    elif coherence >= COHERENCE_DEGRADED:
        return "unstable"
    else:
        return "degraded"


def trigger_refinement(skill_name: str, classification: str, metrics: dict[str, Any], dry_run: bool = False) -> None:
    """Trigger refinement for a skill."""
    logger.info(f"\n{'='*60}")
    logger.info(f"REFINEMENT TRIGGERED: {skill_name}")
    logger.info(f"Classification: {classification}")
    logger.info(f"Coherence: {metrics['coherence_proxy']:.3f}")
    logger.info(f"Success rate: {metrics['success_rate']:.1%}")
    logger.info(f"Inflection rate: {metrics['inflection_rate']:.1%}")
    
    if dry_run:
        logger.info("[DRY RUN - no changes made]")
        return
    
    # Log to journey analyzer for pattern extraction
    try:
        analyzer = JourneyAnalyzer()
        analyzer.record_metric(
            skill=skill_name,
            metric="refinement_triggered",
            value=metrics['coherence_proxy'],
            reason=classification
        )
        logger.info("✓ Logged to JourneyAnalyzer")
    except Exception as e:
        logger.warning(f"Could not log to JourneyAnalyzer: {e}")
    
    # Create refinement marker file
    marker = TELEMETRY_DIR / f"refine_{skill_name}_{int(metrics['coherence_proxy']*100)}.json"
    marker.write_text(json.dumps({
        "skill": skill_name,
        "classification": classification,
        "metrics": metrics,
        "triggered_at": str(Path.cwd())
    }, indent=2))
    logger.info(f"✓ Created refinement marker: {marker.name}")


def export_canonical(skill_name: str, metrics: dict[str, Any], dry_run: bool = False) -> None:
    """Export canonical skill pattern."""
    logger.info(f"\n✅ CANONICAL SKILL: {skill_name}")
    logger.info(f"  Coherence: {metrics['coherence_proxy']:.3f}")
    logger.info(f"  Executions: {metrics.get('executions', 'N/A')}")
    logger.info(f"  Recommendation: Pattern stable - extract as canonical example")
    
    if dry_run:
        return
    
    # Mark as canonical in skill metadata
    canonical_marker = Path("docs/patterns/canonical_skills.jsonl")
    canonical_marker.parent.mkdir(exist_ok=True)
    
    with open(canonical_marker, "a") as f:
        f.write(json.dumps({
            "skill": skill_name,
            "coherence": metrics['coherence_proxy'],
            "executions": metrics.get('executions', 0),
            "timestamp": str(Path.cwd())
        }) + "\n")
    logger.info(f"✓ Added to canonical skills list")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Auto-refine skills based on telemetry")
    parser.add_argument("--dry-run", action="store_true", help="Do not make changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    # Load analysis
    if not TELEMETRY_FILE.exists():
        logger.error(f"No telemetry analysis found at {TELEMETRY_FILE}")
        logger.info("Run: uv run python src/cohezion/scripts/analyze_telemetry.py")
        return 1
    
    analysis = json.loads(TELEMETRY_FILE.read_text())
    
    print(f"\n{'='*60}")
    print("AUTO-REFINE: Compound Loop Closure")
    print(f"{'='*60}")
    print(f"Total skills analyzed: {analysis.get('skills_analyzed', 0)}")
    print(f"HIHO threshold: {COHERENCE_CRITICAL:.1f}")
    print()
    
    # Process each skill
    canonical_count = 0
    refine_count = 0
    
    for skill_name, metrics in analysis.get("by_skill", {}).items():
        coherence = metrics.get("coherence_proxy", 0)
        executions = metrics.get("executions", 0)
        success_rate = metrics.get("success_rate", 0)
        inflection_rate = metrics.get("inflection_rate", 0)
        
        classification = classify_skill(coherence, executions, success_rate, inflection_rate)
        
        if classification == "canonical":
            export_canonical(skill_name, metrics, args.dry_run)
            canonical_count += 1
        elif classification in ["critical", "unstable", "degraded"]:
            trigger_refinement(skill_name, classification, metrics, args.dry_run)
            refine_count += 1
        elif classification == "insufficient_data":
            logger.info(f"⏳ {skill_name}: Need more samples ({executions}/10)")
        else:
            logger.info(f"✓ {skill_name}: {classification} ({coherence:.2f})")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Canonical: {canonical_count}")
    print(f"Refinement triggered: {refine_count}")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
