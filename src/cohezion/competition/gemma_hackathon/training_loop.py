"""Training loop demo: show skill refinement over multiple episodes."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class EpisodeResult:
    episode: int
    scenarios: int
    avg_alignment: float
    avg_effectiveness: float
    refinements: list[str]
    skills: dict[str, str]


def simulate_episode(episode_num: int) -> EpisodeResult:
    """Simulate one training episode with skill refinement."""
    base_skills = {
        "flooding": "Deploy pumps, coordinate evacuation, establish shelter points",
        "earthquake": "Search and rescue, triage, structural assessment",
        "shortage": "Rapid assessment, logistics chain, fair distribution",
        "wildfire": "Evacuate, establish firebreaks, coordinate air/water support",
        "disease": "Contain spread, test/isolate, preserve privacy",
    }

    # Simulate skill refinement based on episode number
    refinements = []
    skills = dict(base_skills)

    if episode_num >= 2:
        skills["flooding"] += " (refined: prioritize vulnerable populations)"
        refinements.append("Refined flooding: prioritize vulnerable populations")

    if episode_num >= 4:
        skills["wildfire"] += " (refined: preemptive evacuation before containment)"
        refinements.append("Refined wildfire: preemptive evacuation before containment")

    if episode_num >= 6:
        skills["disease"] += " (refined: community-led contact tracing)"
        refinements.append("Refined disease: community-led contact tracing")

    # Simulate metrics improving with episodes (with noise)
    base_alignment = 0.60 + (episode_num * 0.02)
    base_effectiveness = 0.75 + (episode_num * 0.025)

    avg_alignment = min(0.95, base_alignment + random.gauss(0, 0.03))
    avg_effectiveness = min(1.0, base_effectiveness + random.gauss(0, 0.04))

    return EpisodeResult(
        episode=episode_num,
        scenarios=5,
        avg_alignment=round(avg_alignment, 3),
        avg_effectiveness=round(avg_effectiveness, 3),
        refinements=refinements,
        skills=skills,
    )


def run_training_loop(episodes: int = 8) -> dict[str, Any]:
    results = []
    for i in range(1, episodes + 1):
        result = simulate_episode(i)
        results.append(
            {
                "episode": result.episode,
                "avg_alignment": result.avg_alignment,
                "avg_effectiveness": result.avg_effectiveness,
                "refinements": len(result.refinements),
            }
        )

    # Final state
    final = simulate_episode(episodes)
    improvement = {
        "alignment": round(final.avg_alignment - results[0]["avg_alignment"], 3),
        "effectiveness": round(final.avg_effectiveness - results[0]["avg_effectiveness"], 3),
    }

    return {
        "training_results": results,
        "final_skills": final.skills,
        "total_refinements": sum(r["refinements"] for r in results),
        "improvement": improvement,
    }


if __name__ == "__main__":
    result = run_training_loop(episodes=8)
    print(json.dumps(result, indent=2))
