"""Item 833: severity_profile() -- count of each severity level across all problems."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, severity_profile


def _p(sev: str) -> Problem:
    return Problem(problem_class="A", finding_id="f1", severity=sev)


def test_severity_string_keys_not_rank_primary_discriminator() -> None:
    # 3 HIGH + 2 CRITICAL -> {"HIGH":3,"CRITICAL":2}; rank-keyed {3:3,4:2} wrong
    problems = [_p("HIGH")] * 3 + [_p("CRITICAL")] * 2
    result = severity_profile(problems)
    assert result.get("HIGH") == 3 and result.get("CRITICAL") == 2
    assert 3 not in result and 4 not in result


def test_absent_severities_not_in_result() -> None:
    problems = [_p("HIGH"), _p("HIGH")]
    result = severity_profile(problems)
    assert "CRITICAL" not in result and "LOW" not in result


def test_all_severities_present() -> None:
    problems = [_p("INFO"), _p("LOW"), _p("MEDIUM"), _p("HIGH"), _p("CRITICAL")]
    result = severity_profile(problems)
    assert all(result.get(s) == 1 for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"])


def test_empty_returns_empty_dict() -> None:
    assert severity_profile([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("HIGH"), _p("HIGH")]
    result = severity_profile(problems)
    assert isinstance(result["HIGH"], int)
