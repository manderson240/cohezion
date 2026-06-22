"""Identity + discriminating tests: flume/ and physics/ orphan wiring sweep 2026-06-22 (round-5)."""

import math

import torch

# ── flume package-level re-exports ────────────────────────────────────────────
from cohezion.flume import FlumeVAE as pkg_FlumeVAE
from cohezion.flume import FlumeVAEConfig as pkg_FlumeVAEConfig
from cohezion.flume import FlumeVAETrainer as pkg_FlumeVAETrainer
from cohezion.flume import LatentMessage as pkg_LatentMessage
from cohezion.flume import MorphospaceMapper as pkg_MorphospaceMapper
from cohezion.flume import SharedLatentMemory as pkg_SharedLatentMemory
from cohezion.flume import TurboQuantCPU as pkg_TurboQuantCPU
from cohezion.flume import lerp as pkg_lerp
from cohezion.flume import similarity_score as pkg_similarity_score
from cohezion.flume import slerp as pkg_slerp

# ── flume source modules (for identity checks) ────────────────────────────────
from cohezion.flume.latent_channel import LatentMessage as src_LatentMessage
from cohezion.flume.latent_channel import SharedLatentMemory as src_SharedLatentMemory
from cohezion.flume.morphospace import MorphospaceMapper as src_MorphospaceMapper
from cohezion.flume.navigation import lerp as src_lerp
from cohezion.flume.navigation import similarity_score as src_similarity_score
from cohezion.flume.navigation import slerp as src_slerp
from cohezion.flume.turbo_quant import TurboQuantCPU as src_TurboQuantCPU
from cohezion.flume.vae import FlumeVAE as src_FlumeVAE
from cohezion.flume.vae import FlumeVAEConfig as src_FlumeVAEConfig

# ── physics package-level re-exports ─────────────────────────────────────────
from cohezion.physics import AnomalyGate as pkg_AnomalyGate
from cohezion.physics import ConservationFilter as pkg_ConservationFilter
from cohezion.physics import HamiltonianDynamics as pkg_HamiltonianDynamics
from cohezion.physics import InvariantChecker as pkg_InvariantChecker
from cohezion.physics import ObserverPatch as pkg_ObserverPatch
from cohezion.physics import OuroborosBridge as pkg_OuroborosBridge
from cohezion.physics import overlap_fraction as pkg_overlap_fraction

# ── physics source modules (for identity checks) ──────────────────────────────
from cohezion.physics.anomaly_gate import AnomalyGate as src_AnomalyGate
from cohezion.physics.conservation_filter import ConservationFilter as src_ConservationFilter
from cohezion.physics.hamiltonian import HamiltonianDynamics as src_HamiltonianDynamics
from cohezion.physics.invariant_checker import InvariantChecker as src_InvariantChecker
from cohezion.physics.observer_patch import ObserverPatch as src_ObserverPatch
from cohezion.physics.observer_patch import overlap_fraction as src_overlap_fraction
from cohezion.physics.ouroboros_bridge import OuroborosBridge as src_OuroborosBridge


# ── flume identity tests ──────────────────────────────────────────────────────


def test_flume_vae_identity():
    """FlumeVAE re-exported from package is the same object as the source class."""
    assert pkg_FlumeVAE is src_FlumeVAE


def test_flume_vae_config_identity():
    assert pkg_FlumeVAEConfig is src_FlumeVAEConfig


def test_lerp_identity():
    assert pkg_lerp is src_lerp


def test_slerp_identity():
    assert pkg_slerp is src_slerp


def test_similarity_score_identity():
    assert pkg_similarity_score is src_similarity_score


def test_turbo_quant_cpu_identity():
    assert pkg_TurboQuantCPU is src_TurboQuantCPU


def test_latent_message_identity():
    assert pkg_LatentMessage is src_LatentMessage


def test_shared_latent_memory_identity():
    assert pkg_SharedLatentMemory is src_SharedLatentMemory


def test_morphospace_mapper_identity():
    assert pkg_MorphospaceMapper is src_MorphospaceMapper


# ── flume behavioral tests ─────────────────────────────────────────────────────


def test_lerp_midpoint():
    """lerp at alpha=0.5 must be the element-wise midpoint of the two input tensors."""
    a = torch.tensor([0.0, 0.0])
    b = torch.tensor([4.0, 2.0])
    mid = pkg_lerp(a, b, 0.5)
    assert torch.allclose(mid, torch.tensor([2.0, 1.0]))


