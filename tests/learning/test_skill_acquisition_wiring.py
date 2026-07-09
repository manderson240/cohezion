"""Wiring proof: learning.skill_acquisition is reachable via a static import edge (wiring sweep 2026-06-06).

`learning/skill_acquisition.py` (`DynamicSkillAcquisition`) was a Class-A orphan — zero static prod
import edges, zero tests, zero registry/string refs. It is wired non-destructively by an `X as X`
re-export in `cohezion/learning/__init__.py` (the package init is reachable, so the re-export is a
literal static edge a bundler/IDE/the audit can follow). These tests FAIL if that edge is removed.
"""

from __future__ import annotations


def test_dynamic_skill_acquisition_reexported_from_package() -> None:
    # Reachable from the PACKAGE surface — fails (ImportError) if the __init__ re-export is removed.
    from cohezion.learning import DynamicSkillAcquisition

    assert DynamicSkillAcquisition is not None


def test_reexport_is_the_same_class_as_submodule() -> None:
    # The re-export must be the SAME object as the submodule's class (a wrong/shadowing re-export fails).
    from cohezion.learning import DynamicSkillAcquisition
    from cohezion.learning.skill_acquisition import (
        DynamicSkillAcquisition as Submodule,
    )

    assert DynamicSkillAcquisition is Submodule
