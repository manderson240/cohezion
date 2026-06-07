"""Discriminating tests for the research-feed structured parser (item 49, 2026-06-06).

`parse_research_feed(feed_path)` parses BLEEDING_EDGE_FEED.md's markdown tables into typed records
{finding, verified, classes, fleet_seam, round}; `feed_dedup_hits(records)` flags a finding logged in
>=2 rounds. Report-only — makes the research loop's verify-dedup output machine-queryable. Prompted by
bigset's DATA DISCIPLINE (verified+dedup'd+queryable), not its SaaS product.

Each test fails a plausible wrong impl:
  - wrong record count / wrong round assignment → test_k_rows_k_records,
  - misses a cross-round duplicate or flags a unique finding → test_dedup_across_rounds,
  - parses round headers / prose as records → test_headers_and_prose_ignored,
  - crashes on missing feed → test_missing_empty.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.research_feed_parser import (
    FeedRecord,
    feed_dedup_hits,
    parse_research_feed,
)


_FEED = """\
# Bleeding-edge feed

## Round 1 — 2026-06-01 (source)
| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`foo`** thing | ✅ yes | NEW · additive | seamA | note one |
| **`bar`** thing | ✅ yes | declined | seamB | note two |

some prose line, not a table.

## Round 2 — 2026-06-02 (source)
| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`foo`** again | ✅ yes | NEW | seamC | note three |
"""


def _write(tmp_path: Path) -> Path:
    f = tmp_path / "FEED.md"
    f.write_text(_FEED)
    return f


def test_k_rows_k_records(tmp_path: Path) -> None:
    recs = parse_research_feed(_write(tmp_path))
    assert len(recs) == 3
    assert all(isinstance(r, FeedRecord) for r in recs)
    by_seam = {r.fleet_seam: r for r in recs}
    assert by_seam["seamA"].round == 1
    assert by_seam["seamA"].finding == "foo"
    assert by_seam["seamA"].classes == "NEW · additive"
    assert by_seam["seamC"].round == 2  # second round assigned correctly


def test_dedup_across_rounds(tmp_path: Path) -> None:
    hits = feed_dedup_hits(parse_research_feed(_write(tmp_path)))
    assert hits == {"foo": [1, 2]}  # foo in both rounds; bar (unique) not flagged
    assert "bar" not in hits


def test_headers_and_prose_ignored(tmp_path: Path) -> None:
    recs = parse_research_feed(_write(tmp_path))
    # No record's finding is a round header or prose fragment.
    findings = {r.finding for r in recs}
    assert findings == {"foo", "bar"}
    assert all("Round" not in r.finding for r in recs)


def test_both_round_header_conventions(tmp_path: Path) -> None:
    # The feed uses BOTH `## Round N — date` and `## date (round N)` — parse both.
    f = tmp_path / "FEED2.md"
    f.write_text(
        "## 2026-06-01 (round 3)\n"
        "| Finding | Verified | Class | Fleet seam | Notes |\n"
        "|---|---|---|---|---|\n"
        "| **`baz`** | ✅ | NEW | seamX | n |\n"
    )
    recs = parse_research_feed(f)
    assert len(recs) == 1
    assert recs[0].round == 3 and recs[0].finding == "baz"


def test_missing_empty(tmp_path: Path) -> None:
    assert parse_research_feed(tmp_path / "nope.md") == []
    (tmp_path / "empty.md").write_text("")
    assert parse_research_feed(tmp_path / "empty.md") == []
    assert feed_dedup_hits([]) == {}
