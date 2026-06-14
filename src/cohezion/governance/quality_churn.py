"""Item 128: Deposit-quality churn (name-level) — report-only (2026-06-08).

``deposit_quality_churn(before, after)`` returns the name-level delta across two
``DepositQualityReport``s — WHICH neurons entered/left each problem set, not just
how many (item-74's count-level delta).

For each problem class (redundant, low_evidence, format_invalid):
  - ``newly``: names that appeared in ``after`` but were NOT in ``before``
    (new problem since last scan — which neuron to fix next).
  - ``resolved``: names that were in ``before`` but are NOT in ``after``
    (fixed since last scan — confirms the fix landed).
  - a name in BOTH → in NEITHER (still open, tracked as stable).

Mirrors item-81 ``human_gate_delta`` (resolved/introduced by NAME) +
item-127 ``discovered_problem_delta`` (same set-difference pattern).

Report-only — tells the loop exactly which neuron to address.  Pure (no I/O,
no writes, no graph).
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.governance.neuron_quality import DepositQualityReport


@dataclass(frozen=True)
class NameChurn:
    """Name-level churn for one problem class.

    Attributes:
        newly:    Names that entered the problem set since the last scan.
        resolved: Names that left the problem set since the last scan.
    """

    newly: list[str]
    resolved: list[str]


@dataclass(frozen=True)
class QualityChurnReport:
    """Name-level churn across all three deposit-quality dimensions.

    Attributes:
        redundant:      Churn in the redundant-name set.
        low_evidence:   Churn in the below-floor-reward set.
        format_invalid: Churn in the malformed-neuron set.
    """

    redundant: NameChurn
    low_evidence: NameChurn
    format_invalid: NameChurn


def _name_churn(before_names: set[str], after_names: set[str]) -> NameChurn:
    """Compute name-level churn between two name sets (pure helper)."""
    return NameChurn(
        newly=sorted(after_names - before_names),
        resolved=sorted(before_names - after_names),
    )


def deposit_quality_churn(
    before: DepositQualityReport,
    after: DepositQualityReport,
) -> QualityChurnReport:
    """Return the name-level delta between two ``DepositQualityReport``s.

    Args:
        before: Report from the earlier scan (the baseline).
        after:  Report from the more recent scan (current state).

    Returns:
        ``QualityChurnReport`` with ``newly``/``resolved`` name lists for each
        of the three problem classes.  Names in both → neither list.

    Pure — no I/O, no writes.  Report-only.
    """
    return QualityChurnReport(
        redundant=_name_churn(
            set(before.redundant.keys()),
            set(after.redundant.keys()),
        ),
        low_evidence=_name_churn(
            set(before.low_evidence),
            set(after.low_evidence),
        ),
        format_invalid=_name_churn(
            set(before.format_invalid),
            set(after.format_invalid),
        ),
    )
