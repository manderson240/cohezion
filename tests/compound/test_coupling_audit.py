"""Discriminating tests for the boolean-flag control-coupling audit (item 97, 2026-06-09).

`boolean_flag_params(paths, *, threshold=2)` flags functions with >= threshold parameters whose
DEFAULT is a boolean literal (the "flag argument / secretly does N things" smell). Report-only,
pure (stdlib ast).

Each test fails a plausible wrong impl:
  - counts ANY default (not just bool) → test_zero_default_not_counted (count=0 must not flag),
  - uses `default == False` (so 0 == False counts) → same test (the count=0 trap),
  - counts positional params with no default → test_positional_no_default_not_counted,
  - flags a single flag → test_single_flag_not_flagged,
  - misses keyword-only flag defaults → test_two_bool_defaults_flagged (kwonly_flags).
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.coupling_audit import boolean_flag_params


# two_flags / kwonly_flags: 2 bool defaults each (True AND False both count) -> flagged@2.
# one_flag: 1 bool (verbose) + a non-bool (count=0)            -> 1, not flagged@2.
# trap:     1 bool (enabled) + count=0  -> THE killer: `==False` or "any default" would see 2.
# positional: no defaults -> 0.
_SRC = """
def two_flags(a, verbose=False, dry_run=True):
    return a


def one_flag(a, verbose=False, count=0):
    return a


def trap(a, count=0, enabled=False):
    return a


def positional(a, b, c):
    return a


def kwonly_flags(a, *, strict=True, cache=False):
    return a
"""


def _write(tmp_path: Path) -> Path:
    f = tmp_path / "mod.py"
    f.write_text(_SRC)
    return f


def test_two_bool_defaults_flagged(tmp_path: Path) -> None:
    out = boolean_flag_params([_write(tmp_path)], threshold=2)
    # Both flagged functions have count 2; ties sort by name. kwonly_flags proves kw_defaults count.
    assert out == [("mod.py::kwonly_flags", 2), ("mod.py::two_flags", 2)]


def test_zero_default_not_counted(tmp_path: Path) -> None:
    # DISCRIMINATING: trap(count=0, enabled=False) has ONE bool flag. An impl using `== False`
    # would count 0 as a flag (0 == False), and an "any default" impl would count both -> 2 ->
    # wrongly flagged. isinstance(value, bool) counts only `enabled` -> 1 -> not flagged.
    flagged = {name for name, _ in boolean_flag_params([_write(tmp_path)], threshold=2)}
    assert "mod.py::trap" not in flagged


def test_single_flag_not_flagged(tmp_path: Path) -> None:
    flagged = {name for name, _ in boolean_flag_params([_write(tmp_path)], threshold=2)}
    assert "mod.py::one_flag" not in flagged  # 1 bool default < threshold 2


def test_positional_no_default_not_counted(tmp_path: Path) -> None:
    flagged = {name for name, _ in boolean_flag_params([_write(tmp_path)], threshold=2)}
    assert "mod.py::positional" not in flagged  # no defaults at all


def test_threshold_one_exposes_counts(tmp_path: Path) -> None:
    # At threshold 1 the single-flag functions appear with the RIGHT count (1, not 2).
    counts = dict(boolean_flag_params([_write(tmp_path)], threshold=1))
    assert counts["mod.py::one_flag"] == 1
    assert counts["mod.py::trap"] == 1  # only `enabled`, NOT count=0


def test_clean_and_missing(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("def f(a, b):\n    return a\n")
    assert boolean_flag_params([tmp_path], threshold=2) == []
    assert boolean_flag_params([tmp_path / "nope.py"], threshold=2) == []  # missing → skipped
