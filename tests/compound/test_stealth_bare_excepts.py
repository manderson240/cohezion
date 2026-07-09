"""Discriminating tests for the stealth bare-except audit (item 65, L359, 2026-06-06).

`stealth_bare_excepts(paths)` flags except handlers that are bare-except in disguise: a truly bare
`except:`, `except Exception:`/`except BaseException:`, OR a tuple CONTAINING `Exception`/`BaseException`
(the L359 stealth case — because Exception is a supertype, `except (ValueError, Exception):` is
semantically `except Exception:`). Sibling-only tuples are NOT flagged.

Each test fails a plausible wrong impl:
  - misses the stealth tuple (only checks bare `Name`) → test_stealth_tuple_flagged,
  - flags a legitimate sibling tuple → test_sibling_tuple_not_flagged,
  - misses truly-bare `except:` → test_bare_except_flagged,
  - flags a narrow single type → test_narrow_except_not_flagged,
  - crashes on a broken file → test_clean_and_badfile.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import stealth_bare_excepts


def _flags(tmp_path: Path, src: str) -> list[tuple[str, str]]:
    (tmp_path / "m.py").write_text(src)
    return stealth_bare_excepts([tmp_path])


def test_bare_except_flagged(tmp_path: Path) -> None:
    out = _flags(tmp_path, "def f():\n    try:\n        pass\n    except:\n        pass\n")
    assert len(out) == 1 and out[0][1] == "bare"


def test_catchall_exception_flagged(tmp_path: Path) -> None:
    out = _flags(tmp_path, "def f():\n    try:\n        pass\n    except Exception:\n        pass\n")
    assert len(out) == 1 and "Exception" in out[0][1]


def test_stealth_tuple_flagged(tmp_path: Path) -> None:
    # except (ValueError, Exception): — Exception in the tuple makes it a stealth bare-except (L359).
    out = _flags(
        tmp_path,
        "def f():\n    try:\n        pass\n    except (ValueError, Exception):\n        pass\n",
    )
    assert len(out) == 1 and out[0][1] == "stealth-tuple"


def test_sibling_tuple_not_flagged(tmp_path: Path) -> None:
    # except (ImportError, KeyError): — siblings, no supertype → legitimate, NOT flagged.
    out = _flags(
        tmp_path,
        "def f():\n    try:\n        pass\n    except (ImportError, KeyError):\n        pass\n",
    )
    assert out == []


def test_narrow_except_not_flagged(tmp_path: Path) -> None:
    out = _flags(tmp_path, "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n")
    assert out == []


def test_clean_and_badfile(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("def f():\n    return 1\n")
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")  # syntax error → skipped, no crash
    assert stealth_bare_excepts([tmp_path]) == []
