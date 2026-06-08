"""Item 156: wire compound_smells into TIDE registry (2026-06-08).

Item 105 implemented ``compound_smells(paths, *, min_dimensions=2)`` in
``simplicity_audit.py``.  Item 73 created the TIDE discovery registry
(``default_templates()``).  Item 156 closes the wiring gap: ``compound_smells``
must appear in ``default_templates()`` so ``discover_problems()`` surfaces
multi-axis worst-offenders without explicit template injection.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: a function tripping complexity + nesting (2 axes) appears
     under ``"compound_smell"`` in ``discover_problems()`` (default registry).
     Kills an impl that wires ``compound_smells`` but under the wrong key or
     problem_class name.
  2. A single-axis function (params only, no deep nesting) does NOT appear.
     Kills an impl that lowers the effective ``min_dimensions`` to 1 when wiring.
  3. ``default_templates()`` contains a ``"compound_smell"`` entry.
     Structural guard: kills an impl that adds the template under a different
     problem_class name (e.g. ``"compound_smells"`` plural).
  4. ``exclude_known`` with the compound_smell id suppresses it.
     Kills an impl that ignores ``exclude_known`` for the new template.
  5. clean source → ``"compound_smell"`` class absent from output.
     Kills an impl that always emits a compound_smell finding.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.problem_discovery import default_templates, discover_problems


# ---------------------------------------------------------------------------
# Source templates
# ---------------------------------------------------------------------------

# A function tripping BOTH long_parameter_lists (7 > 6) AND nesting_outliers (depth 6 > 5).
_COMPOUND_SRC = """\
def compound_function(a, b, c, d, e, f, g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            pass
"""

# A function tripping ONLY long_parameter_lists (7 params) — no deep nesting.
_SINGLE_AXIS_SRC = """\
def single_axis_function(a, b, c, d, e, f, g):
    return a
"""

# A clean function — no smells.
_CLEAN_SRC = """\
def clean_function(x, y):
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


def test_two_axis_function_appears_as_compound_smell(tmp_path: Path) -> None:
    """Function tripping params + nesting (2 axes) → 'compound_smell' finding.

    PRIMARY DISCRIMINATOR: kills an impl that does not wire compound_smells,
    or wires it under the wrong problem_class name.
    """
    probs = discover_problems(_write(tmp_path, _COMPOUND_SRC))
    classes_found = {p.problem_class for p in probs}
    assert "compound_smell" in classes_found, (
        f"2-axis function must fire compound_smell; got classes={sorted(classes_found)}"
    )


def test_single_axis_function_does_not_appear(tmp_path: Path) -> None:
    """Function tripping only one axis (params, no deep nesting) → NOT compound_smell.

    Kills an impl that lowers the effective min_dimensions to 1 when wiring
    (e.g. passes min_dimensions=1 to compound_smells).
    """
    probs = discover_problems(_write(tmp_path, _SINGLE_AXIS_SRC))
    classes_found = {p.problem_class for p in probs}
    assert "compound_smell" not in classes_found, (
        f"single-axis function must NOT fire compound_smell; got classes={sorted(classes_found)}"
    )


def test_default_templates_include_compound_smell() -> None:
    """default_templates() must contain a ProblemTemplate with problem_class='compound_smell'.

    Structural guard: kills an impl that registers the template under a different
    name (e.g. 'compound_smells' plural or 'multi_axis_smell').
    """
    tmpls = default_templates()
    classes = {t.problem_class for t in tmpls}
    assert "compound_smell" in classes, (
        f"'compound_smell' must be in default_templates; got {sorted(classes)}"
    )


def test_exclude_known_suppresses_compound_smell(tmp_path: Path) -> None:
    """exclude_known with the compound_smell finding id suppresses it.

    Kills an impl that ignores exclude_known for the new template (i.e. the
    template's key lambda doesn't compose with the TIDE dedup correctly).
    """
    files = _write(tmp_path, _COMPOUND_SRC)
    # First run — find the compound_smell finding id.
    probs_all = discover_problems(files)
    cs_findings = [p for p in probs_all if p.problem_class == "compound_smell"]
    assert cs_findings, "pre-condition: compound_smell must fire without exclusion"
    cs_id = cs_findings[0].finding_id

    # Second run with that id excluded — compound_smell must be suppressed.
    probs_filtered = discover_problems(files, exclude_known={cs_id})
    # The specific id should be gone (even if the same function fires another class).
    filtered_cs_ids = {p.finding_id for p in probs_filtered if p.problem_class == "compound_smell"}
    assert cs_id not in filtered_cs_ids, (
        f"excluded finding_id must be suppressed; found {filtered_cs_ids}"
    )


def test_clean_source_no_compound_smell(tmp_path: Path) -> None:
    """Clean source → 'compound_smell' class absent from discover_problems() output.

    Kills an impl that always emits a compound_smell placeholder finding.
    """
    probs = discover_problems(_write(tmp_path, _CLEAN_SRC))
    classes_found = {p.problem_class for p in probs}
    assert "compound_smell" not in classes_found, (
        f"clean source must not produce compound_smell; got {sorted(classes_found)}"
    )
