"""Item 124: polyglot_refactor_report — TDD red→green.

``polyglot_refactor_report(repo_root)`` returns a per-language refactor report:
- python     → ruff check (available; ruff is in PATH)
- rust       → cargo clippy (available; cargo is in PATH)
- typescript → tsc --noEmit (ABSENT; tsc not installed → tool_available=False)

Each language section: ``{tool_available: bool, candidates: list[str], drift: int|None}``.

Discriminating tests — each kills a plausible wrong implementation:

  1. All three language keys present             (PRIMARY: kills "partial dict")
  2. Python tool_available=True (ruff in PATH)  (kills "always False")
  3. TypeScript tool_available=False (tsc absent) (kills "crash on missing tool")
  4. Missing language dir → tool_available=False  (kills "fabricate from missing dir")
  5. candidates is always a list                 (kills "None on tool_absent")
  6. drift is None on first run (no baseline)    (kills "fabricate zero drift")
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.polyglot_refactor import polyglot_refactor_report


def test_result_has_all_three_language_keys() -> None:
    """Result dict must have 'python', 'rust', and 'typescript' sections.

    PRIMARY DISCRIMINATOR: kills an impl that returns a partial dict or
    omits a language because its tool is absent.
    """
    result = polyglot_refactor_report(Path("."))
    assert "python" in result, f"'python' key missing; got {list(result.keys())}"
    assert "rust" in result, f"'rust' key missing; got {list(result.keys())}"
    assert "typescript" in result, f"'typescript' key missing; got {list(result.keys())}"


def test_python_section_tool_available_true() -> None:
    """Python section must have tool_available=True because ruff is in PATH.

    Kills an impl that hardcodes tool_available=False for all languages.
    (ruff is installed at /home/mike-anderson/.local/bin/ruff)
    """
    result = polyglot_refactor_report(Path("."))
    assert result["python"].tool_available is True, (
        "Python section must be tool_available=True (ruff is in PATH); "
        f"got {result['python'].tool_available}"
    )


def test_typescript_section_tool_available_false() -> None:
    """TypeScript section must have tool_available=False because tsc is NOT in PATH.

    PRIMARY DISCRIMINATOR: kills an impl that crashes on a missing tool or
    hardcodes tool_available=True regardless of actual PATH state.
    """
    result = polyglot_refactor_report(Path("."))
    assert result["typescript"].tool_available is False, (
        "TypeScript section must be tool_available=False (tsc absent from PATH); "
        f"got {result['typescript'].tool_available}"
    )


def test_missing_python_dir_makes_python_unavailable(tmp_path: Path) -> None:
    """If the Python source directory doesn't exist, tool_available must be False.

    Kills an impl that runs ruff on a non-existent path or fabricates candidates
    from a missing directory.
    """
    result = polyglot_refactor_report(tmp_path)  # tmp_path has no src/cohezion/
    assert result["python"].tool_available is False, (
        "Python section with missing src/ must be tool_available=False; "
        f"got {result['python'].tool_available}"
    )


def test_candidates_is_always_a_list() -> None:
    """candidates must be a list in every section, even when tool is absent.

    Kills an impl that returns None for candidates when the tool is missing
    (downstream code always expects an iterable).
    """
    result = polyglot_refactor_report(Path("."))
    for lang, report in result.items():
        assert isinstance(report.candidates, list), (
            f"candidates must be a list for '{lang}'; got {type(report.candidates).__name__}"
        )


def test_drift_is_none_on_first_run() -> None:
    """drift must be None on the first call (no baseline snapshot yet).

    Kills an impl that fabricates a drift=0 delta without an actual before/after
    comparison (the loop needs two runs to produce a meaningful delta).
    """
    result = polyglot_refactor_report(Path("."))
    for lang, report in result.items():
        assert report.drift is None, (
            f"drift must be None on first run for '{lang}'; got {report.drift!r}"
        )
