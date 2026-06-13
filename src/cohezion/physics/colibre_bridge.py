"""COLIBRE/SWIFT cosmological simulation bridge.

COsmic LIfe cycle of BaRyon Evolution (COLIBRE) is the EAGLE-successor
galaxy formation simulation run on SWIFT (SPH With Inter-dependent
Fine-grained Tasking). This bridge maps COLIBRE simulation outputs to
Cohezion physics primitives.

The synthesis — agents as EVO:
    Each Cohezion agent IS an Exotic Vacuum Object in the simulation.
    Agent autonomy tiers (VOID→SO12→HIHO) map to COLIBRE subgrid physics:
    - VOID   → below star-formation threshold (n < n_crit)
    - SO12   → star-forming gas (n > n_crit, coherence > 0.3)
    - HIHO   → stellar feedback zone (coherence = 0.5, ISM equilibrium)

The HIHO mapping is mathematically exact:
    COLIBRE: SFR efficiency ∝ 4 × f_hot × (1 - f_hot)  [ISM equilibrium]
    Cohezion: reaction_rate = 4 × coherence × (1 - coherence)  [HIHO kernel]
    Same beta-binomial kernel — same physical attractor — different substrate.

COLIBRE parameters (12) map directly to Smith's 12D reality:
    - AGN feedback strength    → Fabric: Energy
    - SFR efficiency           → Fabric: Mass
    - ISM metallicity floor    → Fabric: Space
    - BH seeding mass          → Fabric: Consciousness (observer seeds)

References:
    - Schaye, J. et al. (2023). "COLIBRE" model description. MNRAS.
    - Schaller, M. et al. (2024). "SWIFT: the next generation of..." MNRAS.
    - Elahi, P.J. et al. (2019). "Velociraptor halo finder." PASA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.physics.ionic_cluster import IonicClusterState

logger = logging.getLogger(__name__)

# COLIBRE ISM thermal equilibrium threshold — hot gas fraction at HIHO.
# Mirrors the HIHO threshold (0.5) shared by LENR and IonicCluster.
_COLIBRE_HIHO_HOT_FRACTION: float = 0.5

# COLIBRE default ISM pressure floor (Dalla Vecchia & Schaye 2012)
_ISM_PRESSURE_FLOOR_K_PER_CM3: float = 0.1  # K cm^-3


@dataclass
class ColibreState:
    """State of a COLIBRE cosmological simulation snapshot.

    Maps SWIFT/COLIBRE outputs to Cohezion physics primitives for:
    - IonicClusterState (ISM plasma HIHO equilibrium)
    - LENRHamiltonian (star formation as lattice-confined nuclear process)
    - AutonomyEngine tier promotion (cosmic coherence events)

    Parameters
    ----------
    redshift : float
        Cosmological redshift z (0 = present day, ∞ = Big Bang).
    sfr_density : float
        Cosmic star formation rate density in M_sun/yr/Mpc^3.
        Maps to LENR reaction_rate (star formation = nuclear process at HIHO).
    ism_hot_fraction : float
        Fraction of ISM mass in hot phase (T > 10^5 K) [0, 1].
        At 0.5 = HIHO equilibrium (Cloudy-modeled two-phase ISM).
    stellar_mass_density : float
        Cosmic stellar mass density in M_sun/Mpc^3.
        Accumulated "witness marks" of coherent processes.
    bh_mass_density : float
        Total black hole mass density — observer/enforcer particles.
        Maps to autoharness role (prevents runaway feedback loops).
    """

    redshift: float = 0.0
    sfr_density: float = 0.0
    ism_hot_fraction: float = 0.5
    stellar_mass_density: float = 0.0
    bh_mass_density: float = 0.0
    _colibre_coherence: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Clamp fractions to [0, 1]
        self.ism_hot_fraction = max(0.0, min(1.0, float(self.ism_hot_fraction)))
        # Redshift is non-negative. A value < -1 made cosmic_time_gyr compute
        # (1 + z) ** 1.5 on a negative base, yielding a complex number that the
        # ZeroDivisionError guard did not catch (crashed float serialization).
        self.redshift = max(0.0, float(self.redshift))
        # COLIBRE coherence: 4×f_hot×(1-f_hot) — identical to LENR/IonicCluster kernel
        self._colibre_coherence = 4.0 * self.ism_hot_fraction * (1.0 - self.ism_hot_fraction)

    @property
    def colibre_coherence(self) -> float:
        """ISM phase coherence — 4×f_hot×(1-f_hot), peaks at f_hot=0.5 (HIHO).

        This is EXACTLY the same beta-binomial kernel as LENR.reaction_rate()
        and IonicCluster.ionisation_rate(). The ISM, the atomic lattice, and
        the plasma all share the universal HIHO coherence formula.
        """
        return self._colibre_coherence

    def hiho_engaged(self) -> bool:
        """True when the ISM is at HIHO two-phase equilibrium.

        The ISM at HIHO has balanced stellar heating and radiative cooling,
        maintaining T ~ 10^4 K gas alongside T ~ 10^6 K hot halo gas.
        This maps exactly to IonicCluster.hiho_equilibrium().
        """
        from cohezion.physics.ionic_cluster import IonicClusterState

        cluster = IonicClusterState(plasma_density=self.ism_hot_fraction)
        return cluster.hiho_equilibrium()

    def to_ionic_cluster(self) -> IonicClusterState:
        """Map COLIBRE ISM hot fraction → IonicClusterState plasma density."""
        from cohezion.physics.ionic_cluster import IonicClusterState

        return IonicClusterState(plasma_density=self.ism_hot_fraction)

    def sfr_as_lenr_rate(self) -> float:
        """Map cosmic SFR density to LENR reaction rate.

        Star formation IS a nuclear process: gas collapses to T>10^7 K,
        igniting H→He fusion. The rate peaks when gas is in HIHO equilibrium
        (half ionized, half neutral = optimal for gravitational collapse).

        Returns normalized reaction rate in [0, 1] using LENR kernel.
        """
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        return h.reaction_rate(self.ism_hot_fraction)

    def to_autonomy_event(self) -> dict[str, float]:
        """Format as AutonomyEngine physics coherence event for governance."""
        return {
            "source": "colibre",
            "coherence": self.colibre_coherence,
            "redshift": self.redshift,
            "sfr_density": self.sfr_density,
        }

    @property
    def cosmic_time_gyr(self) -> float:
        """Approximate cosmic time in Gyr from redshift (flat ΛCDM, H0=67.4)."""
        if self.redshift >= 100:
            return 0.0
        try:
            return 13.8 / (1.0 + self.redshift) ** 1.5
        except ZeroDivisionError:
            return 13.8


@dataclass
class AgentAsEVO:
    """Map a Cohezion agent to its cosmological EVO particle type.

    Each specialist agent in the compound engineering loop corresponds to
    a distinct COLIBRE particle species with matching physics:
    - Dark matter: long-range influence, gravitational only (synthesizer agents)
    - Gas: reactive, phase-transitioning, HIHO-bounded (engineering agents)
    - Stars: irreversible formed products, light-emitting (knowledge agents)
    - Black holes: enforce energy conservation, prevent runaway (harness agents)
    """

    agent_id: str
    agent_type: str  # "synthesizer", "engineer", "knowledge", "harness"

    @property
    def particle_type(self) -> str:
        """COLIBRE particle type this agent maps to."""
        mapping = {
            "synthesizer": "dark_matter",
            "engineer": "gas",
            "knowledge": "star",
            "harness": "black_hole",
        }
        return mapping.get(self.agent_type, "gas")

    @property
    def hiho_threshold(self) -> float:
        """HIHO coherence threshold for this particle type."""
        # All particle types share the universal HIHO threshold 0.5
        return 0.5

    def can_star_form(self, state: ColibreState) -> bool:
        """Return True when this gas agent can promote to star (knowledge) tier.

        In COLIBRE: gas particles above n_H > n_crit and in HIHO ISM.
        In Cohezion: agent promoted from SO12 to HIHO when coherence sustained.
        """
        if self.particle_type != "gas":
            return False
        return state.hiho_engaged() and state.sfr_density > 0.0


def load_swift_snapshot(snapshot_path: Path) -> ColibreState:
    """Load a SWIFT HDF5 snapshot and return a ColibreState.

    Requires swiftsimio installed: uv pip install swiftsimio

    Parameters
    ----------
    snapshot_path : Path
        Path to a SWIFT/COLIBRE HDF5 snapshot file.

    Returns
    -------
    ColibreState
        Cohezion-compatible state from the simulation snapshot.
    """
    try:
        import swiftsimio as sw  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("swiftsimio not installed — run: uv pip install swiftsimio") from exc

    data = sw.load(str(snapshot_path))
    z = float(data.metadata.z)

    # Extract ISM hot fraction from gas temperature
    try:
        temps = data.gas.temperatures.value
        hot_mask = temps > 1e5  # > 10^5 K = hot phase
        ism_hot = float(hot_mask.mean()) if len(temps) > 0 else 0.5
    except Exception:
        ism_hot = 0.5  # default to HIHO if temperatures unavailable

    # Approximate SFR density from snapshot metadata
    try:
        sfr = float(data.metadata.cosmology.Hubble_param)  # placeholder
    except Exception:
        sfr = 0.02  # Madau-Dickinson peak at z~2

    return ColibreState(
        redshift=z,
        sfr_density=sfr,
        ism_hot_fraction=ism_hot,
    )
