"""Discriminating tests for silent_except_swallows (item 110, Thread A, 2026-06-08).

`silent_except_swallows(paths)` flags except handlers whose body is EXACTLY one statement:
a bare `pass` or a lone `...` (Ellipsis) — errors caught and dropped silently.

Distinct from item-65's `stealth_bare_excepts` which flags CATCH-ALL WIDTH (catching Exception
or bare except). Item 110 flags silent DROP regardless of catch width.

Each test fails a plausible wrong implementation:
  - one that flags every except, even if it logs/re-raises → test_logging_handler_not_flagged
  - one that misses `...` (Ellipsis) handlers → test_ellipsis_body_flagged
  - one that flags a pass INSIDE a multi-statement body → test_pass_plus_other_not_flagged
  - one that misses narrow except (e.g. `except ValueError: pass`) → test_narrow_except_pass_flagged
  - one that double-flags when item-65's stealth tuple also swallows → test_bare_except_with_pass_flagged
  - one that crashes on a broken file → test_unreadable_file_skipped
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import silent_except_swallows


def _flags(tmp_path: Path, src: str) -> list[tuple[str, str]]:
    (tmp_path / "m.py").write_text(src)
    return silent_except_swallows([tmp_path])


# ---------------------------------------------------------------------------
# T_pass: lone `pass` in except body → flagged as "pass"
# ---------------------------------------------------------------------------


def test_lone_pass_body_flagged(tmp_path: Path) -> None:
    # Fails: an impl that requires bare except (not narrow) to flag.
    src = "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n"
    out = _flags(tmp_path, src)
    assert len(out) == 1
    assert out[0][1] == "pass"


# ---------------------------------------------------------------------------
# T_ellipsis: lone `...` (Ellipsis) in except body → flagged as "ellipsis"
# Fails: an impl that only checks for `ast.Pass`, misses Ellipsis.
# ---------------------------------------------------------------------------


def test_ellipsis_body_flagged(tmp_path: Path) -> None:
    src = "def f():\n    try:\n        pass\n    except KeyError:\n        ...\n"
    out = _flags(tmp_path, src)
    assert len(out) == 1
    assert out[0][1] == "ellipsis"


# ---------------------------------------------------------------------------
# T_logging_not_flagged: logging/re-raise/return handler is NOT a silent swallow
# Fails: an impl that flags ALL except handlers (ignores body content).
# ---------------------------------------------------------------------------


def test_logging_handler_not_flagged(tmp_path: Path) -> None:
    src = (
        "import logging\n"
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError:\n"
        "        logging.warning('swallowed')\n"
    )
    out = _flags(tmp_path, src)
    assert out == []


def test_reraise_handler_not_flagged(tmp_path: Path) -> None:
    src = "def f():\n    try:\n        pass\n    except Exception:\n        raise\n"
    out = _flags(tmp_path, src)
    assert out == []


# ---------------------------------------------------------------------------
# T_pass_plus_other: `pass` PLUS another statement → NOT purely silent (multi-stmt body)
# Fails: an impl that flags any body containing a `pass` regardless of other statements.
# ---------------------------------------------------------------------------


def test_pass_plus_other_not_flagged(tmp_path: Path) -> None:
    src = "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n        x = 1\n"
    out = _flags(tmp_path, src)
    assert out == []


# ---------------------------------------------------------------------------
# T_bare_with_pass: bare `except: pass` is BOTH item-65 (broad) AND item-110 (silent)
# Confirms item 110 is a DISTINCT check — it independently detects the bare+pass combo.
# Fails: an impl that defers to item-65's logic (treating bare-except as out of scope).
# ---------------------------------------------------------------------------


def test_bare_except_with_pass_flagged(tmp_path: Path) -> None:
    src = "def f():\n    try:\n        pass\n    except:\n        pass\n"
    out = _flags(tmp_path, src)
    # Item 110 flags this independently of item-65: it's also a silent swallow.
    assert len(out) == 1 and out[0][1] == "pass"


# ---------------------------------------------------------------------------
# T_clean: no except handlers → empty result
# ---------------------------------------------------------------------------


def test_clean_file_returns_empty(tmp_path: Path) -> None:
    src = "def f():\n    return 1\n"
    assert _flags(tmp_path, src) == []


# ---------------------------------------------------------------------------
# T_unreadable: broken / non-Python file skipped, never crashes
# ---------------------------------------------------------------------------


def test_unreadable_file_skipped(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def f(:\n    pass\n")  # SyntaxError
    result = silent_except_swallows([tmp_path])
    assert isinstance(result, list)  # no exception raised


# ---------------------------------------------------------------------------
# T_multiple: multiple silent handlers in same file → all reported, sorted
# ---------------------------------------------------------------------------


def test_multiple_silent_handlers_all_returned(tmp_path: Path) -> None:
    src = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError:\n"
        "        pass\n"
        "def g():\n"
        "    try:\n"
        "        pass\n"
        "    except KeyError:\n"
        "        ...\n"
    )
    out = _flags(tmp_path, src)
    assert len(out) == 2
    kinds = {k for _, k in out}
    assert "pass" in kinds and "ellipsis" in kinds
