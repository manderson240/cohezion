"""Discriminating tests for the silent-except-swallow audit (item 110, 2026-06-08).

`silent_except_swallows(paths)` is the DUAL of item-65 `stealth_bare_excepts`: item 65 flags
catch-all WIDTH, this flags silent DROP. It flags except handlers whose body is EXACTLY a lone
`pass` or a lone `...` (Ellipsis) — an error caught and discarded with no log/re-raise/handling.
Report-only, pure (stdlib ast).

Each test fails a plausible wrong impl:
  - an impl that requires a bare/catch-all type (item-65 logic) misses a NARROW silent swallow
    → test_narrow_except_pass_flagged,
  - an impl that flags any body CONTAINING pass flags "pass plus other statements"
    → test_pass_plus_other_not_flagged,
  - an impl that flags any single-Expr-Constant body flags a docstring → test_docstring_body_not_flagged,
  - an impl that misses `...` → test_ellipsis_body_flagged,
  - an impl that flags a handled except → test_logged_except_not_flagged.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import silent_except_swallows


def _flags(tmp_path: Path, src: str) -> list[tuple[str, str]]:
    (tmp_path / "m.py").write_text(src)
    return silent_except_swallows([tmp_path])


def test_bare_pass_flagged(tmp_path: Path) -> None:
    out = _flags(tmp_path, "def f():\n    try:\n        g()\n    except:\n        pass\n")
    assert len(out) == 1 and out[0][1] == "pass"


def test_narrow_except_pass_flagged(tmp_path: Path) -> None:
    # DISCRIMINATING: a NARROW `except ValueError: pass` is still a silent swallow. An impl reusing
    # item-65's catch-all-width logic would NOT flag it (ValueError is narrow).
    out = _flags(
        tmp_path, "def f():\n    try:\n        g()\n    except ValueError:\n        pass\n"
    )
    assert len(out) == 1 and out[0][1] == "pass"


def test_ellipsis_body_flagged(tmp_path: Path) -> None:
    # DISCRIMINATING: a lone `...` body is also a silent swallow (an impl checking only Pass misses it).
    out = _flags(tmp_path, "def f():\n    try:\n        g()\n    except KeyError:\n        ...\n")
    assert len(out) == 1 and out[0][1] == "ellipsis"


def test_pass_plus_other_not_flagged(tmp_path: Path) -> None:
    # DISCRIMINATING: `pass` PLUS another statement is NOT purely silent. An impl that flags any
    # body CONTAINING a pass would wrongly flag this.
    src = "def f():\n    try:\n        g()\n    except ValueError:\n        pass\n        log()\n"
    assert _flags(tmp_path, src) == []


def test_logged_except_not_flagged(tmp_path: Path) -> None:
    src = "def f():\n    try:\n        g()\n    except ValueError as e:\n        log(e)\n"
    assert _flags(tmp_path, src) == []


def test_reraise_not_flagged(tmp_path: Path) -> None:
    src = "def f():\n    try:\n        g()\n    except ValueError:\n        raise\n"
    assert _flags(tmp_path, src) == []


def test_docstring_body_not_flagged(tmp_path: Path) -> None:
    # DISCRIMINATING: a string-Constant body (e.g. a comment-as-string) is a single Expr/Constant
    # like `...`, but its value is NOT Ellipsis → must NOT be flagged. An impl that flags any
    # single-Expr-Constant body would wrongly flag this.
    src = (
        'def f():\n    try:\n        g()\n    except ValueError:\n        "intentionally ignored"\n'
    )
    assert _flags(tmp_path, src) == []


def test_clean_file_empty(tmp_path: Path) -> None:
    assert _flags(tmp_path, "def f():\n    return 1\n") == []


def test_badfile_does_not_crash(tmp_path: Path) -> None:
    # A non-parseable file is skipped, never crashes the audit.
    (tmp_path / "bad.py").write_text("def (:\n  not python\n")
    (tmp_path / "ok.py").write_text("def f():\n    try:\n        g()\n    except:\n        pass\n")
    out = silent_except_swallows([tmp_path])
    assert len(out) == 1 and out[0][1] == "pass"
