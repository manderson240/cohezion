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


def _coarse_tier(model_name: str) -> str:
    """Collapse a model id to a coarse hardware-tier strategy label (fewer = better stats)."""
    m = (model_name or "").lower()
    if "flm" in m or "gemma-4-e2b" in m or "npu" in m:
        return "npu"
    if "gemma-4-26b" in m or "gemma-4-e4b" in m or "igpu" in m:
        return "igpu"
    if "claude" in m or "gpt" in m or "gemini" in m or "cloud" in m:
        return "cloud"
    return "cpu"


def log_quality_gate_resolution(
    output_type: str,
    resolving_model: str,
    tried_models: list[str],
    *,
    path: Path | None = None,
) -> dict | None:
    """Fail-soft hook for the orchestrator: log an ESCALATED resolution pair.

    Called only when escalation occurred (a lower tier's gate failed and a higher tier
    resolved) — the non-circular case where a counterfactual was actually observed. Never
    raises (must not break the inference path). Skips writing under pytest unless an
    explicit `path` is given (so the orchestrator's own tests don't pollute the corpus).
    """
    try:
        import sys

        if path is None and ("pytest" in sys.modules or "unittest" in sys.modules):
            return None
        return record_resolution(
            "quality_gate",
            output_type,
            _coarse_tier(resolving_model),
            True,
            source="live",
            tried_order=[_coarse_tier(m) for m in tried_models],
            path=path,
        )
    except Exception:
        return None


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
