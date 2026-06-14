"""Discriminating tests for the bare-assert-in-production report (item 148, 2026-06-07).

`production_asserts(paths)` flags `assert` statements in NON-test modules — asserts are STRIPPED
under `python -O`, so an assert used for runtime validation in shipping code is a silent-failure
footgun. Test modules (filename starts with `test_`, or any `tests/` path segment) legitimately
use assert and are excluded. A sibling of `stealth_bare_excepts` (correctness-smell thread).

Each test fails a plausible wrong impl:
  - flags asserts in test files → test_test_file_assert_not_flagged / test_tests_dir_assert_not_flagged,
  - misses module-level asserts (only looks inside functions) → test_module_level_assert_flagged,
  - wrong/missing line number → test_exact_lines_reported,
  - crashes on a broken file → test_clean_and_badfile_skipped.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import production_asserts


def test_assert_in_function_flagged(tmp_path: Path) -> None:
    f = tmp_path / "validate.py"
    f.write_text("def f(x):\n    assert x > 0\n    return x\n")  # assert on line 2
    assert production_asserts([tmp_path]) == [("validate.py", 2)]


def test_module_level_assert_flagged(tmp_path: Path) -> None:
    f = tmp_path / "cfg.py"
    f.write_text("X = 1\nassert X == 1\n")  # module-level assert on line 2 — also stripped under -O
    assert production_asserts([tmp_path]) == [("cfg.py", 2)]


def test_test_file_assert_not_flagged(tmp_path: Path) -> None:
    f = tmp_path / "test_thing.py"  # filename starts with test_ → legitimate assert
    f.write_text("def test_it():\n    assert 1 == 1\n")
    assert production_asserts([tmp_path]) == []


def test_tests_dir_assert_not_flagged(tmp_path: Path) -> None:
    d = tmp_path / "tests"
    d.mkdir()
    (d / "helper.py").write_text("def check():\n    assert True\n")  # under tests/ → excluded
    assert production_asserts([tmp_path]) == []


def test_no_asserts_absent(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text(
        "def f(x):\n    if x < 0:\n        raise ValueError(x)\n    return x\n"
    )
    assert production_asserts([tmp_path]) == []


def test_exact_lines_reported(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "def a(x):\n"
        "    assert x\n"  # line 2
        "def b(y):\n"
        "    assert y is not None\n"  # line 4
    )
    assert production_asserts([tmp_path]) == [("m.py", 2), ("m.py", 4)]


def test_clean_and_badfile_skipped(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def f():\n    return 1\n")  # no assert
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")  # syntax error → skipped, no crash
    assert production_asserts([tmp_path]) == []