def test_lerp_endpoints():
    """lerp at alpha=0 returns a; alpha=1 returns b."""
    a = torch.tensor([1.0, 2.0])
    b = torch.tensor([5.0, 6.0])
    assert torch.allclose(pkg_lerp(a, b, 0.0), a)
    assert torch.allclose(pkg_lerp(a, b, 1.0), b)


def test_slerp_preserves_magnitude():
    """slerp must keep the interpolated tensor on the unit sphere (approx)."""
    a = torch.randn(32)
    a = a / a.norm()
    b = torch.randn(32)
    b = b / b.norm()
    mid = pkg_slerp(a, b, 0.5)
    assert abs(mid.norm().item() - 1.0) < 0.01, f"Expected unit norm, got {mid.norm().item():.4f}"


def test_similarity_score_self():
    """Cosine similarity of a vector with itself must be 1.0."""
    v = torch.randn(64)
    score = pkg_similarity_score(v, v)
    assert abs(score - 1.0) < 1e-5, f"Self-similarity should be 1.0, got {score}"


def test_similarity_score_orthogonal():
    """Orthogonal vectors normalised to [0,1] range must return 0.5.
    similarity_score = (cosine + 1) / 2, so orthogonal (cosine=0) → 0.5.
    Opposite (cosine=-1) → 0.0. This discriminates against an unnormalised cosine impl.
    """
    a = torch.zeros(4)
    a[0] = 1.0
    b = torch.zeros(4)
    b[1] = 1.0
    score = pkg_similarity_score(a, b)
    assert abs(score - 0.5) < 1e-5, f"Orthogonal vectors should score 0.5, got {score}"

    # Opposite direction must score 0.0
    score_opp = pkg_similarity_score(a, -a)
    assert abs(score_opp) < 1e-5, f"Opposite vectors should score 0.0, got {score_opp}"


def test_flume_vae_trainer_is_class():
    """FlumeVAETrainer must be a class (not None or a module)."""
    assert isinstance(pkg_FlumeVAETrainer, type)


# ── physics identity tests ─────────────────────────────────────────────────────


def test_anomaly_gate_identity():
    assert pkg_AnomalyGate is src_AnomalyGate


def test_conservation_filter_identity():
    assert pkg_ConservationFilter is src_ConservationFilter


def test_hamiltonian_dynamics_identity():
    assert pkg_HamiltonianDynamics is src_HamiltonianDynamics


def test_invariant_checker_identity():
    assert pkg_InvariantChecker is src_InvariantChecker


def test_observer_patch_identity():
    assert pkg_ObserverPatch is src_ObserverPatch


def test_overlap_fraction_identity():
    assert pkg_overlap_fraction is src_overlap_fraction


def test_ouroboros_bridge_identity():
    assert pkg_OuroborosBridge is src_OuroborosBridge


# ── physics behavioral tests ──────────────────────────────────────────────────


def test_overlap_fraction_self():
    """A patch fully overlapping itself must return 1.0.

    SpinorState(alpha, beta): |alpha|^2 + |beta|^2 = 1.  The |0⟩ state is alpha=1, beta=0.
    """

    from cohezion.physics.spinor import SpinorState

    spinor = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))
    patch = pkg_ObserverPatch(agent_id="a", spinor=spinor, angular_radius=math.pi / 4)
    frac = pkg_overlap_fraction(patch, patch)
    assert abs(frac - 1.0) < 1e-6, f"Self-overlap should be 1.0, got {frac}"


def test_overlap_fraction_antipodal():
    """Two patches at antipodal points on the Bloch sphere with tiny radii must return 0.0.

    |0⟩ = (1,0) → Bloch vector (0,0,+1).
    |1⟩ = (0,1) → Bloch vector (0,0,-1).
    With angular_radius=0.1 rad the patches don't overlap.
    """

    from cohezion.physics.spinor import SpinorState

    north = pkg_ObserverPatch(
        agent_id="north",
        spinor=SpinorState(alpha=complex(1, 0), beta=complex(0, 0)),
        angular_radius=0.1,
    )
    south = pkg_ObserverPatch(
        agent_id="south",
        spinor=SpinorState(alpha=complex(0, 0), beta=complex(1, 0)),
        angular_radius=0.1,
    )
    frac = pkg_overlap_fraction(north, south)
    assert frac == 0.0, f"Antipodal patches with small radii should return 0.0, got {frac}"


def test_hamiltonian_dynamics_is_class():
    """HamiltonianDynamics must be a class (not None or a module)."""
    assert isinstance(pkg_HamiltonianDynamics, type)
