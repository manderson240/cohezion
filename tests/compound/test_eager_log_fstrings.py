"""Discriminating tests for the eager-log-fstring report (item 150, 2026-06-07).

`eager_log_fstrings(paths)` flags logger method calls whose FIRST positional arg is an
interpolating f-string — the string is formatted eagerly by the caller even when the level
is disabled.  The lazy form (`log.info("%s", x)`) defers to the handler.

Each test fails a plausible wrong impl:
  - flags every JoinedStr (not just in logger methods) → test_non_logger_fstring_not_flagged,
  - flags %-style calls → test_percent_style_not_flagged,
  - misses a method like `log.error` → test_all_named_methods_flagged,
  - flags constant-only f-strings (no interpolation) → test_constant_fstring_not_flagged,
  - crashes on a bad file → test_bad_syntax_skipped,
  - wrong line number → test_exact_lineno_reported,
  - counts all second-arg positions (should only look at FIRST positional arg) → implicit in
    test_percent_style_not_flagged (second arg is the value, first is the template).
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import eager_log_fstrings


def test_interpolating_fstring_flagged(tmp_path: Path) -> None:
    """The basic case: `log.info(f"x={x}")` must be flagged."""
    (tmp_path / "mod.py").write_text(
        "import logging\n"
        "log = logging.getLogger(__name__)\n"
        "\n"
        "def f(x):\n"
        "    log.info(f'x={x}')\n"  # line 5
    )
    result = eager_log_fstrings([tmp_path])
    assert result == [("mod.py", 5)], result


def test_percent_style_not_flagged(tmp_path: Path) -> None:
    """Lazy %-style arg is the recommended form — must NOT be flagged."""
    (tmp_path / "lazy.py").write_text(
        "import logging\n"
        "log = logging.getLogger(__name__)\n"
        "\n"
        "def f(x):\n"
        "    log.info('x=%s', x)\n"  # no f-string → lazy, not a smell
    )
    assert eager_log_fstrings([tmp_path]) == []


def test_non_logger_fstring_not_flagged(tmp_path: Path) -> None:
    """print(f"...") — method not in _LOG_METHODS → must NOT be flagged."""
    (tmp_path / "printer.py").write_text(
        "def f(x):\n    print(f'value={x}')\n"  # print is not a logger method
    )
    assert eager_log_fstrings([tmp_path]) == []


def test_constant_fstring_not_flagged(tmp_path: Path) -> None:
    """A constant-only f-string (no FormattedValue) has zero formatting cost — NOT a smell."""
    (tmp_path / "const.py").write_text(
        "import logging\n"
        "log = logging.getLogger(__name__)\n"
        "\n"
        "def f():\n"
        "    log.info(f'static message')\n"  # JoinedStr with only Constant children
    )
    assert eager_log_fstrings([tmp_path]) == []


def test_all_named_methods_flagged(tmp_path: Path) -> None:
    """debug/info/warning/error/critical/exception — all in the logger method set."""
    src = (
        "import logging\n"
        "log = logging.getLogger(__name__)\n"
        "\n"
        "def f(x):\n"
        "    log.debug(f'd={x}')\n"  # line 5
        "    log.info(f'i={x}')\n"  # line 6
        "    log.warning(f'w={x}')\n"  # line 7
        "    log.error(f'e={x}')\n"  # line 8
        "    log.critical(f'c={x}')\n"  # line 9
        "    log.exception(f'ex={x}')\n"  # line 10
    )
    (tmp_path / "methods.py").write_text(src)
    result = eager_log_fstrings([tmp_path])
    lines = [lineno for _, lineno in result]
    assert lines == [5, 6, 7, 8, 9, 10], result


def test_exact_lineno_reported(tmp_path: Path) -> None:
    """Line numbers must be exact — not off-by-one."""
    (tmp_path / "two.py").write_text(
        "import logging\n"  # 1
        "log = logging.getLogger(__name__)\n"  # 2
        "\n"  # 3
        "def f(a, b):\n"  # 4
        "    log.info(f'a={a}')\n"  # 5  ← first smell
        "    do_something(a)\n"  # 6
        "    log.warning(f'b={b}')\n"  # 7  ← second smell
    )
    result = eager_log_fstrings([tmp_path])
    assert result == [("two.py", 5), ("two.py", 7)]


def test_clean_file_returns_empty(tmp_path: Path) -> None:
    """No logger calls at all → []."""
    (tmp_path / "clean.py").write_text("def f(x):\n    return x * 2\n")
    assert eager_log_fstrings([tmp_path]) == []


def test_bad_syntax_skipped_no_crash(tmp_path: Path) -> None:
    """A file with invalid Python must be skipped gracefully — no exception raised."""
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")
    (tmp_path / "ok.py").write_text(
        "import logging\n"
        "log = logging.getLogger(__name__)\n"
        "def g(y):\n"
        "    log.info(f'y={y}')\n"  # line 4
    )
    result = eager_log_fstrings([tmp_path])
    assert result == [("ok.py", 4)]
