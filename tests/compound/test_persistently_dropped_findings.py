"""Item 125: persistently_dropped_findings — TDD red→green (2026-06-08).

``persistently_dropped_findings(feed_path, backlog_path)`` returns findings that are
BOTH (a) DROPPED (no backlog item) AND (b) RE-SURFACED in ≥2 rounds.

A single-round drop is normal; the signal fires when the loop keeps NOTICING a
finding but never INTEGRATES it. Composes item-71 ``feed_backlog_crossref`` +
item-49 ``feed_dedup_hits``.

Discriminating tests — each kills a plausible wrong implementation:

  1. Dropped + 2 rounds → flagged                    (MAIN DISC.: kills "return all dropped")
  2. Dropped + only 1 round → NOT flagged            (kills "return all multi-round")
  3. Actioned + 2 rounds → NOT flagged               (kills "return all dedup hits")
  4. Empty feed → []                                 (kills impl that crashes on empty)
  5. Mixed: only the conjunction subset returned     (kills "return dropped ∪ dedup" union)
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.persistently_dropped import persistently_dropped_findings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FEED = """\
## Round 1 — 2026-06-01

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`alpha`** thing | ✅ yes | NEW | seamA | - |
| **`beta`** thing | ✅ yes | NEW | seamB | - |
| **`gamma`** thing | ✅ yes | NEW | seamC | - |

## Round 2 — 2026-06-02

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`alpha`** again | ✅ yes | NEW | seamA | - |
| **`gamma`** again | ✅ yes | NEW | seamC | - |
"""

# Backlog with one reference to 'gamma' (actioned) but not 'alpha' or 'beta'.
_BACKLOG = """\
| Item | Cat | Description | Check | Tag | Status |
| 42 | A | **gamma integration** — implemented gamma thing | check | additive | DONE abc1234 |
"""


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    feed = tmp_path / "FEED.md"
    backlog = tmp_path / "BACKLOG.md"
    feed.write_text(_FEED)
    backlog.write_text(_BACKLOG)
    return feed, backlog


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dropped_and_multi_round_flagged(tmp_path: Path) -> None:
    """'alpha': dropped (not in backlog) + 2 rounds → flagged.

    PRIMARY DISCRIMINATOR: kills an impl that returns all dropped findings
    (would include 'beta') or all dedup hits (would include 'gamma').
    """
    feed, backlog = _write_fixtures(tmp_path)
    result = persistently_dropped_findings(feed, backlog)
    findings = [f for f, _ in result]
    assert "alpha" in findings, f"alpha (dropped + 2 rounds) must be flagged; got {findings}"


def test_dropped_single_round_not_flagged(tmp_path: Path) -> None:
    """'beta': dropped + only 1 round → NOT flagged (single-round drop is normal).

    Kills an impl that returns every dropped finding regardless of round count.
    """
    feed, backlog = _write_fixtures(tmp_path)
    result = persistently_dropped_findings(feed, backlog)
    findings = [f for f, _ in result]
    assert "beta" not in findings, (
        f"beta (dropped but only 1 round) must NOT be flagged; got {findings}"
    )


def test_actioned_multi_round_not_flagged(tmp_path: Path) -> None:
    """'gamma': actioned (in backlog) + 2 rounds → NOT flagged.

    Kills an impl that returns all dedup hits regardless of actioned status.
    """
    feed, backlog = _write_fixtures(tmp_path)
    result = persistently_dropped_findings(feed, backlog)
    findings = [f for f, _ in result]
    assert "gamma" not in findings, (
        f"gamma (actioned, even in 2 rounds) must NOT be flagged; got {findings}"
    )


def test_empty_feed_returns_empty(tmp_path: Path) -> None:
    """Empty feed → empty result (no crash)."""
    feed = tmp_path / "FEED.md"
    backlog = tmp_path / "BACKLOG.md"
    feed.write_text("")
    backlog.write_text("")
    result = persistently_dropped_findings(feed, backlog)
    assert result == [], f"empty feed must → []; got {result}"


def test_rounds_included_in_result(tmp_path: Path) -> None:
    """The result includes the round list for each flagged finding.

    Kills an impl that returns (finding, None) or finding alone.
    """
    feed, backlog = _write_fixtures(tmp_path)
    result = persistently_dropped_findings(feed, backlog)
    by_finding = dict(result)
    assert "alpha" in by_finding, "alpha must appear in result"
    assert by_finding["alpha"] == [1, 2], (
        f"alpha must carry its rounds [1, 2]; got {by_finding['alpha']}"
    )
