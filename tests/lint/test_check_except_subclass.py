"""Unit tests for scripts/lint/check_except_subclass.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LINTER = REPO_ROOT / "scripts" / "lint" / "check_except_subclass.py"


def _run(target: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(LINTER), str(target)],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    return result.returncode, result.stderr


def test_linter_exists():
    assert LINTER.exists(), f"linter script not found at {LINTER}"


def test_clean_file_passes(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text(
        """
def foo():
    try:
        x = 1
    except (ValueError, KeyError) as e:
        print(e)
"""
    )
    code, stderr = _run(f)
    assert code == 0, f"unexpected violations on clean file: {stderr}"


def test_import_error_exception_tuple_flagged(tmp_path):
    f = tmp_path / "dirty.py"
    f.write_text(
        """
def foo():
    try:
        x = 1
    except (ImportError, Exception) as e:
        print(e)
"""
    )
    code, stderr = _run(f)
    assert code == 1, "linter should flag (ImportError, Exception)"
    assert "ImportError is a subclass of Exception" in stderr


def test_nested_subclass_flagged(tmp_path):
    """FileNotFoundError inherits from OSError."""
    f = tmp_path / "dirty.py"
    f.write_text(
        """
def foo():
    try:
        x = 1
    except (FileNotFoundError, OSError) as e:
        print(e)
"""
    )
    code, stderr = _run(f)
    assert code == 1
    assert "FileNotFoundError is a subclass of OSError" in stderr


def test_good_sibling_tuple_passes(tmp_path):
    """(ImportError, AttributeError, KeyError) — none is a subclass of another."""
    f = tmp_path / "good.py"
    f.write_text(
        """
def foo():
    try:
        x = 1
    except (ImportError, AttributeError, KeyError) as e:
        print(e)
"""
    )
    code, stderr = _run(f)
    assert code == 0, f"sibling tuple wrongly flagged: {stderr}"


def test_custom_exceptions_not_flagged(tmp_path):
    """The linter only resolves builtins — custom classes are silently ignored."""
    f = tmp_path / "custom.py"
    f.write_text(
        """
class DomainError(Exception):
    pass


def foo():
    try:
        x = 1
    except (DomainError, Exception) as e:  # we can't resolve DomainError
        print(e)
"""
    )
    code, stderr = _run(f)
    # Custom classes aren't in builtins; linter ignores them. This is by design.
    assert code == 0, f"custom class wrongly flagged: {stderr}"


def test_usage_message(tmp_path):
    result = subprocess.run(
        [sys.executable, str(LINTER)],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    assert result.returncode == 2


def test_nonexistent_path_error(tmp_path):
    code, stderr = _run(tmp_path / "does-not-exist.py")
    assert code == 2
    assert "path not found" in stderr


@pytest.mark.parametrize(
    "pair,flagged",
    [
        (("TimeoutError", "Exception"), True),
        (("KeyError", "LookupError"), True),  # KeyError is LookupError
        (("IndexError", "LookupError"), True),  # IndexError is LookupError
        (("ValueError", "TypeError"), False),  # siblings
        (("RuntimeError", "StopIteration"), False),  # siblings
    ],
)
def test_specific_builtins(tmp_path, pair, flagged):
    a, b = pair
    f = tmp_path / "t.py"
    f.write_text(
        f"""
def foo():
    try:
        x = 1
    except ({a}, {b}) as e:
        print(e)
"""
    )
    code, _stderr = _run(f)
    assert code == (1 if flagged else 0)
