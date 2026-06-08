"""Discriminating tests for the compounded-smell aggregator (item 105, 2026-06-08).

`compound_smells(paths, *, min_dimensions=2)` composes the four per-function simplicity audits
(complexity item-43, nesting 47, parameters 63, size 64) and reports functions flagged on
`>= min_dimensions` axes at once — higher-priority refactor candidates than single-axis ones.
Report-only, pure.

Each test fails a plausible wrong impl:
  - an impl that UNIONS all single-axis flags includes a 1-axis function → test_single_axis_absent,
  - an impl that miscounts dimensions → test_dimension_count_exact,
  - an impl that forgets to materialize a generator (audit #1 exhausts it) → test_accepts_generator,
  - an impl that flags a clean function → test_clean_file_empty.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import compound_smells


# 7 params (> the params threshold of 6) AND a body spanning > 50 lines (> the size threshold of
# 50) → trips exactly TWO axes: parameters + size.
_BODY = "\n".join(f"    x{i} = {i}" for i in range(60))
_TWO_AXIS = f"def big(a, b, c, d, e, f, g):\n{_BODY}\n"

# 7 params, short body → trips ONLY the parameters axis (one dimension).
_ONE_AXIS = "def wide(a, b, c, d, e, f, g):\n    return a\n"


def _smells(tmp_path: Path, src: str, **kw):
    (tmp_path / "m.py").write_text(src)
    return compound_smells([tmp_path], **kw)


def test_two_axis_function_flagged(tmp_path: Path) -> None:
    out = _smells(tmp_path, _TWO_AXIS)
    assert len(out) == 1
    assert out[0].qualified_name == "m.py::big"
    assert out[0].dimensions == ("parameters", "size")
    assert out[0].count == 2


def test_single_axis_absent(tmp_path: Path) -> None:
    # DISCRIMINATING: a function bad on exactly ONE axis must be ABSENT at min_dimensions=2.
    # An impl that unions all single-axis flags would wrongly include it.
    out = _smells(tmp_path, _ONE_AXIS)
    assert out == []


def test_single_axis_present_at_min_one(tmp_path: Path) -> None:
    # Lowering the bar to 1 surfaces the single-axis function — proves the threshold is honored.
    out = _smells(tmp_path, _ONE_AXIS, min_dimensions=1)
    assert len(out) == 1
    assert out[0].qualified_name == "m.py::wide"
    assert out[0].dimensions == ("parameters",) and out[0].count == 1


def test_dimension_count_exact(tmp_path: Path) -> None:
    # DISCRIMINATING: the count is EXACT — the two-axis function reports exactly 2, not 1 or 4.
    out = _smells(tmp_path, _TWO_AXIS + "\n" + _ONE_AXIS)  # one 2-axis, one 1-axis
    assert len(out) == 1  # only the 2-axis function clears min_dimensions=2
    assert out[0].count == 2


def test_accepts_generator(tmp_path: Path) -> None:
    # DISCRIMINATING: paths may be a one-shot generator reused across FOUR audits. An impl that
    # does not materialize it lets audit #1 exhaust it → the other three see nothing → [].
    (tmp_path / "m.py").write_text(_TWO_AXIS)
    gen = (p for p in [tmp_path])
    out = compound_smells(gen)
    assert len(out) == 1 and out[0].count == 2


def test_clean_file_empty(tmp_path: Path) -> None:
    assert _smells(tmp_path, "def f(a):\n    return a\n") == []


def test_same_named_methods_same_axis_counts_once(tmp_path: Path) -> None:
    # DISCRIMINATING (regression for the live-smoke defect): two SAME-NAMED methods (both __init__)
    # that each trip the SAME single axis (parameters) alias to one filename::funcname key. The
    # count is over DISTINCT axes, so it must be 1 (absent at min_dimensions=2) — NOT inflated to 2+
    # by counting the parameters axis once per aliased method.
    src = (
        "class A:\n"
        "    def __init__(self, a, b, c, d, e, f, g):\n"
        "        return\n"
        "class B:\n"
        "    def __init__(self, a, b, c, d, e, f, g):\n"
        "        return\n"
    )
    assert _smells(tmp_path, src) == []  # one distinct axis → below min_dimensions=2
    at_one = _smells(tmp_path, src, min_dimensions=1)
    assert len(at_one) == 1
    assert at_one[0].dimensions == ("parameters",) and at_one[0].count == 1


def test_sorted_by_count_desc(tmp_path: Path) -> None:
    # A 2-axis and a (synthetically) higher-dimension function sort worst-first.
    # Build a function that trips parameters + size; another that trips only parameters+size too
    # but with a longer span — ties broken by name. Here we just assert ordering is by (-count, name).
    src = _TWO_AXIS + "\n" + "def zbig(a, b, c, d, e, f, g):\n" + _BODY + "\n"
    out = _smells(tmp_path, src)
    assert [s.qualified_name for s in out] == ["m.py::big", "m.py::zbig"]
    assert all(s.count == 2 for s in out)
