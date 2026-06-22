"""Hookify Rule Engine - Universal cross-platform rule system"""

import contextlib

from cohezion.hookify.validator import HookifyValidator, Rule, ValidationResult


__all__ = ["HookifyValidator", "Rule", "ValidationResult"]

with contextlib.suppress(Exception):
    from cohezion.hookify.adversarial_review import (
        AdversarialReviewHarness as AdversarialReviewHarness,
    )
    from cohezion.hookify.adversarial_review import (
        AdversarialReviewResult as AdversarialReviewResult,
    )
    from cohezion.hookify.adversarial_review import ConsensusVoter as ConsensusVoter
    from cohezion.hookify.adversarial_review import (
        ReviewPerspective as ReviewPerspective,
    )

with contextlib.suppress(Exception):
    from cohezion.hookify.vault_writer import HookifyVaultWriter as HookifyVaultWriter
