"""Item 291: dominant_severity_per_class() — most common severity label per class (2026-06-08).

``dominant_severity_per_class(problems: list[Problem]) -> dict[str, str]``:
Returns {cls: dominant_severity} for every class with at least one labelled problem.
Classes with only unlabelled problems (severity="") are OMITTED.
Ties broken by lexicographically smallest severity string.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: classes with only unlabelled problems omitted from result.
     Kills impl that includes classes with severity="" problems as dominant.
  2. Tie-break selects lexicographically SMALLEST severity string.
     Kills impl using largest-first or insertion-order tie-break.
  3. Empty input -> {}.
     Kills impl raising on empty.
  4. Class with one labelled problem -> that severity is dominant.
     Kills impl that requires >=2 labelled problems.
  5. Return type is dict[str, str] — both keys and values are strings.
     Kills impl returning Problem objects or counts.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_severity_per_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unlabelled_only_class_omitted() -> None:
    """Classes with only unlabelled problems are omitted.

    PRIMARY DISCRIMINATOR: kills impl including classes without labelled problems.
    'unlabelled_class' has only severity="" problems -> absent from result.
    'labelled_class' has HIGH -> present with value 'HIGH'.
    """
    problems = [
        _p("unlabelled_class", 0),   # severity=""
        _p("unlabelled_class", 1),   # severity=""
        _ps("labelled_class", 2, "HIGH"),
    ]
    result = dominant_severity_per_class(problems)
    assert "unlabelled_class" not in result, (
        "'unlabelled_class' has no labelled problems -> omitted; got "
        + repr(result)
    )
    assert result.get("labelled_class") == "HIGH", (
        "'labelled_class' dominant is HIGH; got " + repr(result)
    )


def test_tie_break_lexicographically_smallest() -> None:
    """Tie-break uses lexicographically smallest severity string.

    Kills impl using largest-first or arbitrary tie-break.
    alpha: HIGH x2, LOW x2. HIGH < LOW alphabetically -> HIGH wins tie.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("alpha", 3, "LOW"),
    ]
    result = dominant_severity_per_class(problems)
    assert result.get("alpha") == "HIGH", (
        "Tie between HIGH and LOW; 'HIGH' < 'LOW' lexicographically -> HIGH wins; got "
        + repr(result.get("alpha"))
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising.

    Kills impl raising on empty list.
    """
    result = dominant_severity_per_class([])
    assert result == {}, "Empty input -> {}; got " + repr(result)


def test_single_labelled_problem_is_dominant() -> None:
    """A class with exactly one labelled problem uses that severity as dominant.

    Kills impl requiring >=2 labelled problems to compute a dominant.
    """
    problems = [_ps("alpha", 0, "CRITICAL")]
    result = dominant_severity_per_class(problems)
    assert result == {"alpha": "CRITICAL"}, (
        "Single labelled problem -> {'alpha': 'CRITICAL'}; got " + repr(result)
    )


def test_return_type_is_dict_str_str() -> None:
    """Return type is dict[str, str] — both keys and values are strings.

    Kills impl returning Problem objects or integer counts.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = dominant_severity_per_class(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, sev in result.items():
        assert isinstance(cls, str) and isinstance(sev, str), (
            "Both key and value must be str; got "
            + repr((type(cls), type(sev)))
        )
