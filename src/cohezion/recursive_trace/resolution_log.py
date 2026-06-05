"""Single-writer for failure-resolution pairs (the collection primitive).

Design: docs/research/FAILURE_RESOLUTION_COLLECTION_DESIGN_2026-06-05.md

All three remediation hook points (AutoDQA, SkillMutationQueue, DegradationDetector)
call `record_resolution(...)`, which appends one domain-tagged JSON line to the corpus
the value gate scans. `read_resolutions()` loads them back for analysis. The default
sink is `~/.cohezion-research/logs/resolution_log.jsonl`; tests inject a temp path.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_LOG = Path.home() / ".cohezion-research" / "logs" / "resolution_log.jsonl"
VALID_DOMAINS = {"quality_gate", "skill_mutation", "routing"}


def record_resolution(
    domain: str,
    failure_class: str,
    strategy: str,
    success: bool,
    *,
    source: str = "live",
    tried_order: list[str] | None = None,
    task_hash: str | None = None,
    ts: str | None = None,
    path: Path | None = None,
) -> dict:
    """Append one resolution record. Returns the written dict.

    `domain` must be one of VALID_DOMAINS — a typo silently mis-buckets the gate's
    per-domain analysis, so it is validated, not coerced.
    """
    if domain not in VALID_DOMAINS:
        raise ValueError(f"unknown domain {domain!r}; expected one of {sorted(VALID_DOMAINS)}")
    rec = {
        "ts": ts or datetime.now(UTC).isoformat(),
        "domain": domain,
        "failure_class": failure_class,
        "strategy": strategy,
        "success": bool(success),
        "source": source,
    }
    if tried_order is not None:
        rec["tried_order"] = list(tried_order)
    if task_hash is not None:
        rec["task_hash"] = task_hash

    sink = path or DEFAULT_LOG
    sink.parent.mkdir(parents=True, exist_ok=True)
    with sink.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def read_resolutions(
    domain: str | None = None,
    *,
    successful_only: bool = False,
    path: Path | None = None,
) -> list[dict]:
    """Load resolution records, optionally filtered by domain / success."""
    sink = path or DEFAULT_LOG
    if not sink.exists():
        return []
    out: list[dict] = []
    for rec in _iter_lines(sink):
        if domain is not None and rec.get("domain") != domain:
            continue
        if successful_only and not rec.get("success"):
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
