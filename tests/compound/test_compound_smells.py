"""Discriminating tests for compound_smells (item 105, 2026-06-08).

``compound_smells(paths, *, min_dimensions=2)`` returns functions flagged on ≥ min_dimensions
of {complexity, nesting, params, size} at their DEFAULT thresholds:
  - complexity_outliers: CC > 15
  - nesting_outliers:    depth > 5
  - long_parameter_lists: params > 6
  - long_functions:      span > 50 lines

Key discriminating tests:

  1. A function tripping ≥2 axes → in the report (happy path).
  2. A function on EXACTLY 1 axis → ABSENT at min_dimensions=2 — kills the naive
     "union all per-axis flags" implementation.
  3. dimension_count is EXACT (not 1 or 3 when it should be 2) — kills over/under-counting.
  4. clean file → [].
  5. min_dimensions=1 exposes single-axis functions — kills an impl that ignores the param.
  6. mixed file: only the multi-axis function appears.
  7. dimensions frozenset is accurate — contains exactly the right axis names.
  8. All-four-axes function has dimension_count==4 and all four dimension names.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import compound_smells


# ---------------------------------------------------------------------------
# Synthetic Python source fixtures
# ---------------------------------------------------------------------------

# Trips EXACTLY 2 axes: complexity (CC=17 > 15) + params (7 > 6).
# Nesting depth = 1 (each `if` is flat, NOT >5).  Size = 17 lines (NOT >50).
_TWO_AXIS_SRC = """\
def two_axis_func(a, b, c, d, e, f, g):
    if a: pass
    if b: pass
    if c: pass
    if d: pass
    if e: pass
    if f: pass
    if g: pass
    if a: pass
    if b: pass
    if c: pass
    if d: pass
    if e: pass
    if f: pass
    if g: pass
    if a: pass
    if b: pass
"""

# Trips EXACTLY 1 axis: nesting (depth=6 > 5).
# CC = 7 (NOT >15).  params = 1 (NOT >6).  size ≈ 8 lines (NOT >50).
_ONE_AXIS_SRC = """\
def one_axis_func(x):
    if x:
        if x:
            if x:
                if x:
                    if x:
                        if x:
                            pass
