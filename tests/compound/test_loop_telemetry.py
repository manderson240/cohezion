"""Discriminating tests for the cross-loop telemetry instrument (item 25, 2026-06-06).

A read-only aggregator over the 3 self-improvement loop artifacts (IMPROVEMENT_BACKLOG status
counts, WIRING_SWEEP_LEDGER swept-package table, BLEEDING_EDGE_FEED round count). The falsifiable
check (item 25): returned counts EXACTLY match the source files. Tests use SYNTHETIC fixtures with
KNOWN counts so a hardcoded/stale-count impl fails, plus a read-only guard (the source bytes must
be unchanged after the call).
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.loop_telemetry import LoopTelemetry, loop_telemetry


_BACKLOG = """\
| 1 | A | **x** | check | additive | DONE abc123 (did it) |
| 2 | B | **y** | check | additive | DONE def456 |
| 3 | C | **z** | check | additive | TODO |
| 18 | B | **blocked one** | check | needs | BLOCKED (assets) — needs HUMAN |
## Notes
- prose mentioning DONE and TODO that must NOT be counted as rows.
"""

_LEDGER = """\
## Swept packages
| Package | Swept | A wired |
|---|---|---|
| compound | **DONE** | 9 |
| inference | **DONE** | 1 |
| world_model | in progress | 1/3 |
### a section header that says DONE but is not a table row
"""

_FEED = """\
# Bleeding-edge feed
## 2026-06-06 (round 1)
some rows
## 2026-06-06 (round 2)
more rows
## Notes (not a round header)
"""


def _write(tmp: Path) -> tuple[Path, Path, Path]:
    b, l, f = tmp / "backlog.md", tmp / "ledger.md", tmp / "feed.md"
    b.write_text(_BACKLOG)
    l.write_text(_LEDGER)
    f.write_text(_FEED)
    return b, l, f


def test_counts_match_source_exactly(tmp_path: Path) -> None:
    b, l, f = _write(tmp_path)
    t = loop_telemetry(backlog_path=b, ledger_path=l, feed_path=f)
    assert isinstance(t, LoopTelemetry)
    # 2 DONE / 1 TODO / 1 BLOCKED rows (prose DONE/TODO in ## Notes must NOT count)
    assert t.backlog_done == 2
    assert t.backlog_todo == 1
    assert t.backlog_blocked == 1
    # 2 **DONE** table rows ("in progress" + the prose header must NOT count)
    assert t.swept_packages_done == 2
    # 2 round headers ("## Notes" must NOT count)
    assert t.research_rounds == 2


def test_is_read_only_source_bytes_unchanged(tmp_path: Path) -> None:
    b, l, f = _write(tmp_path)
    before = (b.read_bytes(), l.read_bytes(), f.read_bytes())
    loop_telemetry(backlog_path=b, ledger_path=l, feed_path=f)
    after = (b.read_bytes(), l.read_bytes(), f.read_bytes())
    assert before == after, "loop_telemetry must be READ-ONLY — it modified a source file"


def test_missing_files_are_zeros_not_a_crash(tmp_path: Path) -> None:
    t = loop_telemetry(
        backlog_path=tmp_path / "nope1.md",
        ledger_path=tmp_path / "nope2.md",
        feed_path=tmp_path / "nope3.md",
    )
    assert t.backlog_done == 0 and t.backlog_todo == 0 and t.backlog_blocked == 0
    assert t.swept_packages_done == 0 and t.research_rounds == 0
