"""Item 94: coverage_gap_delta() fleet-coverage gap-closure tracker (TDD red→green).

Each test fails a plausible wrong implementation:
  - one that reports a stable gap (present in both) → test_gap_in_both_is_neither
  - one that skips newly-opened gaps → test_new_gap_in_after_is_opened
  - one that skips filled gaps → test_gap_only_in_before_is_filled
  - one using set-union instead of set-difference → test_identical_sets_both_empty
  - one that crashes on empty inputs → test_empty_inputs_both_empty
"""

from __future__ import annotations

from cohezion.inference.local_coverage import coverage_gap_delta


# ---------------------------------------------------------------------------
# T_filled: gap present in before AND absent in after → filled
# Fails: an impl that includes all before-gaps regardless of after.
# ---------------------------------------------------------------------------


def test_gap_only_in_before_is_filled() -> None:
    """A gap in 'before' but not 'after' is filled — a local specialist was registered."""
    before = {"CODE_GEN", "RERANK"}
    after = {"RERANK"}  # CODE_GEN gap was filled
    result = coverage_gap_delta(before, after)
    assert "CODE_GEN" in result["filled"], "gap closed between scans → filled"
    assert "CODE_GEN" not in result["opened"]


# ---------------------------------------------------------------------------
# T_opened: gap absent in before AND in after → opened
# Fails: an impl that only tracks filled gaps.
# ---------------------------------------------------------------------------


def test_new_gap_in_after_is_opened() -> None:
    """A new gap in 'after' (absent from 'before') is opened."""
    before = {"RERANK"}
    after = {"RERANK", "FIM"}  # FIM gap appeared
    result = coverage_gap_delta(before, after)
    assert "FIM" in result["opened"], "new gap between scans → opened"
    assert "FIM" not in result["filled"]


# ---------------------------------------------------------------------------
# T_stable: gap in BOTH lists → in neither (kills an impl that reports every gap)
# Fails: an impl that includes stable gaps in 'opened' or 'filled'.
# ---------------------------------------------------------------------------


def test_gap_in_both_is_neither() -> None:
    """A gap present in BOTH snapshots appears in neither 'filled' nor 'opened'."""
    before = {"RERANK", "CODE_GEN"}
    after = {"RERANK", "CODE_GEN"}  # both gaps stable — neither filled nor opened
    result = coverage_gap_delta(before, after)
    assert "RERANK" not in result["filled"]
    assert "RERANK" not in result["opened"]
    assert "CODE_GEN" not in result["filled"]
    assert "CODE_GEN" not in result["opened"]


# ---------------------------------------------------------------------------
# T_identical: identical snapshots → both dicts empty
# Fails: an impl using set-union or reporting all gaps.
# ---------------------------------------------------------------------------


def test_identical_sets_both_empty() -> None:
    """Identical before and after → both filled and opened are empty."""
    gaps = {"RERANK", "FIM", "OCR_DOC"}
    result = coverage_gap_delta(gaps, gaps)
    assert result["filled"] == set()
    assert result["opened"] == set()


# ---------------------------------------------------------------------------
# T_empty: empty snapshots → empty delta, no crash
# Fails: an impl that crashes on empty set inputs.
# ---------------------------------------------------------------------------


def test_empty_inputs_both_empty() -> None:
    """Two empty gap sets → empty delta."""
    result = coverage_gap_delta(set(), set())
    assert result["filled"] == set()
    assert result["opened"] == set()


# ---------------------------------------------------------------------------
# T_mixed: multiple fills and opens in one transition
# ---------------------------------------------------------------------------


def test_mixed_fills_and_opens() -> None:
    """A realistic fleet transition: some gaps filled, some new ones opened, some stable."""
    before = {"RERANK", "CODE_GEN", "FIM"}
    after = {"FIM", "AUDIO_TTS"}  # RERANK+CODE_GEN filled, AUDIO_TTS opened
    result = coverage_gap_delta(before, after)
    assert result["filled"] == {"RERANK", "CODE_GEN"}
    assert result["opened"] == {"AUDIO_TTS"}
    assert "FIM" not in result["filled"]
    assert "FIM" not in result["opened"]
