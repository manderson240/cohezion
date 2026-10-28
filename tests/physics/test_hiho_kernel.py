"""hiho_kernel: the two provable properties, the Fisher identity measured (not asserted), and
a CONSUMPTION check that the compound site reads it rather than restating the literal."""

from __future__ import annotations

import inspect
import math

import pytest

from cohezion.physics.hiho_kernel import bernoulli_fisher_information, hiho_kernel


@pytest.mark.parametrize("x", [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
def test_symmetric_about_one_half(x):
    assert hiho_kernel(x) == pytest.approx(hiho_kernel(1.0 - x))


def test_unique_maximum_of_one_at_one_half():
    grid = [i / 1000 for i in range(1001)]
    vals = [hiho_kernel(x) for x in grid]
    assert max(vals) == pytest.approx(1.0)
    assert grid[vals.index(max(vals))] == pytest.approx(0.5)
    assert hiho_kernel(0.0) == 0.0 and hiho_kernel(1.0) == 0.0


def _fisher_from_score(p: float, h: float = 1e-6) -> float:
    """I(p) = E[(d/dp log P(X|p))^2] for X ~ Bernoulli(p), by finite-difference score."""
    total = 0.0
    for x, prob in ((1, p), (0, 1.0 - p)):

        def lp(q: float, x: int = x) -> float:
            return math.log(q if x == 1 else 1.0 - q)

        score = (lp(p + h) - lp(p - h)) / (2 * h)
        total += prob * score * score
    return total


@pytest.mark.parametrize("p", [0.05, 0.2, 0.5, 0.8, 0.95])
def test_kernel_is_four_over_the_fisher_information_measured(p):
    """The identity is checked against Fisher information computed from the score, not
    from the closed form the module itself states -- an independent oracle."""
    fisher = _fisher_from_score(p)
    assert fisher == pytest.approx(bernoulli_fisher_information(p), rel=1e-5)
    assert hiho_kernel(p) == pytest.approx(4.0 / fisher, rel=1e-5)


@pytest.mark.parametrize("bad", [-0.1, 1.1, -1e-9, 1.0000001])
def test_kernel_rejects_inputs_outside_the_unit_interval(bad):
    """Found by the local scientific-rigor lens (falsifier: hiho_kernel(-0.1) == -0.44)."""
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        hiho_kernel(bad)


def test_fisher_information_rejects_the_closed_endpoints():
    for bad in (0.0, 1.0, -0.1, 1.1):
        with pytest.raises(ValueError):
            bernoulli_fisher_information(bad)


def test_reflex_lineage_stdlib_only():
    src = inspect.getsource(inspect.getmodule(hiho_kernel))
    assert "import numpy" not in src and "from cohezion" not in src


def test_CONSUMPTION_greek_parameters_gamma_reads_the_shared_kernel():
    """Neutralising the wiring (restoring the literal in gamma) turns this red."""
    from cohezion.compound.greek_parameters import GreekParameters

    src = inspect.getsource(GreekParameters.gamma)
    assert "hiho_kernel" in src
    assert "4.0 * x * (1.0 - x)" not in src
    assert GreekParameters().gamma(0.3) == pytest.approx(hiho_kernel(0.3))
