"""Single-writer for routing decisions — the corpus that lets the fleet tune itself.

Backlog item 2 (thread C, self-improvement). Every ``ModelRegistry.get_best_for_task``
decision appends one JSON line recording WHICH model was chosen for WHICH task class, on
WHICH lane, and whether the task-specialist path was taken or it FELL BACK to the
complexity router. Item 9 feeds this corpus into the autoresearch loop so ``LANE_WATTS`` /
task→specialist mappings tune from real outcomes instead of hand-set priors.

Mirrors ``recursive_trace.resolution_log``: fail-soft (never breaks the routing path),
pytest-skipped unless an explicit ``path`` is injected (so the suite never pollutes the
real corpus), and the sink defaults to ``~/.cohezion-research/logs/routing_log.jsonl``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_LOG = Path.home() / ".cohezion-research" / "logs" / "routing_log.jsonl"


def record_routing_decision(
    *,
    task_class: str,
    chosen_model: str | None,
    fell_back: bool,
    lane: str = "",
    outcome: str | None = None,
    source: str = "live",
    ts: str | None = None,
    path: Path | None = None,
) -> dict | None:
    """Append one routing-decision record. Returns the written dict, or None if skipped.

    Skips silently (returns None) when called under pytest/unittest without an explicit
    ``path`` — the test suite must not pollute the real corpus. Never raises.
    """
    try:
        import sys

        if path is None and ("pytest" in sys.modules or "unittest" in sys.modules):
            return None
        rec: dict[str, object] = {
            "ts": ts or datetime.now(UTC).isoformat(),
            "task_class": task_class,
            "chosen_model": chosen_model,
            "lane": lane,
            "fell_back": bool(fell_back),
            "source": source,
        }
        if outcome is not None:
            rec["outcome"] = outcome
        sink = path or DEFAULT_LOG
        sink.parent.mkdir(parents=True, exist_ok=True)
        with sink.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        return rec
    except Exception:
        return None


def read_routing_decisions(
    *,
    task_class: str | None = None,
    fell_back: bool | None = None,
    path: Path | None = None,
) -> list[dict]:
    """Load routing-decision records, optionally filtered by task class / fallback flag."""
    sink = path or DEFAULT_LOG
    if not sink.exists():
        return []
    out: list[dict] = []
    for rec in _iter_lines(sink):
        if task_class is not None and rec.get("task_class") != task_class:
            continue
        if fell_back is not None and bool(rec.get("fell_back")) != fell_back:
            continue
        out.append(rec)
    return out


def _iter_lines(sink: Path) -> Iterator[dict]:
    with sink.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
