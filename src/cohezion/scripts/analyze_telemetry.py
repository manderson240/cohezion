"""Telemetry-to-Skill bridge - closes the compound engineering loop.

Reads telemetry data from .telemetry/, analyzes execution patterns,
extracts refinements for skills that meet coherence thresholds.

Usage:
    uv run python src/cohezion/scripts/analyze_telemetry.py
    uv run python src/cohezion/scripts/analyze_telemetry.py --skill python_PRIME
    uv run python src/cohezion/scripts/analyze_telemetry.py --since 2026-04-19

The compound loop:
    Execute → Telemetry → JourneyAnalyzer → SkillRefiner → Better Skills ↺
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TELEMETRY_DIR = Path(".telemetry")
COHERENCE_THRESHOLD = 0.5  # HIHO threshold

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPattern:
    """Pattern extracted from telemetry."""

    skill_name: str
    request_id: str
    total_latency_ms: float
    avg_step_latency_ms: float
    total_tokens: int
    success: bool
    inflection_detected: bool
    metadata: dict[str, Any]


def load_telemetry_files(skill_name: str | None = None, since: str | None = None) -> list[dict]:
    """Load telemetry files matching filters."""
    if not TELEMETRY_DIR.exists():
        logger.warning("No telemetry directory found")
        return []

    files = sorted(TELEMETRY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    results = []
    for f in files:
        try:
            data = json.loads(f.read_text())

            # Filter by skill
            if skill_name and data.get("skill_name") != skill_name:
                continue

            # Filter by date
            if since:
                try:
                    file_date = datetime.fromisoformat(
                        data.get("timestamp", "").replace("Z", "+00:00")
                    )
                    since_date = datetime.fromisoformat(since)
                    if file_date < since_date:
                        continue
                except (ValueError, TypeError):
                    pass

            results.append(data)
        except (OSError, json.JSONDecodeError):
            continue

    return results


def extract_pattern(telemetry: dict) -> ExecutionPattern | None:
    """Extract pattern from single telemetry entry."""
    skill = telemetry.get("skill_name", "unknown")
    if not skill or skill == "unknown":
        return None

    return ExecutionPattern(
        skill_name=skill,
        request_id=telemetry.get("request_id", ""),
        total_latency_ms=telemetry.get("total_latency_ms", 0),
        avg_step_latency_ms=telemetry.get("total_latency_ms", 0)
        / max(telemetry.get("steps_count", 1), 1),
        total_tokens=telemetry.get("total_tokens_in", 0) + telemetry.get("total_tokens_out", 0),
        success=telemetry.get("success", False),
        inflection_detected=telemetry.get("inflection_detected", False),
        metadata=telemetry,
    )


def analyze_patterns(patterns: list[ExecutionPattern]) -> dict[str, Any]:
    """Analyze patterns for skill refinement opportunities."""
    if not patterns:
        return {"status": "no_data"}

    by_skill: dict[str, list[ExecutionPattern]] = {}
    for p in patterns:
        by_skill.setdefault(p.skill_name, []).append(p)

    analysis = {
        "status": "success",
        "total_executions": len(patterns),
        "skills_analyzed": len(by_skill),
        "by_skill": {},
        "refinement_candidates": [],
    }

    for skill_name, skill_patterns in by_skill.items():
        n = len(skill_patterns)
        if n < 3:
            continue  # Need at least 3 samples

        successes = sum(1 for p in skill_patterns if p.success)
        inflections = sum(1 for p in skill_patterns if p.inflection_detected)
        avg_latency = sum(p.total_latency_ms for p in skill_patterns) / n
        avg_tokens = sum(p.total_tokens for p in skill_patterns) / n

        # Calculate coherence proxy (success rate × efficiency)
        success_rate = successes / n
        efficiency = min(1.0, 1000 / avg_latency) if avg_latency > 0 else 0
        coherence = success_rate * efficiency

        skill_analysis = {
            "executions": n,
            "success_rate": round(success_rate, 3),
            "inflection_rate": round(inflections / n, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_tokens": round(avg_tokens, 0),
            "coherence_proxy": round(coherence, 3),
        }

        analysis["by_skill"][skill_name] = skill_analysis

        # Check if skill meets refinement threshold
        if coherence >= COHERENCE_THRESHOLD and n >= 5:
            analysis["refinement_candidates"].append(
                {
                    "skill": skill_name,
                    "coherence": round(coherence, 3),
                    "executions": n,
                    "recommendation": _generate_recommendation(skill_analysis),
                }
            )

    return analysis


def _generate_recommendation(analysis: dict) -> str:
    """Generate refinement recommendation based on analysis."""
    recommendations = []

    if analysis["inflection_rate"] > 0.3:
        recommendations.append("High inflection rate - consider breaking into sub-skills")

    if analysis["avg_latency_ms"] > 5000:
        recommendations.append("High latency - consider caching or pre-computation")

    if analysis["avg_tokens"] > 2000:
        recommendations.append("High token usage - consider prompt optimization")

    if not recommendations:
        recommendations.append("Pattern stable - extract as canonical example")

    return "; ".join(recommendations)


def export_analysis(analysis: dict, output: Path) -> None:
    """Export analysis to JSON."""
    output.write_text(json.dumps(analysis, indent=2))
    logger.info(f"Exported analysis to {output}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze telemetry for skill refinement")
    parser.add_argument("--skill", help="Filter by skill name")
    parser.add_argument("--since", help="Filter by date (ISO format)")
    parser.add_argument("--output", default=".telemetry/analysis.json", help="Output file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s"
    )

    # Load telemetry
    telemetry = load_telemetry_files(args.skill, args.since)
    logger.info(f"Loaded {len(telemetry)} telemetry files")

    # Extract patterns
    patterns = [p for p in [extract_pattern(t) for t in telemetry] if p]
    logger.info(f"Extracted {len(patterns)} valid patterns")

    # Analyze
    analysis = analyze_patterns(patterns)

    # Print summary
    print(f"\n{'=' * 60}")
    print("TELEMETRY ANALYSIS")
    print(f"{'=' * 60}")
    print(f"Total executions: {analysis.get('total_executions', 0)}")
    print(f"Skills analyzed: {analysis.get('skills_analyzed', 0)}")

    candidates = analysis.get("refinement_candidates", [])
    print(f"Refinement candidates: {len(candidates)}")

    if candidates:
        print(f"\n{'=' * 60}")
        print("CANDIDATES FOR SKILL REFINEMENT")
        print(f"{'=' * 60}")
        for c in candidates:
            print(f"\n  Skill: {c['skill']}")
            print(f"    Coherence: {c['coherence']}")
            print(f"    Executions: {c['executions']}")
            print(f"    Recommendation: {c['recommendation']}")

    # Export
    export_analysis(analysis, Path(args.output))

    return 0 if analysis.get("status") == "success" else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
