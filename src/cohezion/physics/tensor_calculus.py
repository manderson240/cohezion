r"""Scalar & Vector Tensor Calculus Module
=======================================
Implements Rank-0 (Scalar), Rank-1 (Vector / 1-form), and Rank-2 (Metric)
tensor calculus operations for N-dimensional Poincaré manifolds (12D, 256D).

Mathematical Definitions:
  - Rank-0 Scalar: S (invariant under coordinate transformations)
  - Rank-1 Vector (Contravariant): V^i transforming via (d x~/d x^j) V^j
  - Rank-1 1-Form (Covariant): W_i transforming via (d x^j/d x~^i) W_j
  - Inner Product under Metric g_ij: <U, V>_g = g_ij U^i V^j
  - Metric Tensor: g_ij(x) = (4 / (1 - ||x||^2)^2) * delta_ij
  - Inverse Metric Tensor: g^ij(x) = ((1 - ||x||^2)^2 / 4) * delta_ij
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cohezion.contracts import PoincarePoint


@dataclass(frozen=True, slots=True)
class ScalarTensor:
    """Rank-0 Tensor (Scalar invariant quantity)."""

    value: float
    name: str = "scalar"

    def __add__(self, other: ScalarTensor | float) -> ScalarTensor:
        val = other.value if isinstance(other, ScalarTensor) else float(other)
        return ScalarTensor(self.value + val, name=self.name)

    def __mul__(self, other: ScalarTensor | float) -> ScalarTensor:
        val = other.value if isinstance(other, ScalarTensor) else float(other)
        return ScalarTensor(self.value * val, name=self.name)


@dataclass(frozen=True, slots=True)
class VectorTensor:
    """Rank-1 Tensor (Contravariant or Covariant Vector)."""

    components: tuple[float, ...]
    is_covariant: bool = False  # False = Contravariant V^i, True = Covariant V_i

    def __post_init__(self) -> None:
        if not self.components:
            raise ValueError("VectorTensor components cannot be empty")

    @property
    def dim(self) -> int:
        return len(self.components)

    def norm_euclidean(self) -> float:
        """Euclidean norm sqrt(sum(V_i^2))."""
        return math.sqrt(sum(c * c for c in self.components))

    def norm_poincare(self, position: PoincarePoint) -> float:
        """Riemannian norm under Poincaré metric ||V||_g = sqrt(g_ij V^i V^j)."""
        if self.dim != position.dim:
            raise ValueError(
                f"Dimensional mismatch: vector is {self.dim}D, position is {position.dim}D"
            )

        r_sq = sum(c * c for c in position.coords)
        conformal_factor = 2.0 / (1.0 - r_sq)
        euclidean_norm = self.norm_euclidean()

        return conformal_factor * euclidean_norm


class TensorCalculus:
    """Tensor operations provider for Riemannian manifolds."""

    @classmethod
    def poincare_metric(cls, pt: PoincarePoint) -> float:
        """Compute the scalar conformal factor of the Poincaré metric g_ij(x)."""
        r_sq = sum(c * c for c in pt.coords)
        return 4.0 / ((1.0 - r_sq) ** 2)

    @classmethod
    def inner_product(
        cls, u: VectorTensor, v: VectorTensor, position: PoincarePoint
    ) -> ScalarTensor:
        """Compute Riemannian inner product <U, V>_g = g_ij U^i V^j."""
        if u.dim != v.dim or u.dim != position.dim:
            raise ValueError("Dimensional mismatch across vectors and position")

        g_scalar = cls.poincare_metric(position)
        dot_euclidean = sum(uc * vc for uc, vc in zip(u.components, v.components, strict=True))

        # g_ij = (4 / (1 - r^2)^2) * delta_ij
        inner_val = (2.0 / (1.0 - sum(c * c for c in position.coords))) ** 2 * dot_euclidean
        return ScalarTensor(inner_val, name="inner_product")

    @classmethod
    def lower_index(cls, v_contravariant: VectorTensor, position: PoincarePoint) -> VectorTensor:
        """Lower index V_i = g_ij V^j (contravariant to covariant 1-form)."""
        if v_contravariant.is_covariant:
            raise ValueError("Vector is already covariant")

        g_scale = (2.0 / (1.0 - sum(c * c for c in position.coords))) ** 2
        lowered = tuple(c * g_scale for c in v_contravariant.components)
        return VectorTensor(lowered, is_covariant=True)

    @classmethod
    def raise_index(cls, v_covariant: VectorTensor, position: PoincarePoint) -> VectorTensor:
        """Raise index V^i = g^ij V_j (covariant 1-form to contravariant vector)."""
        if not v_covariant.is_covariant:
            raise ValueError("Vector is already contravariant")

        g_inv_scale = ((1.0 - sum(c * c for c in position.coords)) / 2.0) ** 2
        raised = tuple(c * g_inv_scale for c in v_covariant.components)
        return VectorTensor(raised, is_covariant=False)
