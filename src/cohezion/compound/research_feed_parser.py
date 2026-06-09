"""Research-feed structured parser (item 49, 2026-06-06) — report-only.

Parses ``BLEEDING_EDGE_FEED.md``'s markdown tables into typed records so the research loop's
verify-dedup output becomes machine-queryable (prompted by bigset's DATA DISCIPLINE — verified +
dedup'd + queryable — NOT its TS-SaaS product). Mirrors the section-scoped line-parsing of item-25
``loop_telemetry`` / item-31 ``unswept_packages_from_ledger``. Pure — read-only, no writes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_FEED = _REPO / "docs" / "research" / "BLEEDING_EDGE_FEED.md"
_DEFAULT_BACKLOG = _REPO / "docs" / "IMPROVEMENT_BACKLOG.md"
# The feed uses TWO header conventions: `## Round N — date` (recent) and `## date (round N)`
# (earlier). Match a `##` line containing `round <N>` in either position.
_ROUND_HEADER = re.compile(r"^##.*?\bround\s+(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class FeedRecord:
    """One parsed feed table row. ``round`` is the enclosing ``## Round N`` header."""

    finding: str  # normalized finding id (first `backtick` token, else bolded text)
    verified: str
    classes: str
    fleet_seam: str
    round: int


def _finding_id(cell: str) -> str:
    """Normalized finding id from the first cell: first ``backtick`` token, else bolded text."""
    btick = re.search(r"`([^`]+)`", cell)
    if btick:
        return btick.group(1).strip()
    bold = re.search(r"\*\*(.+?)\*\*", cell)
    if bold:
        return bold.group(1).strip()
    return cell.strip()


def parse_research_feed(feed_path: Path | None = None) -> list[FeedRecord]:
    """Parse the feed's per-round markdown tables into ``FeedRecord``s. Pure/read-only.

    Tracks the current round from ``## Round N`` headers; a table DATA row (>=5 cells, not the
    header/separator, inside a round) becomes one record using cells 0-3 (Notes is ignored, so a
    ``|`` inside Notes does not corrupt parsing). Missing/unreadable feed → ``[]`` (never raises).
    """
    path = feed_path or _DEFAULT_FEED
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    out: list[FeedRecord] = []
    current_round: int | None = None
    for line in lines:
        header = _ROUND_HEADER.match(line.strip())
        if header:
            current_round = int(header.group(1))
            continue
        if current_round is None or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue  # not a 5-col feed row
        first = cells[0]
        if first.startswith("Finding") or set(first) <= set("-: "):
            continue  # header row or |---| separator
        out.append(
            FeedRecord(
                finding=_finding_id(first),
                verified=cells[1],
                classes=cells[2],
                fleet_seam=cells[3],
                round=current_round,
            )
        )
    return out


@dataclass(frozen=True)
class CrossrefReport:
    """Research→build traceability: which verified findings became backlog items vs dropped."""

    actioned: list[tuple[str, int]]  # (finding, backlog item number) — logged AND in a backlog row
    dropped: list[str]  # findings with NO backlog row (logged then dropped)


_BACKLOG_ITEM_ROW = re.compile(r"^\|\s*(\d+)\s*\|")


def _backlog_rows(backlog_path: Path) -> list[tuple[int, str]]:
    """Backlog item rows → ``[(item_number, full_row_text), ...]``. Missing/unreadable → ``[]``."""
    try:
        lines = backlog_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[tuple[int, str]] = []
    for line in lines:
        m = _BACKLOG_ITEM_ROW.match(line)
        if m:
            rows.append((int(m.group(1)), line))
    return rows


def feed_backlog_crossref(
    *, feed_path: Path | None = None, backlog_path: Path | None = None
) -> CrossrefReport:
    """For each VERIFIED feed finding, did it become a backlog item (actioned) or get dropped?

    Composes item-49 :func:`parse_research_feed` + the backlog. A finding is *actioned* if its
    normalized id appears (case-insensitive substring) in some backlog row → ``(finding, item#)``;
    else *dropped*. A finding logged in multiple rounds is counted ONCE (first-seen order).
    Report-only, pure/read-only. Missing/unreadable inputs → empty report (never raises).
    """
    records = parse_research_feed(feed_path)
    rows = _backlog_rows(backlog_path or _DEFAULT_BACKLOG)

    seen: set[str] = set()
    actioned: list[tuple[str, int]] = []
    dropped: list[str] = []
    for rec in records:
        finding = rec.finding
        if finding in seen:
            continue  # a finding in >=2 rounds is counted once
        seen.add(finding)
        needle = finding.lower()
        item = next((num for num, text in rows if needle in text.lower()), None)
        if item is not None:
            actioned.append((finding, item))
        else:
            dropped.append(finding)
    return CrossrefReport(actioned=actioned, dropped=dropped)


def feed_dedup_hits(records: Iterable[FeedRecord]) -> dict[str, list[int]]:
    """Findings logged in >=2 DISTINCT rounds → ``{finding: [sorted rounds]}``. Pure.

    The dedup signal the research loop's verify-dedup discipline implies: a finding re-surfacing
    across rounds. A finding in a single round (even if listed twice) is NOT a cross-round dup.
    """
    rounds_by_finding: dict[str, set[int]] = {}
    for r in records:
        rounds_by_finding.setdefault(r.finding, set()).add(r.round)
    return {
        finding: sorted(rounds) for finding, rounds in rounds_by_finding.items() if len(rounds) >= 2
    }


def persistently_dropped_findings(
    *, feed_path: Path | None = None, backlog_path: Path | None = None
) -> list[tuple[str, list[int]]]:
    """Findings the research loop keeps NOTICING but never INTEGRATES (item 125) — report-only.

    The CONJUNCTION of item-71 :func:`feed_backlog_crossref` (DROPPED — no backlog row) AND item-49
    :func:`feed_dedup_hits` (RE-SURFACED in >=2 distinct rounds): a finding that is both is a
    stronger "you keep ignoring this verified lever" signal than either alone. Returns
    ``[(finding, [sorted rounds]), ...]`` sorted most-persistent-first (round count desc, then id),
    so it reads as a prioritized "reconsider these" list.

    The conjunction is load-bearing: an ACTIONED finding is excluded even if it recurs (it is already
    integrated, so it is in ``crossref.actioned`` not ``.dropped``); a single-round drop is excluded
    (a one-off drop is normal, not a persistent miss). Report-only — proposes reconsideration, never
    auto-creates a backlog item (that is the build loop's call). Pure/read-only; missing/unreadable
    inputs → ``[]`` (never raises).
    """
    records = parse_research_feed(feed_path)
    dropped = set(feed_backlog_crossref(feed_path=feed_path, backlog_path=backlog_path).dropped)
    recurring = feed_dedup_hits(records)
    flagged = [(finding, rounds) for finding, rounds in recurring.items() if finding in dropped]
    flagged.sort(key=lambda item: (-len(item[1]), item[0]))
    return flagged
