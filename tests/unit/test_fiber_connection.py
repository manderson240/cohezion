import pytest
from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.tensor_calculus import VectorTensor
from cohezion.physics.fiber_connection import FiberConnectionEngine

def test_christoffel_symbols_origin():
    # At origin (0, ..., 0), Christoffel symbols Gamma^k_{ij} are 0
    pt_origin = PoincarePoint(tuple([0.0] * 12))
    gamma = FiberConnectionEngine.christoffel_symbols(pt_origin)
    assert len(gamma) == 12
    assert gamma[0][0][0] == 0.0

def test_christoffel_symbols_off_origin():
    pt = PoincareManifoldND.project(tuple([0.1] * 12))
    gamma = FiberConnectionEngine.christoffel_symbols(pt)
    assert len(gamma) == 12
    assert gamma[0][0][0] != 0.0  # Non-zero connection off origin

def test_covariant_derivative_step():
    pt = PoincareManifoldND.project(tuple([0.1] * 12))
    v = VectorTensor(tuple([1.0] + [0.0] * 11))
    u = VectorTensor(tuple([0.1] * 12))

    cov_der = FiberConnectionEngine.covariant_derivative_step(v, pt, u)
    assert isinstance(cov_der, VectorTensor)
    assert cov_der.dim == 12
