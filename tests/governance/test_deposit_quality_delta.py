"""Discriminating tests for deposit_quality_delta (backlog item 74, 2026-06-07).

The quality-TREND monitor after item-52's snapshot: across two `DepositQualityReport`s, is the
growing neuron store getting BETTER or WORSE? `deposit_quality_delta(before, after)` returns
signed counts (redundancy/low_evidence/format_invalid). Mirrors the harness-blessed
`DegradationDetector.diff_snapshots` (CB11) + item-39 `loop_progress_delta` pure-delta family.

Each test fails a plausible wrong impl:
  - an impl that clamps deltas at 0 → test_fewer_redundant_is_negative,
  - an impl that swaps before/after → test_more_format_invalid_is_positive,
  - an impl that returns nonzero for identical inputs → test_identical_reports_zero.
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import (
    DepositQualityReport,
    deposit_quality_delta,
)


def _report(
    *,
    redundant: dict[str, int] | None = None,
    low_evidence: list[str] | None = None,
    format_invalid: list[str] | None = None,
) -> DepositQualityReport:
    return DepositQualityReport(
        redundant=redundant or {},
        low_evidence=low_evidence or [],
        format_invalid=format_invalid or [],
    )


def test_identical_reports_zero() -> None:
    r = _report(redundant={"a": 2}, low_evidence=["x"], format_invalid=["y"])
    d = deposit_quality_delta(r, r)
    assert (d.redundancy_delta, d.low_evidence_delta, d.format_invalid_delta) == (0, 0, 0)


def test_more_format_invalid_is_positive() -> None:
    d = deposit_quality_delta(_report(), _report(format_invalid=["a", "b"]))
    assert d.format_invalid_delta == 2  # worse → positive


def test_fewer_redundant_is_negative() -> None:
    # 2 redundant names → 1 redundant name: a CLAMPED impl reports 0; the signed answer is -1.
    before = _report(redundant={"a": 2, "b": 3})
    after = _report(redundant={"a": 2})
    assert deposit_quality_delta(before, after).redundancy_delta == -1


def test_low_evidence_signed() -> None:
    before = _report(low_evidence=["x", "y", "z"])
    after = _report(low_evidence=["x"])
    assert deposit_quality_delta(before, after).low_evidence_delta == -2
