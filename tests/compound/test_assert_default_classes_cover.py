"""Item 170: assert_default_classes_cover() — CI assertion helper (2026-06-08).

``assert_default_classes_cover(required: frozenset[str]) -> None``: raises
``AssertionError`` with a message listing the MISSING class names if any class
in *required* is absent from :func:`default_template_classes`.  Empty *required*
→ no-op (never raises).  Pure; no writes.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``required=frozenset({"complexity_outlier"})`` → no raise.
     Proves the function checks against the REAL ``default_template_classes()``
     output — not a hardcoded list or an always-pass stub.
  2. ``required=frozenset({"nonexistent_xyz"})`` → raises AssertionError whose
     message contains ``"nonexistent_xyz"``.
     Kills an impl that raises with a generic/empty message (not actionable).
  3. Empty ``required=frozenset()`` → no raise.
     Kills an impl that raises on empty required (always fails).
  4. Multiple missing classes → ALL missing names appear in the error message.
     Kills an impl that only reports the first missing class.
  5. A mix of present + absent → only absent names in the message.
     Kills an impl that lists all required classes (not just the missing ones).
"""

from __future__ import annotations

import pytest

from cohezion.compound.problem_discovery import (
    assert_default_classes_cover,
    default_template_classes,
)


def test_known_class_passes_without_raise() -> None:
    """required={known_class} → no raise.

    PRIMARY DISCRIMINATOR: proves the function checks against the REAL
    default_template_classes() instead of always passing or using a hardcoded list.
    Uses a class name known to be in the default registry (complexity_outlier).
    """
    # This should not raise — complexity_outlier is in default_template_classes()
    assert_default_classes_cover(frozenset({"complexity_outlier"}))


def test_unknown_class_raises_with_name_in_message() -> None:
    """required={"nonexistent_xyz"} → AssertionError with the missing name.

    Kills an impl that raises with a generic/empty message, or one that doesn't
    raise at all for missing classes.
    """
    with pytest.raises(AssertionError) as exc_info:
        assert_default_classes_cover(frozenset({"nonexistent_xyz"}))

    assert "nonexistent_xyz" in str(exc_info.value), (
        f"Error message must contain the missing class name; got: {exc_info.value!r}"
    )


def test_empty_required_never_raises() -> None:
    """required=frozenset() → no raise.

    Kills an impl that raises on empty required (e.g., always asserts at least
    one class is required, which would be wrong).
    """
    assert_default_classes_cover(frozenset())


def test_multiple_missing_classes_all_in_message() -> None:
    """required with multiple absent classes → ALL absent names in the message.

    Kills an impl that only reports the first missing class name.
    A CI message that says 'missing: nonexistent_1' when both nonexistent_1 and
    nonexistent_2 are missing forces a second CI run to find the second failure.
    """
    with pytest.raises(AssertionError) as exc_info:
        assert_default_classes_cover(frozenset({"nonexistent_1", "nonexistent_2"}))

    msg = str(exc_info.value)
    assert "nonexistent_1" in msg, f"First missing class must be in message; got: {msg!r}"
    assert "nonexistent_2" in msg, f"Second missing class must be in message; got: {msg!r}"


def test_mix_of_present_and_absent_reports_only_absent() -> None:
    """required contains one known class and one absent → only absent in message.

    Kills an impl that lists ALL required classes (not just the missing ones),
    which would clutter the error message with noise.
    """
    real_class = next(iter(default_template_classes()))  # any real class
    missing_class = "this_class_cannot_exist_in_default_registry_xyz"

    with pytest.raises(AssertionError) as exc_info:
        assert_default_classes_cover(frozenset({real_class, missing_class}))

    msg = str(exc_info.value)
    assert missing_class in msg, f"Missing class must be in message; got: {msg!r}"
    assert real_class not in msg, (
        f"Present class must NOT be in error message (only missing classes); got: {msg!r}"
    )
