"""Item 153: wire stealth_bare_excepts + silent_except_swallows into TIDE registry (2026-06-08).

Items 65 and 110 implemented the instruments in ``simplicity_audit.py``.  Item 73 created
the TIDE discovery registry (``default_templates()``).  Item 153 closes the wiring gap:
both instruments must appear in ``default_templates()`` so ``discover_problems()`` surfaces
them without explicit template injection.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.:  ``except Exception: pass`` fires BOTH classes in one call.
     Kills an impl that wires only ONE of the two instruments.
  2. Narrow ``except ValueError: pass`` → ``silent_except_swallow`` only, NOT ``stealth_bare_except``.
     Kills an impl that conflates width-smell with silence-smell.
  3. Catch-all ``except Exception:`` with logging body → ``stealth_bare_except`` only.
     Kills an impl that always pairs the two findings regardless of body.
  4. Clean ``except ValueError: return None`` → neither class surfaces.
     Kills an impl that flags every exception handler.
  5. ``exclude_known`` suppresses exactly ONE of the two findings on a doubly-flagged handler.
     Kills an impl that ignores ``exclude_known`` for the new templates.

All tests use ``templates=None`` (the DEFAULT registry), exercising the real wiring path.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.problem_discovery import default_templates, discover_problems


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, src: str) -> list[Path]:
    """Write ``src`` to a temp .py file and return it as a one-element list."""
    p = tmp_path / "subject.py"
    p.write_text(src)
    return [p]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_catchall_pass_fires_both_classes(tmp_path: Path) -> None:
    """``except Exception: pass`` is BOTH a catch-all (width) AND a silent swallow (depth).

    PRIMARY DISCRIMINATOR: kills an impl that wires only one of the two instruments.
    discover_problems() with the DEFAULT registry must return findings for BOTH
    ``stealth_bare_except`` AND ``silent_except_swallow``.
    """
    src = "def f():\n    try:\n        pass\n    except Exception:\n        pass\n"
    probs = discover_problems(_write(tmp_path, src))
    classes_found = {p.problem_class for p in probs}
    assert "stealth_bare_except" in classes_found, (
        f"stealth_bare_except must fire on 'except Exception: pass'; got {classes_found}"
    )
    assert "silent_except_swallow" in classes_found, (
        f"silent_except_swallow must fire on 'except Exception: pass'; got {classes_found}"
    )


def test_narrow_pass_fires_swallow_only(tmp_path: Path) -> None:
    """``except ValueError: pass`` → silent_except_swallow ONLY (catch is narrow, not catch-all).

    Kills an impl that conflates the two instruments: ``stealth_bare_except`` measures
    CATCH WIDTH (``Exception``/bare), not body silence.  A narrow handler with a silent body
    is a silent swallow but NOT a stealth bare-except.
    """
    src = "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n"
    probs = discover_problems(_write(tmp_path, src))
    classes_found = {p.problem_class for p in probs}
    assert "silent_except_swallow" in classes_found, (
        f"silent_except_swallow must fire on narrow-catch silent body; got {classes_found}"
    )
    assert "stealth_bare_except" not in classes_found, (
        f"stealth_bare_except must NOT fire on narrow 'except ValueError'; got {classes_found}"
    )


def test_catchall_with_logging_fires_bare_only(tmp_path: Path) -> None:
    """``except Exception: log.error(...)`` → stealth_bare_except ONLY.

    Kills an impl that always pairs both findings on any ``except Exception``.
    A handler with a logging statement is NOT purely silent → ``silent_except_swallow``
    must NOT fire; only the catch-width smell applies.
    """
    src = (
        "import logging\n"
        "log = logging.getLogger(__name__)\n"
        "\n"
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        log.error('something went wrong')\n"
    )
    probs = discover_problems(_write(tmp_path, src))
    classes_found = {p.problem_class for p in probs}
    assert "stealth_bare_except" in classes_found, (
        f"stealth_bare_except must fire on 'except Exception'; got {classes_found}"
    )
    assert "silent_except_swallow" not in classes_found, (
        f"silent_except_swallow must NOT fire when body has logging; got {classes_found}"
    )


def test_clean_except_fires_neither(tmp_path: Path) -> None:
    """Narrow catch + non-silent body → neither finding surfaces.

    Kills an impl that flags every exception handler regardless of width or silence.
    ``except ValueError: return None`` is a LEGITIMATE narrow handler with a real action.
    """
    src = "def f():\n    try:\n        pass\n    except ValueError:\n        return None\n"
    probs = discover_problems(_write(tmp_path, src))
    classes_found = {p.problem_class for p in probs}
    assert "stealth_bare_except" not in classes_found, (
        f"stealth_bare_except must NOT fire on narrow except; got {classes_found}"
    )
    assert "silent_except_swallow" not in classes_found, (
        f"silent_except_swallow must NOT fire when body returns; got {classes_found}"
    )


def test_exclude_known_suppresses_one_of_two(tmp_path: Path) -> None:
    """``exclude_known`` with the stealth_bare_except id → only silent_except_swallow surfaces.

    Proves TIDE dedup still works for the new templates: when a finding id is in
    ``exclude_known``, that specific finding is suppressed while the OTHER finding from the
    same handler (different class) still surfaces.  Kills an impl that ignores
    ``exclude_known`` for the new templates.
    """
    src = "def f():\n    try:\n        pass\n    except Exception:\n        pass\n"
    files = _write(tmp_path, src)

    # First run without exclusion — both classes must fire (foundational)
    probs_all = discover_problems(files)
    bare_findings = [p for p in probs_all if p.problem_class == "stealth_bare_except"]
    assert bare_findings, "test pre-condition: stealth_bare_except must fire without exclusion"
    bare_id = bare_findings[0].finding_id

    # Second run with that id excluded — stealth_bare_except suppressed, swallow still fires
    probs_filtered = discover_problems(files, exclude_known={bare_id})
    filtered_classes = {p.problem_class for p in probs_filtered}
    assert "stealth_bare_except" not in filtered_classes, (
        f"stealth_bare_except must be SUPPRESSED by exclude_known; got {filtered_classes}"
    )
    assert "silent_except_swallow" in filtered_classes, (
        f"silent_except_swallow must still surface after stealth id excluded; got {filtered_classes}"
    )


def test_default_templates_include_exception_smells() -> None:
    """default_templates() must include both 'stealth_bare_except' and 'silent_except_swallow'.

    Direct structural check: kills an impl that wires one but forgets the other, or
    accidentally registers under a different problem_class name.
    """
    tmpls = default_templates()
    classes = {t.problem_class for t in tmpls}
    assert "stealth_bare_except" in classes, (
        f"stealth_bare_except must be in default_templates; got {sorted(classes)}"
    )
    assert "silent_except_swallow" in classes, (
        f"silent_except_swallow must be in default_templates; got {sorted(classes)}"
    )
