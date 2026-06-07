"""Cross-loop telemetry — a READ-ONLY aggregator over the three self-improvement loop artifacts.

Item 25 (thread A). The build loop (`docs/IMPROVEMENT_BACKLOG.md`), the wiring-sweep loop
(`docs/audits/WIRING_SWEEP_LEDGER.md`), and the research loop (`docs/research/BLEEDING_EDGE_FEED.md`)
each write a durable artifact. This module parses their current state into one queryable summary —
what the ad-hoc HTML status report computed inline, made a tested instrument. Pure read-only:
counts are derived from the files on every call (never cached, never written), so they cannot go
stale relative to the source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_BACKLOG = _REPO / "docs" / "IMPROVEMENT_BACKLOG.md"
_DEFAULT_LEDGER = _REPO / "docs" / "audits" / "WIRING_SWEEP_LEDGER.md"
_DEFAULT_FEED = _REPO / "docs" / "research" / "BLEEDING_EDGE_FEED.md"

# A backlog ROW starts with ``| <number> |``; its STATUS is the last pipe-delimited cell.
_BACKLOG_ROW = re.compile(r"^\|\s*\d+\s*\|")
# A swept-package table row: ``| <pkg> | **DONE** | …`` (the 2nd cell is exactly **DONE**).
_LEDGER_DONE = re.compile(r"^\|\s*[\w/]+\s*\|\s*\*\*DONE\*\*\s*\|")
# A research round header: ``## … (round N)``.
_ROUND_HEADER = re.compile(r"^##\s.*round\s*\d+", re.IGNORECASE)


@dataclass(frozen=True)
class LoopTelemetry:
    """A snapshot of the three loops' progress, derived from their artifacts."""

    backlog_done: int
    backlog_todo: int
    backlog_blocked: int
    swept_packages_done: int
    research_rounds: int


def _read(path: Path | None, default: Path) -> list[str]:
    p = path or default
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []  # missing/unreadable → empty (graceful zeros, never a crash)


def _status_first_word(row: str) -> str:
    """The first word of a backlog row's LAST pipe-delimited cell (its status)."""
    cells = [c.strip() for c in row.split("|") if c.strip()]
    if not cells:
        return ""
    return cells[-1].split()[0] if cells[-1].split() else ""


def loop_telemetry(
    *,
    backlog_path: Path | None = None,
    ledger_path: Path | None = None,
    feed_path: Path | None = None,
) -> LoopTelemetry:
    """Aggregate the three loop artifacts into one summary. READ-ONLY — never writes.

    Counts are exact: backlog DONE/TODO/BLOCKED come from the status cell of each numbered row
    (prose mentions are ignored); swept-package DONE from the ledger table's ``**DONE**`` rows;
    research rounds from ``## … (round N)`` headers. Missing files yield zeros, not an error.
    """
    backlog = _read(backlog_path, _DEFAULT_BACKLOG)
    done = todo = blocked = 0
    for line in backlog:
        if not _BACKLOG_ROW.match(line):
            continue
        status = _status_first_word(line).upper()
        if status == "DONE":
            done += 1
        elif status == "TODO":
            todo += 1
        elif status == "BLOCKED":
            blocked += 1

    ledger = _read(ledger_path, _DEFAULT_LEDGER)
    swept_done = sum(1 for line in ledger if _LEDGER_DONE.match(line))

    feed = _read(feed_path, _DEFAULT_FEED)
    rounds = sum(1 for line in feed if _ROUND_HEADER.match(line))

    return LoopTelemetry(
        backlog_done=done,
        backlog_todo=todo,
        backlog_blocked=blocked,
        swept_packages_done=swept_done,
        research_rounds=rounds,
    )


@dataclass(frozen=True)
class StallReport:
    """The verdict of comparing two LoopTelemetry snapshots. REPORT-ONLY (proposes, never acts)."""

    stalled: bool
    reason: str


