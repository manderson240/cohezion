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
    persistently_dropped_findings,
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


# --- item 125: persistently_dropped_findings (DROPPED AND recurring conjunction) -------------
#
# Fixture covers the discriminating TRIPLE so each plausible wrong impl fails on a distinct row:
#   dropthrice  rounds {1,2,3}, no backlog row  -> DROPPED + recurring -> FLAGGED (sorts first)
#   droptwice   rounds {1,2},   no backlog row  -> DROPPED + recurring -> FLAGGED (sorts second)
#   droponce    round  {1},     no backlog row  -> dropped but 1 round  -> NOT (kills "all dropped")
#   kepttwice   rounds {1,2},   has backlog row -> recurring but actioned -> NOT (kills "all dedup")


def _conj_fixture(tmp_path: Path) -> tuple[Path, Path]:
    feed = tmp_path / "FEED_CONJ.md"
    feed.write_text(
        "## Round 1 — d1\n"
        "| Finding | Verified | Class | Fleet seam | Notes |\n"
        "|---|---|---|---|---|\n"
        "| **`dropthrice`** | ✅ | NEW | s1 | n |\n"
        "| **`droptwice`** | ✅ | NEW | s2 | n |\n"
        "| **`droponce`** | ✅ | NEW | s3 | n |\n"
        "| **`kepttwice`** | ✅ | NEW | s4 | n |\n"
        "\n"
        "## Round 2 — d2\n"
        "| Finding | Verified | Class | Fleet seam | Notes |\n"
        "|---|---|---|---|---|\n"
        "| **`dropthrice`** | ✅ | NEW | s1 | n |\n"
        "| **`droptwice`** | ✅ | NEW | s2 | n |\n"
        "| **`kepttwice`** | ✅ | NEW | s4 | n |\n"
        "\n"
        "## Round 3 — d3\n"
        "| Finding | Verified | Class | Fleet seam | Notes |\n"
        "|---|---|---|---|---|\n"
        "| **`dropthrice`** | ✅ | NEW | s1 | n |\n"
    )
    backlog = tmp_path / "BACKLOG_CONJ.md"
    # Only `kepttwice` has a backlog row -> ACTIONED; the three drop* findings have none.
    backlog.write_text(
        "| 200 | A | a lever that uses kepttwice here | verify | additive | TODO |\n"
    )
    return feed, backlog


def test_persistently_dropped_conjunction_and_order(tmp_path: Path) -> None:
    feed, backlog = _conj_fixture(tmp_path)
    out = persistently_dropped_findings(feed_path=feed, backlog_path=backlog)
    # Exact result: only DROPPED-and-recurring findings, most-persistent first (round count desc).
    assert out == [("dropthrice", [1, 2, 3]), ("droptwice", [1, 2])]
    flagged = {f for f, _ in out}
    assert "droponce" not in flagged  # single-round drop -> kills the "return all dropped" impl
    assert "kepttwice" not in flagged  # actioned -> kills the "return all dedup-hits" impl


def test_persistently_dropped_single_round_not_flagged(tmp_path: Path) -> None:
    feed, backlog = _conj_fixture(tmp_path)
    out = dict(persistently_dropped_findings(feed_path=feed, backlog_path=backlog))
    assert "droponce" not in out  # a one-off drop (1 round) is normal, not a persistent miss


def test_persistently_dropped_actioned_not_flagged(tmp_path: Path) -> None:
    feed, backlog = _conj_fixture(tmp_path)
    out = dict(persistently_dropped_findings(feed_path=feed, backlog_path=backlog))
    assert "kepttwice" not in out  # recurred in 2 rounds but already integrated -> excluded


def test_persistently_dropped_empty(tmp_path: Path) -> None:
    out = persistently_dropped_findings(
        feed_path=tmp_path / "nope.md", backlog_path=tmp_path / "nope2.md"
    )
    assert out == []


def test_persistently_dropped_readonly(tmp_path: Path) -> None:
    feed, backlog = _conj_fixture(tmp_path)
    before = (feed.read_bytes(), backlog.read_bytes())
    persistently_dropped_findings(feed_path=feed, backlog_path=backlog)
    assert (feed.read_bytes(), backlog.read_bytes()) == before  # pure: inputs unchanged
    assert feed_dedup_hits([]) == {}
