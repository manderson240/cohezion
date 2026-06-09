"""Item 873: fid_severity_rank_z_scores() -- per-problem z-score within fid."""
from __future__ import annotations
import math
from cohezion.compound.problem_discovery import Problem, fid_severity_rank_z_scores


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_key_fid_not_class_primary_discriminator() -> None:
    # fid f1: [INFO(0), HIGH(3), HIGH(3)] -> keyed by fid
    problems = [_p("A", "f1", "INFO"), _p("A", "f1", "HIGH"), _p("A", "f1", "HIGH")]
    result = fid_severity_rank_z_scores(problems)
    assert "f1" in result
    assert "A" not in result  # must NOT be class-keyed
    assert len(result["f1"]) == 3


def test_z_scores_correct_values() -> None:
    # fid f2: [INFO(0), CRITICAL(4)]: mean=2.0, std=2.0 -> z=[-1.0, 1.0]
    problems = [_p("B", "f2", "INFO"), _p("B", "f2", "CRITICAL")]
    result = fid_severity_rank_z_scores(problems)
    assert abs(result["f2"][0] - (-1.0)) < 1e-9
    assert abs(result["f2"][1] - 1.0) < 1e-9


def test_std_zero_gives_all_zeros() -> None:
    problems = [_p("C", "f3", "MEDIUM")] * 5
    result = fid_severity_rank_z_scores(problems)
    assert all(abs(z) < 1e-9 for z in result["f3"])


def test_single_problem_gives_zero() -> None:
    problems = [_p("D", "f4", "HIGH")]
    result = fid_severity_rank_z_scores(problems)
    assert len(result["f4"]) == 1
    assert abs(result["f4"][0]) < 1e-9


def test_different_classes_same_fid_grouped() -> None:
    # different classes but same fid -> z-scores span both
    problems = [_p("X", "f5", "INFO"), _p("Y", "f5", "CRITICAL")]
    result = fid_severity_rank_z_scores(problems)
    assert abs(result["f5"][0] - (-1.0)) < 1e-9
    assert abs(result["f5"][1] - 1.0) < 1e-9


def test_order_matches_input() -> None:
    # First problem is INFO (low rank) -> negative z; second CRITICAL -> positive z
    problems = [_p("A", "f6", "INFO"), _p("A", "f6", "CRITICAL")]
    result = fid_severity_rank_z_scores(problems)
    assert result["f6"][0] < 0
    assert result["f6"][1] > 0


def test_z_scores_sum_to_zero() -> None:
    problems = [_p("A", "f7", s) for s in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = fid_severity_rank_z_scores(problems)
    assert abs(sum(result["f7"])) < 1e-9


def test_multiple_fids_independent() -> None:
    # f8: all HIGH -> zeros; f9: INFO+HIGH -> symmetric non-zero
    problems = ([_p("A", "f8", "HIGH")] * 3 +
                [_p("B", "f9", "INFO"), _p("B", "f9", "HIGH")])
    result = fid_severity_rank_z_scores(problems)
    assert all(abs(z) < 1e-9 for z in result["f8"])
    assert abs(result["f9"][0] + result["f9"][1]) < 1e-9
    assert result["f9"][0] < 0 and result["f9"][1] > 0


def test_empty_returns_empty_dict() -> None:
    assert fid_severity_rank_z_scores([]) == {}


def test_return_type_is_list_of_float() -> None:
    problems = [_p("G", "f10", "HIGH"), _p("G", "f10", "LOW")]
    result = fid_severity_rank_z_scores(problems)
    assert isinstance(result["f10"], list)
    assert all(isinstance(z, float) for z in result["f10"])
