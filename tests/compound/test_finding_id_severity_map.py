"""Item 311: finding_id_severity_map() — finding_id to severity set map (2026-06-08).

``finding_id_severity_map(problems) -> dict[str, frozenset[str]]``:
For every unique finding_id that has at least one labelled record, returns the
frozenset of severity strings it carries across all records.
Unlabelled records (severity='') are excluded from the frozenset.
Finding_ids with NO labelled records are omitted entirely.
Empty input -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: inner frozenset contains ONLY labelled severities (no '').
     Kills impl including empty-string severity in the frozenset.
  2. Finding_id with BOTH labelled and unlabelled records -> appears with labelled only.
     Kills impl that omits the finding_id just because some records are unlabelled.
  3. Finding_id with ONLY unlabelled records is omitted entirely.
     Kills impl that includes a finding_id with an empty frozenset.
  4. A finding_id appearing with multiple DIFFERENT severities collects all into frozenset.
     Kills impl that keeps only the first/last severity encountered.
  5. Empty input -> {}.
     Kills impl that crashes or returns non-empty on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_severity_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def _pu(cls: str, fid: str) -> Problem:
    """Unlabelled problem."""
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_inner_frozenset_excludes_empty_severity() -> None:
    """Inner frozenset contains ONLY labelled severities, never ''.

    PRIMARY DISCRIMINATOR: kills impl including empty-string in frozenset.
    f001 appears twice with '' (unlabelled) and once with 'HIGH'.
    Result frozenset for f001 must be frozenset({'HIGH'}), not frozenset({'HIGH', ''}).
    """
    problems = [
        _pu("alpha", "f001"),  # unlabelled
        _p("alpha", "f001", "HIGH"),  # labelled HIGH
    ]
    result = finding_id_severity_map(problems)
    assert "f001" in result, "f001 has at least one labelled record -> in result"
    assert result["f001"] == frozenset({"HIGH"}), (
        "f001 frozenset should be {'HIGH'} (no ''); got " + repr(result["f001"])
    )
    assert "" not in result["f001"], "empty-string severity must not be in frozenset; got " + repr(
        result["f001"]
    )


def test_finding_id_with_both_labelled_and_unlabelled_appears() -> None:
    """Finding_id with both labelled AND unlabelled records -> appears with labelled only.

    Kills impl that omits the finding_id when some records are unlabelled.
    f002: 1 unlabelled + 1 CRITICAL -> appears with frozenset({'CRITICAL'}).
    """
    problems = [_pu("beta", "f002"), _p("beta", "f002", "CRITICAL")]
    result = finding_id_severity_map(problems)
    assert "f002" in result, "f002 has labelled record -> must appear; got keys: " + repr(
        list(result.keys())
    )
    assert result["f002"] == frozenset({"CRITICAL"}), (
        "f002 -> frozenset({'CRITICAL'}); got " + repr(result["f002"])
    )


def test_finding_id_with_only_unlabelled_omitted() -> None:
    """Finding_id with ONLY unlabelled records is NOT in result.

    Kills impl that includes a finding_id with an empty frozenset.
    f003: only unlabelled records -> omitted entirely.
    f004: 1 MEDIUM -> included.
    """
    problems = [_pu("gamma", "f003"), _pu("gamma", "f003"), _p("delta_cls", "f004", "MEDIUM")]
    result = finding_id_severity_map(problems)
    assert "f003" not in result, "f003 only unlabelled -> not in result; got keys: " + repr(
        list(result.keys())
    )
    assert "f004" in result, "f004 has MEDIUM record -> in result"


def test_finding_id_with_multiple_severities_collects_all() -> None:
    """Finding_id appearing with multiple severities -> frozenset contains all.

    Kills impl that keeps only the first or last severity.
    f005: appears with HIGH, CRITICAL, LOW -> frozenset({'HIGH','CRITICAL','LOW'}).
    """
    problems = [
        _p("epsilon_cls", "f005", "HIGH"),
        _p("epsilon_cls", "f005", "CRITICAL"),
        _p("zeta_cls", "f005", "LOW"),  # same finding_id, different class
    ]
    result = finding_id_severity_map(problems)
    assert "f005" in result, "f005 has labelled records -> in result"
    assert result["f005"] == frozenset({"HIGH", "CRITICAL", "LOW"}), (
        "f005 -> frozenset({'HIGH','CRITICAL','LOW'}); got " + repr(result["f005"])
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl that crashes or returns non-empty.
    """
    result = finding_id_severity_map([])
    assert result == {}, "empty -> {}; got " + repr(result)
