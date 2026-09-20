"""The HIHO coherence kernel, defined once, with its information-geometric reading.

``hiho_kernel(x) = 4 x (1 - x)`` on ``[0, 1]``: maximum 1 at ``x = 0.5``, symmetric about it,
zero at both ends. Nineteen executable sites in ``physics/``, ``model/`` and ``compound/``
restate the literal (measured 2026-09-20); this module is the identity point they can share.

What the kernel IS (2026-09-20, from the categorical-family discussion): for a Bernoulli
variable with success probability ``x``, the variance is ``x(1 - x)`` and the Fisher
information is its reciprocal, ``I(x) = 1 / (x(1 - x))``. So

    hiho_kernel(x) = 4 · Var[Bernoulli(x)] = 4 / I(x).

The HIHO point ``x = 0.5`` is therefore the point of LEAST Fisher information per unit of
probability change -- the flattest point of the Bernoulli statistical manifold, where an
observation moves the belief least. "Peak coherence at 0.5" and "maximum entropy / minimum
curvature" are the same statement. The factor 4 normalises the peak to 1. The Bernoulli
family is an exponential family whose natural parameter is the log-odds; the same reading
holds for every categorical coordinate. Verified numerically in
``tests/physics/test_hiho_kernel.py`` against the Fisher information computed from the score.

Stdlib only (reflex lineage): importable in a fresh interpreter with no package machinery.
"""

from __future__ import annotations


__all__ = ["bernoulli_fisher_information", "hiho_kernel"]


def hiho_kernel(x: float) -> float:
    """``4 x (1 - x)``. Peak 1.0 at 0.5; 0.0 at 0 and 1; symmetric: k(x) == k(1 - x)."""
    return 4.0 * x * (1.0 - x)


def bernoulli_fisher_information(x: float) -> float:
    """``I(x) = 1 / (x (1 - x))`` for ``0 < x < 1``; the kernel is ``4 / I(x)``."""
    if not 0.0 < x < 1.0:
        raise ValueError("Fisher information is defined on the open interval (0, 1)")
    return 1.0 / (x * (1.0 - x))
