"""Item 387: classes_with_shared_finding_ids() — classes owning ≥1 shared fid (2026-06-08).

``classes_with_shared_finding_ids(problems) -> frozenset[str]``:
Returns the frozenset of problem_class names that own at least one finding_id
also present under another class.  Classes with all-unique finding_ids are
excluded.  Empty → frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns CLASS NAMES (not finding_ids).
     Kills impl returning finding_ids_shared_across_classes.
  2. A class is included if ANY of its fids is shared (not ALL).
     Kills impl requiring all fids to be shared.
  3. Classes with only unique fids are excluded.
     Kills impl including all classes.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. A single shared fid pulls in BOTH classes that own it.
     Kills impl counting only the "source" class.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_with_shared_finding_ids,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_class_names_not_finding_ids() -> None:
    """Returns class name strings, not finding_ids.

    PRIMARY DISCRIMINATOR: kills impl returning finding_ids_shared_across_classes.
    """
    problems = [_p("alpha", "shared"), _p("beta", "shared"), _p("gamma", "unique")]
    result = classes_with_shared_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset"
    assert all(isinstance(v, str) for v in result), "Elements must be class name strings"
    assert "alpha" in result, "alpha owns shared fid → included; got " + repr(result)
    assert "beta" in result, "beta owns shared fid → included; got " + repr(result)
    assert "gamma" not in result, "gamma has only unique fid → excluded; got " + repr(result)
    assert "shared" not in result, "finding_id must NOT appear in result; got " + repr(result)


def test_any_shared_fid_qualifies_class() -> None:
    """A class qualifies if ANY of its fids is shared (not all).

    Kills impl requiring all fids to be shared.
    alpha has: shared fid + unique fid → alpha still qualifies.
    """
    problems = [
        _p("alpha", "shared"),
        _p("beta", "shared"),
        _p("alpha", "alpha-only"),
    ]
    result = classes_with_shared_finding_ids(problems)
    assert "alpha" in result, "alpha has 1 shared fid + 1 unique → included"
    assert "beta" in result, "beta has 1 shared fid → included"


def test_all_unique_fids_excluded() -> None:
    """Classes with all-unique finding_ids are excluded.

    Kills impl including all classes.
    """
    problems = [
        _p("a", "fid:only-a"),
        _p("b", "fid:only-b"),
        _p("c", "fid:only-c"),
    ]
    result = classes_with_shared_finding_ids(problems)
    assert result == frozenset(), "No shared fids → empty result; got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input returns frozenset()."""
    assert classes_with_shared_finding_ids([]) == frozenset()


def test_single_shared_fid_pulls_in_both_classes() -> None:
    """A single shared fid includes BOTH classes that own it.

    Kills impl counting only the 'source' class.
    """
    problems = [_p("cls1", "link"), _p("cls2", "link"), _p("cls3", "unique")]
    result = classes_with_shared_finding_ids(problems)
    assert result == frozenset({"cls1", "cls2"}), (
        "Both classes sharing fid 'link' must be in result; got " + repr(result)
    )
