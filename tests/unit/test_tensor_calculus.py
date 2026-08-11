import math
import pytest
from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.tensor_calculus import ScalarTensor, VectorTensor, TensorCalculus

def test_scalar_tensor_arithmetic():
    s1 = ScalarTensor(0.5, name="coherence")
    s2 = ScalarTensor(0.3, name="coherence")
    s_sum = s1 + s2
    assert pytest.approx(s_sum.value) == 0.8

    s_prod = s1 * 2.0
    assert pytest.approx(s_prod.value) == 1.0

def test_vector_tensor_norms():
    position = PoincareManifoldND.project(tuple([0.1] * 12))
    v = VectorTensor(tuple([1.0] + [0.0] * 11))

    assert pytest.approx(v.norm_euclidean()) == 1.0
    v_norm_g = v.norm_poincare(position)
    assert v_norm_g > 1.0  # Conformal factor > 1 inside unit ball

def test_tensor_index_raising_lowering():
    position = PoincareManifoldND.project(tuple([0.1] * 12))
    v_contra = VectorTensor(tuple([0.5] * 12), is_covariant=False)

    # Lower index V_i = g_ij V^j
    v_cov = TensorCalculus.lower_index(v_contra, position)
    assert v_cov.is_covariant is True

    # Raise index V^i = g^ij V_j back to original
    v_reconstructed = TensorCalculus.raise_index(v_cov, position)
    assert v_reconstructed.is_covariant is False
    for orig, rec in zip(v_contra.components, v_reconstructed.components):
        assert pytest.approx(orig, abs=1e-5) == rec

def test_tensor_inner_product():
    position = PoincareManifoldND.project(tuple([0.05] * 256))
    u = VectorTensor(tuple([0.1] * 256))
    v = VectorTensor(tuple([0.2] * 256))

    prod = TensorCalculus.inner_product(u, v, position)
    assert isinstance(prod, ScalarTensor)
    assert prod.value > 0.0
