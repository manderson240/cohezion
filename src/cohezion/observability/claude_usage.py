"""Claude usage monitor — token-burn tracking from Claude Code transcripts (task #15, 2026-06-07).

User directive: "We need a way to monitor our claude usage so we don't hit our limits too soon."

Claude Code writes a JSONL transcript per session under ``~/.claude/projects/<slug>/<id>.jsonl``;
every assistant message carries a ``message.usage`` block (input / output / cache_read /
cache_creation tokens). This module aggregates those into time windows so the user — and the
loops, via ``burn_per_hour`` — can see the burn rate and back off before hitting a plan cap.

HONEST SCOPE (metacognitive-calibration): this reports LOCAL token spend, a *proxy* for plan
usage. The exact Max-plan session/weekly percentages are server-side rate-limit buckets with
opaque weighting; this tool cannot reproduce them. It reports real token counts + burn rate +
a projection against a *user-supplied* budget — directional, not the authoritative server %.

`summarize_usage` is pure (injected records + now_ts); `load_usage_records` is the I/O loader
(reads the JSONL, not unit-tested against live files).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class UsageRecord:
    """One assistant message's token usage at a point in time."""

    ts: float  # unix seconds
    input: int
    output: int
    cache_read: int
    cache_creation: int


@dataclass(frozen=True)
class WindowUsage:
    """Aggregated usage over one named time window ending at ``now_ts``."""

    window: str
    seconds: float
    records: int
    input: int
    output: int
    cache_read: int
    cache_creation: int
    total: int
    burn_per_hour: float

    def projected_pct(self, budget_tokens: int) -> float | None:
        """Percent of a user-supplied per-window token budget consumed (None if no budget)."""
        if budget_tokens <= 0:
            return None
        return 100.0 * self.total / budget_tokens


def summarize_usage(
    records: Iterable[UsageRecord],
    *,
    now_ts: float,
    windows: Mapping[str, float],
) -> dict[str, WindowUsage]:
    """Aggregate ``records`` into each named window (seconds back from ``now_ts``). Pure.

    A record belongs to window ``w`` iff ``record.ts >= now_ts - windows[w]``. ``burn_per_hour``
    is total window tokens divided by the window length in hours — so a half-empty window still
    reports the rate over its full span (a conservative, comparable burn metric).
    """
    recs = list(records)
    out: dict[str, WindowUsage] = {}
    for name, secs in windows.items():
        cutoff = now_ts - secs
        inside = [r for r in recs if r.ts >= cutoff]
        ti = sum(r.input for r in inside)
        to = sum(r.output for r in inside)
        tcr = sum(r.cache_read for r in inside)
        tcc = sum(r.cache_creation for r in inside)
        total = ti + to + tcr + tcc
        hours = secs / 3600.0 if secs > 0 else 1.0
        out[name] = WindowUsage(
            window=name,
            seconds=secs,
            records=len(inside),
            input=ti,
            output=to,
            cache_read=tcr,
            cache_creation=tcc,
            total=total,
            burn_per_hour=total / hours,
        )
    return out


def usage_guard(
    summary: Mapping[str, WindowUsage],
    *,
    window: str = "week",
    soft_budget: int = 0,
    hard_budget: int = 0,
    metric: str = "total",
) -> Literal["proceed", "throttle", "halt"]:
    """Throttle decision for the autonomous loops (task #15 / item 134, 2026-06-07).

    The behavioral consumer of the usage monitor — so the loops NEVER run the Claude Code
    plan quota to zero. Given a ``summary`` (from :func:`summarize_usage`) and per-window token
    budgets, returns what a loop tick should do BEFORE spending an agent turn:

    - ``"proceed"`` — burn below ``soft_budget`` (or no budget configured → gate off).
    - ``"throttle"`` — ``soft_budget <= value < hard_budget``: the loop should widen its
      ScheduleWakeup interval and shift inference to the local fleet (``extend_claude``) instead
      of spending agent turns.
    - ``"halt"`` — ``value >= hard_budget``: stop scheduling new autonomous wakeups; only
      user-driven turns and local-fleet work continue, preserving Claude availability.

    Budgets are EXPLICIT (user/config-supplied) — this never invents a token→plan-% mapping (the
    server-side % is opaque). ``metric`` selects which token field to gate on (``"total"`` or
    ``"output"``; output is the scarce one — cache_read dominates totals but is cheap).
    Pure: depends only on the injected summary + budgets.
    """
    if soft_budget <= 0 and hard_budget <= 0:
        return "proceed"  # gate off — no budget configured
    w = summary.get(window)
    if w is None:
        return "proceed"
    value = float(getattr(w, metric, w.total))
    if hard_budget > 0 and value >= hard_budget:
        return "halt"
    if soft_budget > 0 and value >= soft_budget:
        return "throttle"
    return "proceed"


def load_usage_records(projects_dir: str | Path) -> list[UsageRecord]:
    """Parse all transcript JSONL under ``projects_dir`` into UsageRecords. I/O (not unit-tested).

    Robust to malformed lines and missing fields — a corrupt line is skipped, not fatal. Uses
    each entry's ISO ``timestamp`` (falls back to skipping a record with no parseable time).
    """
    from datetime import datetime

    root = Path(projects_dir).expanduser()
    records: list[UsageRecord] = []
    for jsonl in root.rglob("*.jsonl"):
        try:
            text = jsonl.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                d = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            usage = (d.get("message") or {}).get("usage") or {}
            if not usage:
                continue
            raw_ts = d.get("timestamp")
            ts: float | None = None
            if isinstance(raw_ts, str):
                try:
                    ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    ts = None
            elif isinstance(raw_ts, (int, float)):
                ts = float(raw_ts)
            if ts is None:
                continue
            records.append(
                UsageRecord(
                    ts=ts,
                    input=int(usage.get("input_tokens", 0) or 0),
                    output=int(usage.get("output_tokens", 0) or 0),
                    cache_read=int(usage.get("cache_read_input_tokens", 0) or 0),
                    cache_creation=int(usage.get("cache_creation_input_tokens", 0) or 0),
                )
            )
    return records
