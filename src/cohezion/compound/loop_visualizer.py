"""Compound loop ASCII visualizer.

Provides terminal-friendly progress reporting for the overnight EVO loop,
showing HIHO balance, experiment trends, and retirement status.
"""
from __future__ import annotations

from typing import Any


def render_hiho_bar(balance: float, width: int = 20) -> str:
    """Render HIHO balance as an ASCII bar.

    |████████████░░░░░░░░| 0.62 EXPLOIT
    """
    filled = round(balance * width)
    empty = width - filled
    mode = "EXPLOIT" if balance >= 0.5 else "EXPLORE"
    bar = "█" * filled + "░" * empty
    return f"|{bar}| {balance:.2f} {mode}"


def render_experiment_table(
    stats: dict[str, dict[str, Any]],
    max_rows: int = 5,
    retirement_candidates: list[str] | None = None,
) -> str:
    """Render experiment stats as an ASCII table."""
    retired = set(retirement_candidates or [])
    rows = sorted(
        stats.items(),
        key=lambda x: -x[1].get("n_keeps", 0),
    )[:max_rows]

    lines = ["Experiment           | n    | keep% | mean  | cv     | status"]
    lines.append("-" * 70)
    for exp, d in rows:
        status = "✓RETIRE" if exp in retired else "active"
        lines.append(
            f"{exp:<20s} | {d['total']:<4d} | {d['keep_rate']:.0%}   | "
            f"{d['mean_metric']:.4f} | {d['cv']:.4f} | {status}"
        )
    return "\n".join(lines)


def render_session_summary(
    n_experiments: int,
    hiho_balance: float,
    mean_delta: float,
    keep_rate: float,
    retirement_candidates: list[str],
    score_trend: dict[str, Any] | None = None,
) -> str:
    """Render a full session summary."""
    lines = [
        "╔══════════════════════════════════════╗",
        "║   COMPOUND ENGINEERING SESSION        ║",
        "╚══════════════════════════════════════╝",
        f"  HIHO Balance: {render_hiho_bar(hiho_balance)}",
        f"  Experiments:  {n_experiments}",
        f"  Keep Rate:    {keep_rate:.0%}",
        f"  Mean Delta:   {mean_delta:+.4f}",
    ]

    if score_trend:
        trend_arrow = "▲" if score_trend.get("improving") else ("▼" if score_trend.get("degrading") else "→")
        lines.append(f"  Score Trend:  {trend_arrow} mean={score_trend.get('mean', 0):.3f}")

    if retirement_candidates:
        lines.append(f"  Retiring:     {', '.join(retirement_candidates[:3])}")

    return "\n".join(lines)