def detect_loop_stall(before: LoopTelemetry, after: LoopTelemetry) -> StallReport:
    """Flag a STALLED build loop across two telemetry snapshots (item 30, extends item 25).

    A stall is *outstanding work with no completions between snapshots*:
      - ``backlog_done`` unchanged while ``backlog_todo > 0`` (items remain but none completed), OR
      - ``backlog_blocked`` grew while ``backlog_done`` did not (work piling into BLOCKED).

    NOT a stall:
      - ``backlog_done`` advanced → healthy progress.
      - identical snapshots with ``backlog_todo == 0`` and no new BLOCKED → quiescent (nothing
        left to do — done, not stuck). This guards against the naive "done unchanged ⇒ stalled"
        impl that would false-flag an empty backlog.

    Report-only: returns a verdict; it never mutates state or acts on the flag.
    """
    if after.backlog_done > before.backlog_done:
        return StallReport(
            False, f"healthy: backlog_done {before.backlog_done}->{after.backlog_done}"
        )
    # From here, DONE did not advance.
    if after.backlog_todo > 0:
        return StallReport(
            True, f"stalled: no DONE progress with {after.backlog_todo} TODO remaining"
        )
    if after.backlog_blocked > before.backlog_blocked:
        return StallReport(
            True,
            f"stalled: BLOCKED grew {before.backlog_blocked}->{after.backlog_blocked} "
            "with no DONE progress",
        )
    return StallReport(False, "quiescent: no TODO remaining and no new BLOCKED — not a stall")


@dataclass(frozen=True)
class LoopProgressDelta:
    """Signed per-field delta between two LoopTelemetry snapshots (item 39, extends item 25).

    Mirrors the harness-blessed ``DegradationDetector.diff_snapshots`` (CB11) pure-delta pattern:
    deltas are HONEST and SIGNED — a regression (DONE or swept count dropping) shows as a NEGATIVE
    delta, never clamped to zero. Both ``detect_loop_stall`` (item 30) and the Fleet-Health
    Specialist (item 36) can consume this as the numeric layer under their verdicts.
    """

    done_delta: int
    todo_delta: int
    blocked_delta: int
    swept_delta: int
    rounds_delta: int


def loop_progress_delta(before: LoopTelemetry, after: LoopTelemetry) -> LoopProgressDelta:
    """The signed ``after - before`` delta for each LoopTelemetry field. Pure (no I/O, no writes).

    Report-only: a structured numeric diff, never clamped or absolute-valued, so a regression is
    visible as a negative component (e.g. a backlog where items were re-opened, or a swept-package
    count corrected downward).
    """
    return LoopProgressDelta(
        done_delta=after.backlog_done - before.backlog_done,
        todo_delta=after.backlog_todo - before.backlog_todo,
        blocked_delta=after.backlog_blocked - before.backlog_blocked,
        swept_delta=after.swept_packages_done - before.swept_packages_done,
        rounds_delta=after.research_rounds - before.research_rounds,
    )


@dataclass(frozen=True)
class RegressionReport:
    """Verdict of comparing two snapshots for a REGRESSION (item 58). REPORT-ONLY."""

    regressed: bool
    reason: str


def detect_loop_regression(before: LoopTelemetry, after: LoopTelemetry) -> RegressionReport:
    """Flag a REGRESSION — a monotone-should-increase count moved BACKWARD (item 58).

    Consumes item-39 ``loop_progress_delta``: a regression is ``done_delta < 0`` OR ``swept_delta < 0``
    OR ``rounds_delta < 0`` — work that was completed/swept/researched became un-done. This is the
    predicate that justifies item 39's UNCLAMPED signed delta (a clamped delta could never go
    negative, so it could not express this).

    Distinct from item-30's STALL (no *progress*): a regression is *negative* progress (worse). New
    TODO work (``todo_delta > 0``) is healthy growth, NOT a regression; growing ``blocked`` is stall
    territory, NOT a regression. Report-only; pure.
    """
    delta = loop_progress_delta(before, after)
    backward: list[str] = []
    if delta.done_delta < 0:
        backward.append(f"done {before.backlog_done}->{after.backlog_done}")
    if delta.swept_delta < 0:
        backward.append(f"swept {before.swept_packages_done}->{after.swept_packages_done}")
    if delta.rounds_delta < 0:
        backward.append(f"rounds {before.research_rounds}->{after.research_rounds}")
    if backward:
        return RegressionReport(True, "regression: " + "; ".join(backward))
    return RegressionReport(
        False, "no regression: no completed/swept/researched count moved backward"
    )
