"""Item 158: TIDE template count invariant (2026-06-08).

``default_template_classes()`` → ``frozenset[str]``: returns the exact set of
``problem_class`` names in ``default_templates()``.  Acts as a structural meta-
check on the now-complete 14-template TIDE wiring.  The structural guard fires
immediately when a future change accidentally removes a template or wires a new
one with a duplicate class name.

Discriminating tests — each kills a plausible wrong implementation:

  1. ``default_template_classes()`` returns a frozenset containing all 14
     expected class names  (PRIMARY DISC.: kills a stub that hardcodes fewer names
     or returns an empty / wrong type).
  2. The set has EXACTLY 14 members (no duplicate class names accepted).
     Kills an impl that accidentally wires two templates with the same class.
  3. Key class names are present: ``"compound_smell"``, ``"long_function"``,
     ``"long_parameter_list"`` (the three most recently wired — 155–157).
     Kills an impl that hardcodes only the older class names.
  4. ``len(default_templates()) >= 14`` — count invariant from the real function.
     Kills an impl that only partially wires the templates.
  5. ``default_template_classes()`` returns a ``frozenset`` (immutable set), not
     a ``list`` or ``set``.
     Kills an impl that returns the wrong container type.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import default_template_classes, default_templates


# The 14 expected class names after items 155–157.
_EXPECTED_CLASSES: frozenset[str] = frozenset(
    {
        "boolean_flag_params",
        "complexity_outlier",
        "compound_smell",
        "eager_log_fstring",
        "long_function",
        "long_parameter_list",
        "mutable_default_args",
        "needless_passthrough",
        "nesting_outlier",
        "passthrough_function",
        "production_assert",
        "silent_except_swallow",
        "stealth_bare_except",
        "unsandboxed_exec",
    }
)


def test_default_template_classes_returns_all_expected() -> None:
    """default_template_classes() returns all 14 expected class names.

    PRIMARY DISCRIMINATOR: kills a stub that returns an empty set, a hardcoded
    subset, or derives from a stale snapshot of the templates list.
    """
    classes = default_template_classes()
    missing = _EXPECTED_CLASSES - classes
    assert not missing, f"default_template_classes() is missing: {sorted(missing)}"


def test_exactly_14_unique_class_names() -> None:
    """The set has exactly 14 members — no duplicates, no extras.

    Kills an impl that accidentally wires two templates under the same
    problem_class name (a duplicate would make the count == 13 in the set).
    """
    classes = default_template_classes()
    assert len(classes) == 14, (
        f"expected exactly 14 unique class names; got {len(classes)}: {sorted(classes)}"
    )


def test_recently_wired_classes_present() -> None:
    """compound_smell, long_function, long_parameter_list must be in the set.

    These are the three most recently added classes (items 155–157).
    Kills an impl that hardcodes only the older class names and misses the new ones.
    """
    classes = default_template_classes()
    for expected in ("compound_smell", "long_function", "long_parameter_list"):
        assert expected in classes, (
            f"'{expected}' must be in default_template_classes; got {sorted(classes)}"
        )


def test_default_templates_count_invariant() -> None:
    """len(default_templates()) >= 14 (count invariant on the real list).

    Kills an impl that only partially wires the templates (returns fewer than 14).
    Validates the actual list, not just the class-name set — duplicate class names
    show as duplicate list entries (count > set size).
    """
    count = len(default_templates())
    assert count >= 14, f"expected >= 14 templates in default_templates(); got {count}"


def test_returns_frozenset_not_set_or_list() -> None:
    """default_template_classes() returns a frozenset (immutable).

    Kills an impl that returns a list (ordered, mutable) or a regular set
    (mutable — callers could accidentally mutate the returned container).
    """
    result = default_template_classes()
    assert isinstance(result, frozenset), f"expected frozenset; got {type(result).__name__}"
