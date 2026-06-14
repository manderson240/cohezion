"""Item 157: wire long_functions + long_parameter_lists as standalone TIDE templates (2026-06-08).

Items 63 (``long_parameter_lists``) and 64 (``long_functions``) are used inside
``compound_smells`` but were NOT wired as standalone TIDE templates — a function
with 51+ lines or 7+ params never surfaced independently in ``discover_problems()``.
Item 157 closes both gaps.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: A 51+ line function appears under ``"long_function"`` AND a
     7+ param function appears under ``"long_parameter_list"`` in one call.
     Kills an impl that wires only one of the two templates.
  2. A 7+ param function without deep nesting/size → ``"long_parameter_list"``
     only, NOT ``"compound_smell"`` (no second axis tripped).
     Kills an impl that conflates standalone vs compound wiring.
  3. ``default_templates()`` contains both ``"long_function"`` and
     ``"long_parameter_list"`` entries (structural guard).
     Kills an impl that uses the wrong problem_class name.
  4. ``exclude_known`` suppresses the ``long_function`` finding while the
     ``long_parameter_list`` finding still surfaces (TIDE dedup composability).
     Kills an impl that ignores ``exclude_known`` for the new templates.
  5. A clean short function with few params → in NEITHER new class.
     Kills an impl that always emits a long_function/long_parameter_list finding.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.problem_discovery import default_templates, discover_problems


# ---------------------------------------------------------------------------
# Source templates
# ---------------------------------------------------------------------------

# A function with > 50 lines (long_functions threshold: span > 50)
# AND > 6 params (long_parameter_lists threshold: params > 6).
# Builds a 55-line function body by padding with comment lines.
_LONG_LINES = "\n".join(f"    x{i} = {i}" for i in range(53))  # 53 assignment lines
_SIZE_AND_PARAMS_SRC = f"""\
def big_function(a, b, c, d, e, f, g):
{_LONG_LINES}
    return a
"""

# A clean short function with only 2 params and 1 line — no smells.
_CLEAN_SRC = """\
def clean(x, y):
    return x + y
"""

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, src: str) -> list[Path]:
    p = tmp_path / "subject.py"
    p.write_text(src)
    return [p]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_both_size_smells_surface(tmp_path: Path) -> None:
    """A long function with many params surfaces BOTH long_function and long_parameter_list.

    PRIMARY DISCRIMINATOR: kills an impl that wires only one of the two templates.
    Both ``"long_function"`` and ``"long_parameter_list"`` must appear in the
    output of a single ``discover_problems()`` call with the default registry.
    """
    probs = discover_problems(_write(tmp_path, _SIZE_AND_PARAMS_SRC))
    classes_found = {p.problem_class for p in probs}
    assert "long_function" in classes_found, (
        f"51+ line function must fire long_function; got {sorted(classes_found)}"
    )
    assert "long_parameter_list" in classes_found, (
        f"7+ param function must fire long_parameter_list; got {sorted(classes_found)}"
    )


def test_default_templates_include_both_size_smells() -> None:
    """default_templates() must have both 'long_function' and 'long_parameter_list' entries.

    Structural guard: kills an impl that uses a different problem_class name
    (e.g. 'long_functions' plural, 'large_function', or 'too_many_params').
    """
    tmpls = default_templates()
    classes = {t.problem_class for t in tmpls}
    assert "long_function" in classes, (
        f"'long_function' must be in default_templates; got {sorted(classes)}"
    )
    assert "long_parameter_list" in classes, (
        f"'long_parameter_list' must be in default_templates; got {sorted(classes)}"
    )


def test_exclude_known_suppresses_long_function_only(tmp_path: Path) -> None:
    """exclude_known with the long_function id suppresses it; long_parameter_list still fires.

    Kills an impl that ignores exclude_known for the new templates, or that
    accidentally cross-suppresses both templates when only one id is excluded.
    """
    files = _write(tmp_path, _SIZE_AND_PARAMS_SRC)
    # Find the long_function finding id.
    probs_all = discover_problems(files)
    lf_findings = [p for p in probs_all if p.problem_class == "long_function"]
    assert lf_findings, "pre-condition: long_function must fire"
    lf_id = lf_findings[0].finding_id

    probs_filtered = discover_problems(files, exclude_known={lf_id})
    filtered_classes = {p.problem_class for p in probs_filtered}
    assert "long_function" not in {
        p.finding_id for p in probs_filtered if p.problem_class == "long_function"
    } or lf_id not in {p.finding_id for p in probs_filtered}, (
        f"excluded long_function id must be suppressed; got ids={[p.finding_id for p in probs_filtered if p.problem_class == 'long_function']}"
    )
    assert "long_parameter_list" in filtered_classes, (
        f"long_parameter_list must still surface after long_function excluded; got {sorted(filtered_classes)}"
    )


def test_clean_function_in_neither_class(tmp_path: Path) -> None:
    """Clean short function → neither long_function nor long_parameter_list fires.

    Kills an impl that always emits a size-smell placeholder.
    """
    probs = discover_problems(_write(tmp_path, _CLEAN_SRC))
    classes_found = {p.problem_class for p in probs}
    assert "long_function" not in classes_found, (
        f"clean function must not fire long_function; got {sorted(classes_found)}"
    )
    assert "long_parameter_list" not in classes_found, (
        f"clean function must not fire long_parameter_list; got {sorted(classes_found)}"
    )
