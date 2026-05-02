"""Full paper draft review using local model (Lemonade).

Reads DRAFT_v2.md, dispatches each section to PaperTrackAgent,
and collects actionable improvements.

This is the most valuable use of the orchestrator for our highest-EV target.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cohezion.competition.orchestrator.main import CompetitionOrchestrator


logger = logging.getLogger(__name__)


def read_draft(path: Path) -> dict[str, str]:
    """Split draft into sections."""
    text = path.read_text()
    sections: dict[str, str] = {}
    current_title = "header"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            sections[current_title] = "\n".join(current_lines)
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    sections[current_title] = "\n".join(current_lines)
    return sections


def review_paper(orch: CompetitionOrchestrator, draft_path: Path) -> dict:
    """Review each section of the paper."""
    sections = read_draft(draft_path)
    results: dict[str, dict] = {}

    # Review each substantive section
    for title, content in sections.items():
        if title in ("header", "Abstract"):
            continue
        if len(content.strip()) < 50:
            continue

        print(f"\n--- Reviewing: {title} ---")
        result = orch.dispatch(
            "arc-paper",
            {
                "action": "suggest_improvements",
                "draft": f"Section: {title}\n\n{content[:3000]}",
            },
        )
        results[title] = result.get("suggestions", {})
        issues = results[title].get("issues", [])
        priority = results[title].get("priority", "unknown")
        print(f"Priority: {priority} | Issues: {len(issues)}")
        for issue in issues[:3]:
            print(f"  - {issue}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    orch = CompetitionOrchestrator()
    health = orch.health_check()
    print(json.dumps(health, indent=2))

    if not health["lemonade_warm"]:
        print("Lemonade not available. Exiting.")
        exit(1)

    draft = Path(
        "/home/mike-anderson/dev/cohezion/src/cohezion/competition/arc_prize_paper_track/DRAFT_v2.md"
    )
    if not draft.exists():
        print(f"Draft not found: {draft}")
        exit(1)

    reviews = review_paper(orch, draft)

    # Summary
    high_priority = [t for t, r in reviews.items() if r.get("priority") == "high"]
    total_issues = sum(len(r.get("issues", [])) for r in reviews.values())

    print(f"\n{'=' * 60}")
    print("PAPER REVIEW COMPLETE")
    print(f"{'=' * 60}")
    print(f"Sections reviewed: {len(reviews)}")
    print(f"Total issues found: {total_issues}")
    print(f"High-priority sections: {len(high_priority)}")
    if high_priority:
        print("Sections needing most work:")
        for s in high_priority:
            print(f"  - {s}")

    print(f"\nMETRIC competitions_orchestrated={len(reviews)}")
