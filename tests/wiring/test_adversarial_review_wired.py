"""Discriminating test for the wiring-sweep edge: hookify → adversarial_review (2026-06-06).

`hookify/adversarial_review` was a genuine production orphan — its AdversarialReviewHarness /
ConsensusVoter / AdversarialReviewResult / ReviewPerspective (graph-aware adversarial review OF
HOOKIFY RULES) had ZERO importers. VERIFIED DISTINCT from compound/tdd_adversarial/adversarial_review
(which reviews compound-engineering decisions) — wired non-destructively, not consolidated.

Falsifiable: fails if the static edge is removed — every name must resolve FROM the package AND be
the hookify module's own object (identity), and appear in __all__. The identity check also guards
against accidentally re-exporting the SAME-NAMED compound symbol instead of hookify's.
"""

from __future__ import annotations

import cohezion.hookify as hookify
import cohezion.hookify.adversarial_review as src


def test_adversarial_review_reexported_from_hookify() -> None:
    for name in (
        "AdversarialReviewHarness",
        "ConsensusVoter",
        "AdversarialReviewResult",
        "ReviewPerspective",
    ):
        assert hasattr(hookify, name), f"hookify.{name} unreachable — wiring edge missing"
        assert getattr(hookify, name) is getattr(src, name), (
            f"{name} is not hookify's source object"
        )
        assert name in hookify.__all__, f"{name} missing from hookify.__all__"


def test_reexported_review_perspective_is_hookify_not_compound() -> None:
    # Name collision guard: hookify.ReviewPerspective must be HOOKIFY's (a dataclass), NOT the
    # compound/tdd_adversarial Enum of the same name — proving distinct, correctly-wired modules.
    import cohezion.compound.tdd_adversarial.adversarial_review as compound_ar

    assert hookify.ReviewPerspective is src.ReviewPerspective
    assert hookify.ReviewPerspective is not compound_ar.ReviewPerspective
