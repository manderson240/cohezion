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
from dataclasses import dataclass
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


# ── item 9: routing corpus → autoresearch tuning proposals ───────────────────────────────
@dataclass(frozen=True)
class TuningProposal:
    """A measurable, evidence-backed tuning suggestion derived from the routing corpus."""

    kind: str  # "recruit_specialist" (a task class chronically falls back → needs a specialist)
    target: str  # the task_class (or lane) the proposal is about
    evidence: str  # human-readable justification
    metric: float  # the driving statistic (e.g. fallback rate) — higher = more urgent


def propose_tuning(
    records: list[dict],
    *,
    min_samples: int = 5,
    fallback_threshold: float = 0.5,
) -> list[TuningProposal]:
    """Derive tuning proposals from routing-decision records. Empty/insufficient → [].

    This closes the agentic self-improvement loop (item 9): the autoresearch loop feeds the
    corpus produced by ``record_routing_decision`` (item 2) here, and acts on the proposals.
    The only currently-derivable signal is *chronic fallback*: a task class whose decisions
    fall back to the complexity router more than ``fallback_threshold`` of the time over at
    least ``min_samples`` samples is missing a task-specialist — propose recruiting one
    (the Hebbian-recruitment seed, item 14). Below ``min_samples`` is treated as noise, never
    a signal — so a fresh/empty corpus honestly yields no proposal (UNPROVEN), never a
    fabricated one.
    """
    by_class: dict[str, list[dict]] = {}
    for rec in records:
        tc = rec.get("task_class")
        if tc:
            by_class.setdefault(str(tc), []).append(rec)

    proposals: list[TuningProposal] = []
    for task_class, recs in by_class.items():
        if len(recs) < min_samples:
            continue  # not enough evidence — do not propose from noise
        fallback_rate = sum(1 for r in recs if r.get("fell_back")) / len(recs)
        if fallback_rate > fallback_threshold:
            proposals.append(
                TuningProposal(
                    kind="recruit_specialist",
                    target=task_class,
                    evidence=(
                        f"{task_class}: {fallback_rate:.0%} of {len(recs)} routing decisions "
                        f"fell back to the complexity router — a task-specialist is missing."
                    ),
                    metric=round(fallback_rate, 4),
                )
            )
    return sorted(proposals, key=lambda p: -p.metric)


def propose_tuning_from_log(
    *,
    path: Path | None = None,
    min_samples: int = 5,
    fallback_threshold: float = 0.5,
) -> list[TuningProposal]:
    """Read the routing corpus and derive tuning proposals. No corpus → [] (honest UNPROVEN)."""
    records = read_routing_decisions(path=path)
    return propose_tuning(
        records, min_samples=min_samples, fallback_threshold=fallback_threshold
    )


# ── item 14: Hebbian specialist recruitment (proposes, never registers) ──────────────────
# Task class → suggested lane. Light/classification tasks recruit onto the cheap NPU; most
# generation/extraction tasks onto the iGPU; deep-reasoning tasks onto the CPU. Heuristic only —
# a human reviewing the proposal picks the concrete model.
_TASK_LANE_HINT: dict[str, str] = {
    "ROUTING": "npu",
    "SENSING": "npu",
    "REASONING": "cpu",
    "MATH": "cpu",
    "LONG_HORIZON": "cpu",
    "ARCHITECT": "cpu",
    "GOVERNANCE": "cpu",
}
_DEFAULT_LANE_HINT = "igpu_rocwmma"  # EXTRACTION/VISION/CODE_GEN/STRUCTURED/FUNCTION_CALL/RERANK/…


@dataclass(frozen=True)
class SpecialistProposal:
    """A concrete, HUMAN-GATED recruitment suggestion. Proposes a task→lane specialist; a human
    reviews and picks the model. Never auto-registers into the FleetRegistry."""

    task_class: str
    suggested_lane: str
    fallback_rate: float
    rationale: str


def propose_specialists(
    records: list[dict],
    *,
    min_samples: int = 5,
    fallback_threshold: float = 0.5,
) -> list[SpecialistProposal]:
    """Enrich item-9's recruit_specialist signals into concrete specialist proposals.

    For each task class that chronically falls back (via :func:`propose_tuning`), suggest a
    lane (cheap NPU for routing/sensing, CPU for deep reasoning, iGPU otherwise). HUMAN-GATED:
    this returns proposals and NEVER touches the registry. Empty/healthy corpus → [].
    """
    proposals: list[SpecialistProposal] = []
    for tuning in propose_tuning(
        records, min_samples=min_samples, fallback_threshold=fallback_threshold
    ):
        if tuning.kind != "recruit_specialist":
            continue
        lane = _TASK_LANE_HINT.get(tuning.target, _DEFAULT_LANE_HINT)
        proposals.append(
            SpecialistProposal(
                task_class=tuning.target,
                suggested_lane=lane,
                fallback_rate=tuning.metric,
                rationale=(
                    f"{tuning.target} falls back {tuning.metric:.0%} of the time → recruit a "
                    f"{lane} specialist. PROPOSAL ONLY — a human picks the model and registers it."
                ),
            )
        )
    return proposals
