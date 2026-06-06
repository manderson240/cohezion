"""Hookify Rule Engine - Universal cross-platform rule system"""

import contextlib

from cohezion.hookify.validator import HookifyValidator, Rule, ValidationResult


__all__ = ["HookifyValidator", "Rule", "ValidationResult"]

# Wiring-sweep 2026-06-06: adversarial_review was a genuine production orphan — its
# AdversarialReviewHarness / ConsensusVoter / AdversarialReviewResult / ReviewPerspective
# (graph-aware adversarial review OF HOOKIFY RULES, review_rule(Rule)) had ZERO importers.
# VERIFIED DISTINCT (not a duplicate) from compound/tdd_adversarial/adversarial_review, which
# reviews compound-engineering DECISIONS (project_root, skill-refinement) — different domain, API,
# and class set; the shared `ReviewPerspective` name is coincidence (dataclass here vs Enum there).
# Cycle-safe (only a TYPE_CHECKING import of hookify.validator.Rule). Guarded re-export.
with contextlib.suppress(Exception):
    from cohezion.hookify.adversarial_review import (
        AdversarialReviewHarness as AdversarialReviewHarness,
    )
    from cohezion.hookify.adversarial_review import (
        AdversarialReviewResult as AdversarialReviewResult,
    )
    from cohezion.hookify.adversarial_review import (
        ConsensusVoter as ConsensusVoter,
    )
    from cohezion.hookify.adversarial_review import (
        ReviewPerspective as ReviewPerspective,
    )

    __all__ += [
        "AdversarialReviewHarness",
        "AdversarialReviewResult",
        "ConsensusVoter",
        "ReviewPerspective",
    ]
