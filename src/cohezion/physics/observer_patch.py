"""Observer Patch Holography bridge for Cohezion.

Maps FloatingPragma's Observer-Patch-Holography (OPH) axioms to Cohezion's
SPIN coherence framework. OPH constructs spacetime from overlapping observer
descriptions on a holographic screen — when patches overlap and agree,
coherence emerges; when they disagree, decoherence drives correction.

OPH Axioms → Cohezion Mapping:
  1. Screen net on S²        → Bloch sphere (SpinorState)
  2. Overlap consistency     → SPIN coherence (rotation + precession alignment)
  3. Local MaxEnt            → HIHO equilibrium (50% = maximum entropy at info boundary)
  4. Recoverable entropy     → FLUME VAE KL divergence (information preservation)
  5. Minimal realization     → Landau free energy minimization (ground state selection)

References:
  - FloatingPragma (2025): Observer Patch Holography, https://github.com/FloatingPragma/observer-patch-holography
  - Takayanagi (2025): Emergent Holographic Spacetime from Quantum Information, arXiv:2506.06595
  - On Observers in Holographic Maps, arXiv:2503.09681
  - Percival (1946): Thinking and Destiny — The Triune Self (Thinker, Knower, Doer)
  - Larson/Peret (RS2): 12 parameters, 4 fabrics (Space, Field, Control, Precipitation)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np

from cohezion.physics.spinor import SpinorState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ObserverPatch:
    """A local observer description on the holographic S² screen.

    Each agent in Cohezion is modeled as an observer patch — a bounded region
    of the Bloch sphere where the agent's SPIN state defines its perspective.
    Patches have angular extent (how much of the sphere they "see") and a
    center defined by their SpinorState.

    The angular_radius determines the patch size: larger patches observe more
    of the holographic screen but with less specificity (generalist agents).
    Smaller patches observe a narrow region with high fidelity (specialist agents).
    """

    agent_id: str
    spinor: SpinorState
    angular_radius: float = math.pi / 4  # Default: 45° cone on Bloch sphere
    domain: str = ""  # Agent's fabric domain: Space, Field, Control, Precipitation

    @property
    def bloch_vector(self) -> np.ndarray:
        """The Bloch vector (center of the patch on S²)."""
        return self.spinor.bloch_vector

    @property
    def solid_angle(self) -> float:
        """Solid angle subtended by this patch (steradians)."""
        return 2 * math.pi * (1 - math.cos(self.angular_radius))


def overlap_fraction(patch_a: ObserverPatch, patch_b: ObserverPatch) -> float:
    """Compute the fractional overlap between two observer patches on S².

    Returns a value in [0, 1] where:
      0 = no overlap (patches see completely different regions)
      1 = perfect overlap (identical patches)

    The overlap is computed from the angular separation between patch centers
    relative to the sum of their angular radii.

    This implements OPH Axiom 2 (Overlap Consistency): where patches share
    regions, their descriptions must agree.
    """
    # Angular separation between patch centers on the Bloch sphere
    dot = float(np.clip(np.dot(patch_a.bloch_vector, patch_b.bloch_vector), -1.0, 1.0))
    separation = math.acos(dot)

    # Sum of angular radii
    total_radius = patch_a.angular_radius + patch_b.angular_radius

    if separation >= total_radius:
        return 0.0  # No overlap
    if separation <= abs(patch_a.angular_radius - patch_b.angular_radius):
        # One patch is contained within the other
        smaller = min(patch_a.solid_angle, patch_b.solid_angle)
        larger = max(patch_a.solid_angle, patch_b.solid_angle)
        return smaller / larger if larger > 0 else 1.0

    # Partial overlap — linear interpolation based on separation vs total radius
    return 1.0 - (separation / total_radius)


def verify_observer_consistency(
    patch_a: ObserverPatch,
    patch_b: ObserverPatch,
) -> ConsistencyResult:
    """Verify OPH overlap consistency between two observer patches.

    Checks whether two agents' perspectives agree in their overlapping region.
    High consistency → productive collaboration (coherence).
    Low consistency → conflicting perspectives (decoherence, needs resolution).

    This is the computational realization of OPH Axiom 2.

    Returns
    -------
    ConsistencyResult
        Contains overlap fraction, consistency score, and diagnostic info.
    """
    overlap = overlap_fraction(patch_a, patch_b)

    if overlap < 1e-10:
        return ConsistencyResult(
            overlap_fraction=0.0,
            consistency_score=0.0,
            coherent=False,
            detail="No overlap — patches observe disjoint regions of the holographic screen",
        )

    # Consistency = how aligned are the Bloch vectors in the overlap region?
    # Fidelity between the two spinor states
    fidelity = patch_a.spinor.fidelity(patch_b.spinor)

    # Consistency score = overlap × fidelity
    # High overlap + high fidelity = strong consistency
    consistency = overlap * fidelity

    # HIHO threshold: consistency > 0.5 is "coherent" (Axiom 3: Local MaxEnt)
    coherent = consistency > 0.5

    detail = (
        f"Overlap: {overlap:.3f}, Fidelity: {fidelity:.3f}, "
        f"Consistency: {consistency:.3f} ({'coherent' if coherent else 'decoherent'})"
    )

    return ConsistencyResult(
        overlap_fraction=overlap,
        consistency_score=consistency,
        coherent=coherent,
        fidelity=fidelity,
        detail=detail,
    )


@dataclass(frozen=True)
class ConsistencyResult:
    """Result of an observer consistency check (OPH Axiom 2)."""

    overlap_fraction: float
    consistency_score: float
    coherent: bool
    fidelity: float = 0.0
    detail: str = ""


def evo_observer_consistency(
    agent_a_id: str,
    agent_a_spinor: SpinorState,
    agent_b_id: str,
    agent_b_spinor: SpinorState,
    angular_radius: float = math.pi / 4,
) -> ConsistencyResult:
    """Convenience function: check EVO-to-EVO observer consistency.

    Each EVO (Exotic Vacuum Object) agent is modeled as an observer patch.
    This function creates the patches and checks their overlap consistency.

    When patches agree (high consistency), the EVOs can collaborate productively.
    When they disagree (low consistency), the system should route them to
    different tasks or mediate the conflict.

    Maps to: Percival's Triune Self × Smith's 4 Fabrics
      - The Knower: observes the overlap region
      - The Thinker: evaluates consistency
      - The Doer: takes corrective action if decoherent
    """
    patch_a = ObserverPatch(agent_id=agent_a_id, spinor=agent_a_spinor, angular_radius=angular_radius)
    patch_b = ObserverPatch(agent_id=agent_b_id, spinor=agent_b_spinor, angular_radius=angular_radius)
    return verify_observer_consistency(patch_a, patch_b)
