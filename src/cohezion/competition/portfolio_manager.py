"""Compound Loop applied to competition portfolio management."""

from __future__ import annotations

import json
from typing import Any


COMPETITIONS = [
    {
        "name": "arc-prize-2026-arc-agi-2",
        "prize_usd": 700_000,
        "teams": 2083,
        "deadline_weeks": 6,
        "alignment_with_skills": 0.85,
        "effort_weeks": 2,
        "match_with_stack": 0.90,
    },
    {
        "name": "arc-prize-2026-arc-agi-3",
        "prize_usd": 850_000,
        "teams": 3148,
        "deadline_weeks": 6,
        "alignment_with_skills": 0.70,
        "effort_weeks": 3,
        "match_with_stack": 0.75,
    },
    {
        "name": "arc-prize-2026-paper-track",
        "prize_usd": 450_000,
        "teams": 193,
        "deadline_weeks": 7,
        "alignment_with_skills": 0.95,
        "effort_weeks": 2,
        "match_with_stack": 0.95,
    },
    {
        "name": "enveda-CASMI26-molecule-id-mass-spectra",
        "prize_usd": 50_000,
        "teams": 744,
        "deadline_weeks": 12,
        "alignment_with_skills": 0.80,
        "effort_weeks": 1,
        "match_with_stack": 0.85,
    },
    {
        "name": "rsna-knee-abnormality-detection",
        "prize_usd": 77_000,
        "teams": 3968,
        "deadline_weeks": 5,
        "alignment_with_skills": 0.80,
        "effort_weeks": 1,
        "match_with_stack": 0.85,
    },
    {
        "name": "biohub-cell-tracking-during-development",
        "prize_usd": 60_000,
        "teams": 3697,
        "deadline_weeks": 1,
        "alignment_with_skills": 0.90,
        "effort_weeks": 1,
        "match_with_stack": 0.90,
    },
    {
        "name": "kaggriculture",
        "prize_usd": 50_000,
        "teams": 9479,
        "deadline_weeks": 2,
        "alignment_with_skills": 0.85,
        "effort_weeks": 1,
        "match_with_stack": 0.90,
    },
]


def expected_value(c: dict[str, Any]) -> float:
    """Compute competition EV = prize * alignment * match / (teams * effort)."""
    prob_win = min(1.0, c["alignment_with_skills"] * c["match_with_stack"] / c["teams"])
    time_value = 1.0 / max(1, c["effort_weeks"])
    return c["prize_usd"] * prob_win * time_value


def alignment_gate(c: dict[str, Any], threshold: float = 0.5) -> bool:
    return c["alignment_with_skills"] >= threshold


def main() -> dict[str, Any]:
    print("=" * 60)
    print("COMPOUND COMPETITION PORTFOLIO MANAGER")
    print("=" * 60)
    print()

    # Phase 1: Alignment Gate — filter out misaligned competitions
    aligned = [c for c in COMPETITIONS if alignment_gate(c)]
    print(f"Passed alignment gate: {len(aligned)}/{len(COMPETITIONS)}")
    for c in aligned:
        print(f"  ✓ {c['name']} (alignment={c['alignment_with_skills']})")
    print()

    # Phase 2: Score by Expected Value
    scored = [(expected_value(c), c) for c in aligned]
    scored.sort(key=lambda x: x[0], reverse=True)

    print("-" * 60)
    print("SCORING (Expected Value)")
    print("-" * 60)
    for ev, c in scored:
        print(
            f"  {c['name']:35s} EV=${ev:>8.0f}  |  prize=${c['prize_usd']:>9,}  |  teams={c['teams']}"
        )
    print()

    # Phase 3: Decision
    best = scored[0][1]
    print("-" * 60)
    print("DECISION")
    print("-" * 60)
    print(f"  Primary target: {best['name']}")
    print(f"  Expected value: ${expected_value(best):,.0f}")
    print(f"  Effort required: {best['effort_weeks']} weeks")
    print()

    # Phase 4: Journey Log
    result = {
        "aligned_competitions": [c["name"] for c in aligned],
        "rankings": [
            {"name": c["name"], "ev": round(ev, 0), "prize": c["prize_usd"], "teams": c["teams"]}
            for ev, c in scored
        ],
        "recommendation": best["name"],
        "recommendation_ev": round(expected_value(best), 0),
    }

    from pathlib import Path
    out_path = Path(__file__).parent / "competition_portfolio.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved portfolio analysis to {out_path}")
    return result


if __name__ == "__main__":
    main()
