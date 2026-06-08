"""Item 125: persistently_dropped_findings — report-only (2026-06-08).

``persistently_dropped_findings(feed_path, backlog_path)`` returns findings that are
BOTH (a) DROPPED (no backlog item) AND (b) RE-SURFACED in ≥2 rounds.

A single-round drop is normal; the signal fires when the loop keeps NOTICING a
finding but never INTEGRATES it.  Composes:

  - Item 71 :func:`feed_backlog_crossref` — which findings have no backlog entry
  - Item 49 :func:`feed_dedup_hits` — which findings appeared in ≥2 distinct rounds

Report-only — reads feed and backlog, never writes.  Pure (no live probes, no
asyncio).  Missing/unreadable inputs → ``[]`` (never raises).
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.research_feed_parser import (
    feed_backlog_crossref,
    feed_dedup_hits,
    parse_research_feed,
)


def persistently_dropped_findings(
    feed_path: Path | None = None,
    backlog_path: Path | None = None,
) -> list[tuple[str, list[int]]]:
    """Return findings that are both DROPPED and RE-SURFACED in ≥2 rounds.

    A finding *persistently dropped* when the loop keeps re-noticing it across
    rounds but never creates a backlog item for it.  Single-round drops are normal
    churn; persistence is the signal.

    Args:
        feed_path:
            Path to the research feed markdown (default: ``docs/research/BLEEDING_EDGE_FEED.md``).
        backlog_path:
            Path to the improvement backlog markdown (default: ``docs/IMPROVEMENT_BACKLOG.md``).

    Returns:
        List of ``(finding, [round, ...])`` pairs, sorted by finding name.
        ``rounds`` is the sorted list of round numbers in which the finding appeared.
        Empty list when feed is empty or no findings meet the criterion.

    Pure — no live fleet probe, no asyncio, no writes.
    Report-only — proposes attention targets; the loop driver decides whether to act.
    """
    records = parse_research_feed(feed_path)
    if not records:
        return []

    crossref = feed_backlog_crossref(feed_path=feed_path, backlog_path=backlog_path)
    dedup = feed_dedup_hits(records)

    dropped_set = set(crossref.dropped)
    result = [(finding, rounds) for finding, rounds in dedup.items() if finding in dropped_set]
    return sorted(result, key=lambda x: x[0])
