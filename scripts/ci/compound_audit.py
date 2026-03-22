#!/usr/bin/env python3
"""CI: Compound engineering audit -- learnings, scores, and refinement suggestions."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from cohezion.core.compound.retrospection import RetrospectionEngine
from cohezion.core.template_engine import TemplateEngine


def main() -> int:
    """Run compound audit and write report artifact."""
    retro = RetrospectionEngine()

    # Analyze learnings
    patterns = retro.analyze_learnings()
    print(f"Learning patterns found: {len(patterns)}")

    # Compound scores
    scores = retro.calculate_compound_scores()
    top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_scores:
        print("\nTop 5 compound scores:")
        for name, score in top_scores:
            print(f"  {score:.3f}  {name}")

    # Skill refinement suggestions
    refinements = retro.suggest_skill_refinements()
    if refinements:
        print(f"\nSkill refinement suggestions ({len(refinements)}):")
        for ref in refinements:
            print(f"  - {ref.skill_name}: {ref.reason}")
            for addition in ref.suggested_additions:
                print(f"      + {addition}")
    else:
        print("\nNo skill refinements suggested")

    # Cross-reference graph from SEE ALSO
    engine = TemplateEngine()
    specs = engine.parse_all()
    cross_ref_edges = sum(len(spec.see_also) for spec in specs)
    print(f"\nSEE ALSO cross-reference edges: {cross_ref_edges}")

    # Write artifact
    report = {
        "learning_count": len(patterns),
        "top_scores": dict(top_scores),
        "refinement_suggestions": [
            {
                "skill_name": ref.skill_name,
                "reason": ref.reason,
                "suggested_additions": ref.suggested_additions,
            }
            for ref in refinements
        ],
        "cross_reference_edges": cross_ref_edges,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }

    report_path = Path("compound-report.json")
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nArtifact written: {report_path}")

    print("OK: Compound audit complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
