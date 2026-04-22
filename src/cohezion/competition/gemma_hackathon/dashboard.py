"""CLI Dashboard for Compound Crisis Response demo."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EpisodeMetrics:
    alignment: float
    effectiveness: float
    learning_gain: float
    skill_count: int


def render_episode_metrics(metrics: EpisodeMetrics) -> str:
    bar_len = 20
    a_fill = int(metrics.alignment * bar_len)
    e_fill = int(metrics.effectiveness * bar_len)
    g_fill = int(metrics.learning_gain * bar_len)
    lines = [
        "",
        "╔═════════════════════════════════════════╗",
        "║  COMPOUND CRISIS RESPONSE DASHBOARD   ║",
        "╠═════════════════════════════════════════╣",
        f"║  Alignment    [{'█' * a_fill}{'░' * (bar_len - a_fill)}] {metrics.alignment:>5.1%} ║",
        f"║  Effectiveness [{'█' * e_fill}{'░' * (bar_len - e_fill)}] {metrics.effectiveness:>5.1%} ║",
        f"║  Learning Gain [{'█' * g_fill}{'░' * (bar_len - g_fill)}] {metrics.learning_gain:>5.1%} ║",
        f"║  Skills: {metrics.skill_count:<29} ║",
        "╚═════════════════════════════════════════╝",
        "",
    ]
    return "\n".join(lines)


def render_training_progress(episodes: list[dict[str, Any]]) -> str:
    lines = [
        "",
        "╔═══════════════════════════════════════════════════════╗",
        "║     SKILL REFINEMENT PROGRESS (8 EPISODES)            ║",
        "╠═══════════════════════════════════════════════════════╣",
        "║ Episode │ Alignment │ Effectiveness │ Refinements   ║",
        "╠═════════╪═══════════╪═══════════════╪═══════════════╣",
    ]
    for ep in episodes:
        lines.append(
            f"║   {ep['episode']:>3}   │  {ep['avg_alignment']:>5.3f}   │    {ep['avg_effectiveness']:>5.3f}    │      {ep['refinements']:<3}        ║"
        )
    lines.append("╚═══════════════════════════════════════════════════════╝")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    # Example usage when run standalone
    from training_loop import run_training_loop

    result = run_training_loop(episodes=8)
    print(render_training_progress(result["training_results"]))
    print(f"Total improvement: alignment +{result['improvement']['alignment']:.3f}, effectiveness +{result['improvement']['effectiveness']:.3f}")
