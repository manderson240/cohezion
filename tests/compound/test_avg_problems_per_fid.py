"""Item 841: avg_problems_per_fid() -- global average problems per distinct fid.

avg_problems_per_fid(problems) -> float.
= len(problems) / count_distinct_fids. Empty -> 0.0. Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: total/distinct_fids (kills class-density version and total=6);
     6 problems across 3 fids -> 2.0; class-density differs.
  2. Single fid -> density = total (all problems same fid).
  3. One per fid -> 1.0.
  4. Empty -> 0.0.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, avg_problems_per_fid


def _p(fid: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity="HIGH")


def test_fid_density_not_class_density_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; 6 problems / 3 distinct fids = 2.0;
    class-density (6/1=6.0) differs because all are class 'A'."""
    problems = [_p("f1")] * 3 + [_p("f2")] * 2 + [_p("f3")] * 1
    got = avg_problems_per_fid(problems)
    assert math.isclose(got, 2.0, abs_tol=1e-9), f"expected 2.0; got {got}"
    assert not math.isclose(got, 6.0, abs_tol=1e-6), "Must not be class density"
    assert isinstance(got, float)


def test_single_fid_density_equals_count() -> None:
    """All problems with one fid -> density = total."""
    problems = [_p("f1")] * 4
    got = avg_problems_per_fid(problems)
    assert math.isclose(got, 4.0, abs_tol=1e-9)


def test_one_per_fid_gives_one() -> None:
    """One problem per distinct fid -> density = 1.0."""
    problems = [_p("f1"), _p("f2"), _p("f3")]
    got = avg_problems_per_fid(problems)
    assert math.isclose(got, 1.0, abs_tol=1e-9)


def test_empty_returns_zero() -> None:
    """Empty -> 0.0."""
    assert avg_problems_per_fid([]) == 0.0


def test_return_type_is_float() -> None:
    """Result must be float."""
    problems = [_p("f1"), _p("f2")]
    assert isinstance(avg_problems_per_fid(problems), float)
