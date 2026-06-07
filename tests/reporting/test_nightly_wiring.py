"""Wiring proof: reporting.nightly is reachable via a static import edge (wiring sweep 2026-06-06).

`reporting/nightly.py` (`NightlyReporter`) had no static prod import edge and an empty package
`__init__` — reached only by `tests/reporting/test_nightly.py` (Class B, tests-only). It is wired
non-destructively by an `X as X` re-export in `cohezion/reporting/__init__.py` (the package init is
reachable, so the re-export is a literal static edge a static analyzer can follow). These tests FAIL
if that edge is removed.
"""

from __future__ import annotations


def test_nightly_reporter_reexported_from_package() -> None:
    # Reachable from the PACKAGE surface — fails (ImportError) if the __init__ re-export is removed.
    from cohezion.reporting import NightlyReporter

    assert NightlyReporter is not None


def test_reexport_is_the_same_class_as_submodule() -> None:
    # The re-export must be the SAME object as the submodule's class (a wrong/shadowing re-export fails).
    from cohezion.reporting import NightlyReporter
    from cohezion.reporting.nightly import NightlyReporter as Submodule

    assert NightlyReporter is Submodule
