"""Compound Loop applied to competition portfolio management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

COMPETITIONS = [
    {
        "name": "gemma-4-good-hackathon",
        "prize_usd": 200_000,
        "teams": 109,
        "deadline_weeks": 3,
        "alignment_with_skills": 0.8,  # we have gemma, compound loop, social good
        "effort_weeks": 1,
        "match_with_stack": 0.9,  # our infrastructure
    },
    {
        "name": "arc-prize-2026-arc-agi-2",
        "prize_usd": 700_000,
        "teams": 448,
        "deadline_weeks": 28,
        "alignment_with_skills": 0.3,  # low: eval tasks resist our primitives
        "effort_weeks": 12,
        "match_with_stack": 0.4,
    },
    {
        "name": "arc-prize-2026-paper-track",
        "prize_usd": 450_000,
        "teams": 29,
        "deadline_weeks": 28,
        "alignment_with_skills": 0.9,  # high: our compound loop is novel research
        "effort_weeks": 4,
        "match_with_stack": 0.95,
    },
    {
        "name": "arc-prize-2026-arc-agi-3",
        "prize_usd": 850_000,
        "teams": 594,
        "deadline_weeks": 28,
        "alignment_with_skills": 0.2,
        "effort_weeks": 16,
        "match_with_stack": 0.3,
    },
    {
        "name": "sei-ai-accelathon",
        "prize_usd": 1_000_000,
        "teams": 200,  # estimated
        "deadline_weeks": 18,
        "alignment_with_skills": 0.6,  # MCP tooling track matches our infra
        "effort_weeks": 6,
        "match_with_stack": 0.7,
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
        print(f"  {c['name']:35s} EV=${ev:>8.0f}  |  prize=${c['prize_usd']:>9,}  |  teams={c['teams']}")
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

    with open("competition_portfolio.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Saved portfolio analysis to competition_portfolio.json")
    return result


if __name__ == "__main__":
    main()
