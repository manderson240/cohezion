"""Discriminating tests for feed_backlog_crossref (backlog item 71, 2026-06-07).

Closes research→build traceability: for each VERIFIED feed finding, did it become a backlog
item (actioned) or get logged-and-dropped? Composes item-49 `parse_research_feed`. Report-only.

Each test fails a plausible wrong impl:
  - an impl that calls everything actioned → test_dropped_finding_not_in_backlog,
  - an impl that double-counts a finding logged in 2 rounds → test_finding_in_two_rounds_once,
  - an impl that crashes on missing files instead of empty report → test_empty_missing,
  - an impl that returns the wrong item number → test_actioned_maps_to_correct_item.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.research_feed_parser import CrossrefReport, feed_backlog_crossref


_FEED = """
## Round 1 — test
| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **ActionedModel** is a thing | ok | NEW | seam | n |
| **DroppedModel** is a thing | ok | NEW | seam | n |

## Round 2 — test
| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **ActionedModel** is a thing | ok | NEW | seam | n |
"""

_BACKLOG = """
| 99 | M | **ActionedModel registration** (a real seam) | falsifiable check | TODO |
| 100 | A | **Unrelated item** (something else entirely) | falsifiable check | TODO |
"""


def _write(tmp_path: Path) -> tuple[Path, Path]:
    feed = tmp_path / "feed.md"
    feed.write_text(_FEED, encoding="utf-8")
    backlog = tmp_path / "backlog.md"
    backlog.write_text(_BACKLOG, encoding="utf-8")
    return feed, backlog


def test_actioned_maps_to_correct_item(tmp_path: Path) -> None:
    feed, backlog = _write(tmp_path)
    rep = feed_backlog_crossref(feed_path=feed, backlog_path=backlog)
    assert isinstance(rep, CrossrefReport)
    assert ("ActionedModel", 99) in rep.actioned  # the RIGHT item number, not 100


def test_dropped_finding_not_in_backlog(tmp_path: Path) -> None:
    feed, backlog = _write(tmp_path)
    rep = feed_backlog_crossref(feed_path=feed, backlog_path=backlog)
    # DroppedModel appears in NO backlog row → dropped (an all-actioned impl fails here).
    assert "DroppedModel" in rep.dropped
    assert all(f != "DroppedModel" for f, _ in rep.actioned)


def test_finding_in_two_rounds_once(tmp_path: Path) -> None:
    feed, backlog = _write(tmp_path)
    rep = feed_backlog_crossref(feed_path=feed, backlog_path=backlog)
    # ActionedModel is in round 1 AND round 2 → counted EXACTLY once across the whole report.
    total = sum(1 for f, _ in rep.actioned if f == "ActionedModel") + rep.dropped.count(
        "ActionedModel"
    )
    assert total == 1


def test_empty_missing(tmp_path: Path) -> None:
    rep = feed_backlog_crossref(feed_path=tmp_path / "nope.md", backlog_path=tmp_path / "nope2.md")
    assert rep.actioned == [] and rep.dropped == []