"""

# Trips ALL 4 axes: complexity (CC=16>15) + nesting (depth=6>5) + params (7>6) + size (52>50).
_FOUR_AXIS_SRC = """\
def four_axis_func(a, b, c, d, e, f, g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            pass
    if a: pass
    if b: pass
    if c: pass
    if d: pass
    if e: pass
    if f: pass
    if g: pass
    if a: pass
    if b: pass
    x = 1
    x = 2
    x = 3
    x = 4
    x = 5
    x = 6
    x = 7
    x = 8
    x = 9
    x = 10
    x = 11
    x = 12
    x = 13
    x = 14
    x = 15
    x = 16
    x = 17
    x = 18
    x = 19
    x = 20
    x = 21
    x = 22
    x = 23
    x = 24
    x = 25
    x = 26
    x = 27
    x = 28
    x = 29
    x = 30
    x = 31
    x = 32
    x = 33
    x = 34
    x = 35
"""

# A completely clean function — trips zero axes.
_CLEAN_SRC = """\
def clean_func(a, b):
    return a + b
"""


def _write(tmp_path: Path, name: str, src: str) -> Path:
    p = tmp_path / name
    p.write_text(src, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_two_axis_function_flagged(tmp_path: Path) -> None:
    """A function tripping complexity + params (2 axes) → appears in the report.

    Fails: an impl that returns [] for any input.
    """
    path = _write(tmp_path, "src.py", _TWO_AXIS_SRC)
    results = compound_smells([path])
    names = [r.qualified_name for r in results]
    assert any("two_axis_func" in n for n in names), (
        f"two_axis_func (CC=17>15, params=7>6) must appear; got {names}"
    )


def test_single_axis_absent_at_min_2(tmp_path: Path) -> None:
    """A function on EXACTLY 1 axis → ABSENT at min_dimensions=2.

    PRIMARY discriminator: kills the naive 'union all per-axis flags' implementation.
    one_axis_func trips only nesting (depth=6>5), NOT complexity (CC=7≤15) or params (1≤6) or size.
    """
    path = _write(tmp_path, "src.py", _ONE_AXIS_SRC)
    results = compound_smells([path])  # default min_dimensions=2
    names = [r.qualified_name for r in results]
    assert not any("one_axis_func" in n for n in names), (
        f"one_axis_func (1 axis only: nesting) must NOT appear at min_dimensions=2; got {names}"
    )


def test_dimension_count_exact(tmp_path: Path) -> None:
    """dimension_count is EXACTLY 2 for a 2-axis function — kills an over/under-counting impl."""
    path = _write(tmp_path, "src.py", _TWO_AXIS_SRC)
    results = compound_smells([path])
    assert len(results) == 1, f"expected exactly 1 result; got {results}"
    assert results[0].dimension_count == 2, (
        f"two_axis_func trips exactly 2 axes; dimension_count must be 2, "
        f"got {results[0].dimension_count}"
    )


def test_four_axis_dimension_count(tmp_path: Path) -> None:
    """A function tripping all 4 axes has dimension_count==4.

    Kills an impl that caps dimension_count at 2 or returns the wrong count.
    """
    path = _write(tmp_path, "src.py", _FOUR_AXIS_SRC)
    results = compound_smells([path])
    assert len(results) == 1, f"expected 1 result for four_axis_func; got {results}"
    assert results[0].dimension_count == 4, (
        f"four_axis_func trips all 4 axes; dimension_count must be 4, "
        f"got {results[0].dimension_count}"
    )


def test_four_axis_dimensions_set(tmp_path: Path) -> None:
    """dimensions frozenset contains all four axis names for a 4-axis function.

    Kills an impl that only tracks a subset of axes.
    """
    path = _write(tmp_path, "src.py", _FOUR_AXIS_SRC)
    results = compound_smells([path])
    assert len(results) == 1
    assert results[0].dimensions == frozenset({"complexity", "nesting", "params", "size"}), (
        f"Expected all 4 dimension names; got {results[0].dimensions}"
    )


def test_clean_file_empty(tmp_path: Path) -> None:
    """A file with no smell outliers → empty report.

    Fails: an impl that always returns at least one result.
    """
    path = _write(tmp_path, "src.py", _CLEAN_SRC)
    results = compound_smells([path])
    assert results == [], f"clean function must not appear in compound_smells; got {results}"


def test_min_dimensions_one_exposes_single_axis(tmp_path: Path) -> None:
    """min_dimensions=1 includes the 1-axis function — kills an impl that ignores the parameter."""
    path = _write(tmp_path, "src.py", _ONE_AXIS_SRC)
    results = compound_smells([path], min_dimensions=1)
    names = [r.qualified_name for r in results]
    assert any("one_axis_func" in n for n in names), (
        f"At min_dimensions=1, one_axis_func (nesting only) must appear; got {names}"
    )


def test_mixed_file_only_multi_axis_appears(tmp_path: Path) -> None:
    """File with both 1-axis and 2-axis → only 2-axis in report at default min_dimensions=2.

    Kills an impl that unions all single-axis flags and includes both functions.
    """
    src = _TWO_AXIS_SRC + "\n" + _ONE_AXIS_SRC
    path = _write(tmp_path, "src.py", src)
    results = compound_smells([path])
    names = [r.qualified_name for r in results]
    assert any("two_axis_func" in n for n in names), f"two_axis_func must appear; got {names}"
    assert not any("one_axis_func" in n for n in names), (
        f"one_axis_func (1 axis) must NOT appear at min_dimensions=2; got {names}"
    )


def test_two_axis_dimensions_accurate(tmp_path: Path) -> None:
    """dimensions frozenset contains exactly 'complexity' and 'params' for the 2-axis function.

    Kills an impl that always returns all four names or always returns an empty frozenset.
    two_axis_func: CC=17 (complexity ✓), depth=1 (nesting ✗), params=7 (params ✓), size=17 (✗).
    """
    path = _write(tmp_path, "src.py", _TWO_AXIS_SRC)
    results = compound_smells([path])
    assert len(results) == 1
    dims = results[0].dimensions
    assert "complexity" in dims, f"complexity must be in dimensions; got {dims}"
    assert "params" in dims, f"params must be in dimensions; got {dims}"
    assert "nesting" not in dims, f"nesting must NOT be in dimensions (depth=1≤5); got {dims}"
    assert "size" not in dims, f"size must NOT be in dimensions (17 lines≤50); got {dims}"
