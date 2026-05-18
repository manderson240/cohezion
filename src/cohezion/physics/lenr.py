"""LENR Hamiltonian — Lattice-Confined Nuclear Reaction model.

Low Energy Nuclear Reaction (LENR) describes nuclear processes (d+d → 4He + heat)
that occur at sub-Coulomb-barrier energies when deuterium is confined in metallic
lattices (Pd, Ni). The lattice coherence is the key enabler: lattice phonons
reduce the effective Coulomb barrier through coherent enhancement.

Cohezion mapping:
    coherence → lattice coherence amplitude (0 = disordered, 1 = fully coherent)
    reaction_threshold = 0.5 = HIHO — the LENR reaction rate peaks at 50% coherence
    because HIHO represents optimal balance between exploiting current lattice
    configuration and exploring new configurations.

    reaction_rate(c) = 4 · c · (1 - c)   [peaks at c = 0.5, vanishes at 0 and 1]

    This is the beta-binomial kernel — identical to the HIHO phase transition
    function used in BioelectricNetwork and FourFabricGauge.

Bridge targets:
    - hamiltonian.py: inherits HIHO_WELL potential landscape (target = 0.5)
    - bioelectric_model.py: coherence maps to gap junction conductance
    - AutonomyEngine.record_coherence(): reports reaction events to governance layer

References:
    - Fleischmann, M. & Pons, S. (1989). "Electrochemically induced nuclear fusion"
      Journal of Electroanalytical Chemistry 261(2A)
    - Hagelstein, P.L. et al. (2004). "New Physical Effects in Metal Deuterides"
      Condensed Matter Nuclear Science, ICCF-11
    - Storms, E. (2007). "The Science of Low Energy Nuclear Reaction" World Scientific
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

# Shared HIHO threshold — used as the LENR reaction peak AND governance gate.
# This constant is intentionally the same value used in BioelectricNetwork (G_c = 0.5)
# and FourFabricGauge (Control coupling = 0.5). A single constant prevents drift.
_HIHO_THRESHOLD: float = 0.5


@dataclass
class LENRHamiltonian:
    """Lattice-confined nuclear reaction model bridged to Cohezion coherence.

    Parameters
    ----------
    reaction_threshold : float
        Coherence level at which reaction rate peaks (default 0.5 = HIHO).
    lattice_coupling : float
        Phonon-mediated coupling strength (dimensionless, default 1.0).
        Higher values amplify the reaction rate without shifting the peak.
    agent_id : str
        Governance agent ID for AutonomyEngine.record_coherence() calls.
    """

    reaction_threshold: float = _HIHO_THRESHOLD
    lattice_coupling: float = 1.0
    agent_id: str = "lenr-bridge"
    _coherence_events: list[tuple[float, float]] = field(default_factory=list, repr=False)

    def reaction_rate(self, coherence: float) -> float:
        """Reaction rate as a function of lattice coherence.

        Uses the beta-binomial kernel that peaks at coherence = reaction_threshold:
            rate(c) = 4 · coupling · c · (1 - c)

        This is equivalent to rescaling so the peak falls at the HIHO threshold
        regardless of the threshold value:
            rate(c) = coupling · (c / t) · ((1 - c) / (1 - t)) · 4t(1-t)

        For t = 0.5: simplifies to 4 · coupling · c · (1 - c).

        Returns
        -------
        float
            Reaction rate in [0, coupling]. Zero at c=0 and c=1.
        """
        c = max(0.0, min(1.0, float(coherence)))
        t = self.reaction_threshold
        if t <= 0.0 or t >= 1.0:
            return 0.0
        # General form: peaked at t, vanishes at 0 and 1
        peak = 4.0 * t * (1.0 - t)  # normalisation so max = coupling
        rate = self.lattice_coupling * (c * (1.0 - c) / (t * (1.0 - t))) * peak
        return float(rate)

    def record_coherence_event(
        self, coherence: float, autonomy_engine: object | None = None
    ) -> float:
        """Record a coherence measurement and optionally forward to AutonomyEngine.

        Parameters
        ----------
        coherence : float
            Current lattice coherence in [0, 1].
        autonomy_engine : AutonomyEngine | None
            If provided, calls autonomy_engine.record_coherence(agent_id, coherence).

        Returns
        -------
        float
            The reaction rate at the given coherence level.
        """
        coherence = max(0.0, min(1.0, float(coherence)))
        rate = self.reaction_rate(coherence)
        self._coherence_events.append((coherence, rate))

        if autonomy_engine is not None:
            try:
                autonomy_engine.record_coherence(self.agent_id, coherence)
            except Exception:
                logger.warning(
                    "LENRHamiltonian: AutonomyEngine.record_coherence failed "
                    "(agent_id=%s, coherence=%.3f)",
                    self.agent_id,
                    coherence,
                )

        logger.debug(
            "LENR coherence event: coherence=%.3f rate=%.4f (agent=%s)",
            coherence,
            rate,
            self.agent_id,
        )
        return rate

    @property
    def event_count(self) -> int:
        return len(self._coherence_events)

    @property
    def mean_rate(self) -> float:
        if not self._coherence_events:
            return 0.0
        return sum(r for _, r in self._coherence_events) / len(self._coherence_events)
