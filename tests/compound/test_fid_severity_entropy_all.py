"""Item 716: fid_severity_entropy_all() -- Shannon entropy per fid (vectorized dict).

Fid-axis complement of class_severity_entropy_all (item 715).
fid_severity_entropy_all(problems) -> dict[str, float].
H = -sum(p_i * log2(p_i)) over severity distribution per fid.
Single-severity -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; equal CRITICAL+HIGH -> H=1.0 bit;
     class-outer wrong; count-impl wrong.
  2. Single severity -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_entropy_all


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_equal_split_gives_one_bit_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND entropy = 1.0 for equal split.

    fid 'f1': 1 CRITICAL + 1 HIGH -> H=1.0 bit.
    class-outer wrong (key='A'); count-impl gives 2 wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "HIGH")]
    result = fid_severity_entropy_all(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert abs(result["f1"] - 1.0) < 1e-9, (
        f"Equal CRITICAL+HIGH -> H=1.0 bit; got {result['f1']} (count-impl=2 wrong)"
    )
    assert isinstance(result["f1"], float), f"Must be float; got {type(result['f1'])}"


def test_single_severity_gives_zero() -> None:
    """Single severity -> entropy = 0.0."""
    problems = [_p("f2", "HIGH")] * 4
    result = fid_severity_entropy_all(problems)
    assert result["f2"] == 0.0, f"All HIGH -> H=0.0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_entropy_all([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid entropy computed independently."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "HIGH")]  # f3: equal split -> H=1.0
    problems += [_p("f4", "MEDIUM")] * 5                  # f4: all same -> H=0.0
    result = fid_severity_entropy_all(problems)
    assert abs(result["f3"] - 1.0) < 1e-9, f"f3 equal split -> H=1.0; got {result.get('f3')}"
    assert result["f4"] == 0.0, f"f4 all same -> H=0.0; got {result.get('f4')}"


def test_four_equal_labels_give_two_bits() -> None:
    """4 equal probability labels -> H = 2.0 bits."""
    problems = [
        _p("f5", "CRITICAL"), _p("f5", "HIGH"), _p("f5", "MEDIUM"), _p("f5", "LOW")
    ]
    result = fid_severity_entropy_all(problems)
    assert abs(result["f5"] - 2.0) < 1e-9, f"4 equal labels -> H=2.0 bits; got {result.get('f5')}"
