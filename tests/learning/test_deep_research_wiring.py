"""Wiring proof: learning.deep_research is reachable via a static import edge (wiring sweep 2026-06-06).

`learning/deep_research.py` (`DeepResearchPipeline`) was the last Class-A orphan in the learning
package — 0 static prod import edges, 0 tests, 0 registry/string refs. It is wired non-destructively
by an `X as X` re-export in `cohezion/learning/__init__.py` (the package init is reachable, so the
re-export is a literal static edge). These tests FAIL if that edge is removed.
"""

from __future__ import annotations


def test_deep_research_pipeline_reexported_from_package() -> None:
    # Reachable from the PACKAGE surface — fails (ImportError) if the __init__ re-export is removed.
    from cohezion.learning import DeepResearchPipeline

    assert DeepResearchPipeline is not None


def test_reexport_is_the_same_class_as_submodule() -> None:
    # The re-export must be the SAME object as the submodule's class (a wrong/shadowing re-export fails).
    from cohezion.learning import DeepResearchPipeline
    from cohezion.learning.deep_research import DeepResearchPipeline as Submodule

    assert DeepResearchPipeline is Submodule
