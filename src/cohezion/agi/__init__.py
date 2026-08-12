"""Cohezion AGI Progress & AutoHarness Synthesis Package

Implements AutoHarness (arXiv:2603.03329v1) code-as-action policy synthesis,
ARC-Prize/AIMO reasoning solvers, and self-evaluating R-Zero evolution.

WHY THE GUARD BELOW: this package eagerly re-exported ``kaggle_autoharness``, which
imports ``cohezion.inference.unified_hybrid_router``. That module is absent from this
branch, so the failed import propagated out of ``__init__`` and made EVERY module in the
package unimportable -- including ``agi.flume_vae``, which loads perfectly standalone and
does not reference the router, directly or transitively.

One missing optional sibling should not blackhole a package. The guard is deliberately
NOT silent: a suppressed ImportError here reads exactly like "the feature does not exist",
which is how a dependency gap becomes a phantom dormancy finding.

``__all__`` is built from what actually imported, so it never advertises a name that is
not bound -- otherwise ``from cohezion.agi import *`` raises AttributeError on a name this
module itself promised.
"""

from __future__ import annotations

import logging

from cohezion.agi.autoharness_policy import ActionPolicyResult, AutoHarnessPolicy

logger = logging.getLogger(__name__)

__all__ = ["ActionPolicyResult", "AutoHarnessPolicy"]

try:
    from cohezion.agi.kaggle_autoharness import (
        AIMOProofState,
        ARCGridInvariant,
        KaggleAutoHarness,
        KaggleHarnessResult,
    )
except ImportError as exc:  # pragma: no cover - depends on branch state
    logger.warning(
        "cohezion.agi: kaggle_autoharness unavailable (%s). Its four names are not "
        "exported; the rest of the package, including flume_vae, is unaffected.",
        exc,
    )
else:
    __all__ += [
        "AIMOProofState",
        "ARCGridInvariant",
        "KaggleAutoHarness",
        "KaggleHarnessResult",
    ]
