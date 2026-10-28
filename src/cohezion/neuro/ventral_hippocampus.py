"""Ventral Hippocampus (vHPC) Affective-Motivational Circuit Architecture.

Based on Biane, Wagner-Carena & Kheirbek (Nature Reviews Neuroscience, 2026):
"The ventral hippocampus: computations, circuits and functions".

Contrasts dorsal hippocampal (dHPC) spatial/metric mapping with ventral hippocampal
(vHPC) affective-motivational manifold computations. Computes state-dependent routing
across projection targets:
- Basolateral Amygdala (BLA): Valence tagging, fear/threat plasticity, signed error.
- Medial Prefrontal Cortex (mPFC): Contextual cognitive control, conflict arbitration.
- Nucleus Accumbens (NAc): Incentive salience, reward expectation, exploration vigor.
- Hypothalamus (LH/PVN): Autonomic arousal, stress response, resource throttling.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


class HippocampalAxis(StrEnum):
    """Functional subdivision along the longitudinal hippocampal axis."""

    DORSAL = "dorsal"  # High-precision Euclidean metric maps, spatial navigation, AST geometry
    INTERMEDIATE = "intermediate"  # Behavioral transition zone, context-space integration
    VENTRAL = "ventral"  # Low-precision spatial, high-dimensional affective-motivational manifold


class VentralProjectionTarget(StrEnum):
    """Downstream projection-defined recipient structures of the ventral hippocampus."""

    BLA = "basolateral_amygdala"  # Valence assignment, associative plasticity, signed error
    MPFC = "medial_prefrontal_cortex"  # Cognitive control, conflict arbitration, policy priors
    NAC = "nucleus_accumbens"  # Incentive salience, reward anticipation, exploratory vigor
    HYPOTHALAMUS = "hypothalamus"  # Autonomic arousal, metabolic homeostasis, resource throttle


class VentralBehavioralMode(StrEnum):
    """Behavioral and architectural execution regimes output by the vHPC circuit."""

    MOTIVATED_EXPLORATION = "motivated_exploration"  # High reward expectancy, active tier dispatch
    DEFENSIVE_CONSOLIDATION = "defensive_consolidation"  # High threat/uncertainty, formal ZKFV gate
    MPFC_ARBITRATION = "mpfc_arbitration"  # Approach-avoidance conflict, consensus deliberation
    SAFE_AVOIDANCE = "safe_avoidance"  # Unfavorable expected value, defensive fallback


@dataclass
class VentralHippocampalState:
    """Snapshot representation of the ventral hippocampal manifold and routing state."""

    spatial_dim: int
    interoceptive_energy: float  # [0.0, 1.0] Available system energy/resources
    interoceptive_stress: float  # [0.0, 1.0] Resource pressure / error accumulation
    affective_vector: list[float]  # Fused spatial + interoceptive latent vector
    latent_belief: dict[str, float]  # Probability distribution over inferred latent contexts
    uncertainty_entropy: float  # Shannon entropy over latent context states
    approach_valence: float  # Expected reward / incentive value
    avoidance_valence: float  # Expected cost / threat / error risk
    conflict_signal: float  # c = V_app - V_avoid
    target_weights: dict[str, float]  # Softmax-modulated or gated output distribution
    mode: VentralBehavioralMode


class VentralHippocampusCircuit:
    """Ventral Hippocampal Affective-Motivational Mapping and Circuit Routing Engine.

    Operationalizes empirical discoveries from Biane et al. (2026) for autonomous AI agents:
    1. Fuses spatial/syntactic state with internal interoceptive/system metrics into an
       affective-motivational manifold vector.
    2. Performs recursive Bayesian hidden-state inference to resolve ambiguous task contexts.
    3. Solves approach-avoidance conflict and routes gating signals deterministically to
       BLA, mPFC, NAc, and Hypothalamus analogs.
    """

    LATENT_STATES = ["SAFE_EXPLOIT", "AMBIGUOUS_CONFLICT", "HIGH_THREAT_RISK"]

    def __init__(
        self,
        spatial_dim: int = 12,
        conflict_sensitivity: float = 2.0,
        surreal_client: SurrealClient | None = None,
    ) -> None:
        """Initialize the Ventral Hippocampus Circuit.

        Parameters
        ----------
        spatial_dim : int, default=12
            Dimensionality of the input spatial/state vector (matches FLUME 12D manifold).
        conflict_sensitivity : float, default=2.0
            Scaling parameter kappa for sigmoidal approach-avoidance conflict gating.
        surreal_client : SurrealClient | None
            SurrealDB persistence client for recording neuron/synapse topologies.
        """
        self.spatial_dim = spatial_dim
        self.conflict_sensitivity = conflict_sensitivity
        self.client = surreal_client

        # Latent state prior: uniform initialization
        n_states = len(self.LATENT_STATES)
        self.belief = dict.fromkeys(self.LATENT_STATES, 1.0 / n_states)

        # Transition matrix between latent states (prior probability of remaining or switching)
        self.transition_matrix = np.array(
            [
                [0.85, 0.10, 0.05],  # From SAFE_EXPLOIT
                [0.20, 0.60, 0.20],  # From AMBIGUOUS_CONFLICT
                [0.05, 0.15, 0.80],  # From HIGH_THREAT_RISK
            ]
        )

        # Projection weight seeds for downstream channels
        # Shape: (4 targets, spatial_dim + 2 interoceptive dims)
        rng = np.random.default_rng(seed=20260911)
        self.w_proj = rng.normal(0.0, 0.25, size=(4, spatial_dim + 2))

    def compute_affective_vector(
        self,
        spatial_coordinates: list[float] | np.ndarray,
        interoceptive_energy: float = 0.8,
        interoceptive_stress: float = 0.2,
    ) -> np.ndarray:
        """Fuses spatial coordinates with interoceptive internal state into a manifold vector.

        Unlike dHPC which maintains purely spatial metric coordinates, vHPC computes
        a state-dependent representation combining external location/context with internal
        arousal and physiological state.

        Parameters
        ----------
        spatial_coordinates : list[float] | np.ndarray
            Spatial or task coordinate vector (e.g. 12D Poincaré embedding).
        interoceptive_energy : float
            Internal resource level [0.0, 1.0].
        interoceptive_stress : float
            Internal stress / error rate / resource depletion [0.0, 1.0].

        Returns
        -------
        np.ndarray
            Fused affective-motivational manifold vector.
        """
        s_vec = np.asarray(spatial_coordinates, dtype=np.float64)
        if len(s_vec) < self.spatial_dim:
            padded = np.zeros(self.spatial_dim, dtype=np.float64)
            padded[: len(s_vec)] = s_vec
            s_vec = padded
        elif len(s_vec) > self.spatial_dim:
            s_vec = s_vec[: self.spatial_dim]

        intero = np.array([float(interoceptive_energy), float(interoceptive_stress)])
        fused = np.concatenate([s_vec, intero])
        # Non-linear hyperbolic tangent compression preserving metric boundaries while weighting affect
        affective_v = np.tanh(fused)
        return affective_v

    def infer_latent_context(
        self,
        observation_likelihoods: dict[str, float],
    ) -> tuple[dict[str, float], float]:
        """Performs Bayesian hidden-state inference to infer latent task context.

        vHPC ensembles encode abstract task states and contextual contingencies that are
        not directly observable from sensory features alone.

        Parameters
        ----------
        observation_likelihoods : dict[str, float]
            Likelihoods P(Observation | Latent State) for each latent state.

        Returns
        -------
        tuple[dict[str, float], float]
            Updated belief distribution P(z | O) and Shannon entropy (uncertainty).
        """
        prior_vec = np.array([self.belief[s] for s in self.LATENT_STATES])
        # Prior propagation through transition matrix
        predicted_prior = self.transition_matrix.T @ prior_vec

        # Evidence update
        likelihood_vec = np.array(
            [max(1e-6, observation_likelihoods.get(s, 0.33)) for s in self.LATENT_STATES]
        )
        unnormalized_posterior = predicted_prior * likelihood_vec
        total_evidence = float(np.sum(unnormalized_posterior))

        if total_evidence > 0.0:
            posterior_vec = unnormalized_posterior / total_evidence
        else:
            posterior_vec = np.ones(len(self.LATENT_STATES)) / len(self.LATENT_STATES)

        self.belief = {state: float(posterior_vec[i]) for i, state in enumerate(self.LATENT_STATES)}

        # Calculate Shannon entropy (uncertainty metric U_t)
        entropy = -float(np.sum([p * math.log2(p) if p > 1e-9 else 0.0 for p in posterior_vec]))

        return dict(self.belief), entropy

    def arbitrate_approach_avoidance(
        self,
        reward_expectation: float,
        threat_risk: float,
        uncertainty_entropy: float = 0.0,
    ) -> tuple[VentralBehavioralMode, dict[str, float], float]:
        """Resolves approach-avoidance conflict and routes gating signals to downstream targets.

        Mathematical model:
        c = V_app - V_avoid
        g = sigma(kappa * c)
        NAc (approach vigor): gamma_NAc = g * (1 - 0.4 * U_t)
        Hyp (visceral throttle): gamma_Hyp = (1 - g) + 0.4 * U_t
        BLA (unsigned valence update): gamma_BLA = |c|
        mPFC (cognitive control): gamma_mPFC = sigma(abs(c) * 2.0)

        Parameters
        ----------
        reward_expectation : float
            Anticipated reward or goal progress value [0.0, 1.0].
        threat_risk : float
            Anticipated failure penalty, error risk, or uncertainty [0.0, 1.0].
        uncertainty_entropy : float
            Current hidden-state entropy U_t.

        Returns
        -------
        tuple[VentralBehavioralMode, dict[str, float], float]
            Selected behavioral mode, downstream target activations, and raw conflict c.
        """
        c = float(reward_expectation - threat_risk)
        kappa = self.conflict_sensitivity

        # Gating factor via logistic sigmoid
        g = 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, kappa * c))))

        # Normalized uncertainty factor in [0, 1]
        norm_u = min(1.0, uncertainty_entropy / 1.585)  # log2(3) approx 1.585

        # Downstream pathway routing signals
        gamma_nac = max(0.0, min(1.0, g * (1.0 - 0.4 * norm_u)))
        gamma_hyp = max(0.0, min(1.0, (1.0 - g) + 0.4 * norm_u))
        gamma_bla = max(0.0, min(1.0, abs(c)))
        gamma_mpfc = max(0.0, min(1.0, 1.0 / (1.0 + math.exp(-2.0 * abs(c)))))

        targets = {
            VentralProjectionTarget.NAC.value: float(gamma_nac),
            VentralProjectionTarget.HYPOTHALAMUS.value: float(gamma_hyp),
            VentralProjectionTarget.BLA.value: float(gamma_bla),
            VentralProjectionTarget.MPFC.value: float(gamma_mpfc),
        }

        # Behavioral regime arbitration
        if threat_risk > 0.75 or norm_u > 0.70:
            mode = VentralBehavioralMode.DEFENSIVE_CONSOLIDATION
        elif abs(c) < 0.20 and (reward_expectation > 0.35 and threat_risk > 0.35):
            mode = VentralBehavioralMode.MPFC_ARBITRATION
        elif c > 0.20:
            mode = VentralBehavioralMode.MOTIVATED_EXPLORATION
        else:
            mode = VentralBehavioralMode.SAFE_AVOIDANCE

        return mode, targets, c

    def process_step(
        self,
        spatial_coordinates: list[float] | np.ndarray,
        interoceptive_energy: float = 0.8,
        interoceptive_stress: float = 0.2,
        observation_likelihoods: dict[str, float] | None = None,
        reward_expectation: float = 0.5,
        threat_risk: float = 0.3,
    ) -> VentralHippocampalState:
        """Executes a full cycle through the ventral hippocampal circuit.

        Parameters
        ----------
        spatial_coordinates : list[float] | np.ndarray
            Spatial/task embedding vector.
        interoceptive_energy : float
            Available energy / compute margin [0.0, 1.0].
        interoceptive_stress : float
            Resource pressure / error frequency [0.0, 1.0].
        observation_likelihoods : dict[str, float] | None
            Observations for latent state inference. Defaults to neutral.
        reward_expectation : float
            Estimated value of pending action [0.0, 1.0].
        threat_risk : float
            Estimated risk or failure consequence [0.0, 1.0].

        Returns
        -------
        VentralHippocampalState
            Full circuit output state ready for agent dispatch or database persistence.
        """
        if observation_likelihoods is None:
            observation_likelihoods = dict.fromkeys(self.LATENT_STATES, 0.33)

        affective_v = self.compute_affective_vector(
            spatial_coordinates, interoceptive_energy, interoceptive_stress
        )

        belief, entropy = self.infer_latent_context(observation_likelihoods)

        mode, targets, conflict = self.arbitrate_approach_avoidance(
            reward_expectation=reward_expectation,
            threat_risk=threat_risk,
            uncertainty_entropy=entropy,
        )

        return VentralHippocampalState(
            spatial_dim=self.spatial_dim,
            interoceptive_energy=interoceptive_energy,
            interoceptive_stress=interoceptive_stress,
            affective_vector=[float(x) for x in affective_v],
            latent_belief=belief,
            uncertainty_entropy=entropy,
            approach_valence=reward_expectation,
            avoidance_valence=threat_risk,
            conflict_signal=conflict,
            target_weights=targets,
            mode=mode,
        )

    async def persist_circuit_state(
        self,
        state: VentralHippocampalState,
        step_id: str = "v_step_latest",
    ) -> dict[str, int]:
        """Asynchronously records circuit state and projection synapses into SurrealDB.

        Parameters
        ----------
        state : VentralHippocampalState
            State snapshot to persist.
        step_id : str
            Unique identifier for the step.

        Returns
        -------
        dict[str, int]
            Count of seeded neurons and projection synapses.
        """
        if not self.client:
            logger.debug("SurrealClient not connected; skipping persistence.")
            return {"neurons_seeded": 0, "synapses_seeded": 0}

        # Persist the vHPC hub node
        q_hub = (
            f"UPSERT neuron:`vhpc_hub_{step_id}` SET "
            f"title = 'Ventral Hippocampus Hub', "
            f"tier = '{HippocampalAxis.VENTRAL.value}', "
            f"region = 'limbic_ventral_cortex', "
            f"mode = '{state.mode.value}', "
            f"conflict = {state.conflict_signal}, "
            f"uncertainty = {state.uncertainty_entropy}, "
            f"updated_at = time::now();"
        )
        try:
            await self.client.query(q_hub)
        except Exception as e:
            logger.warning("Failed to persist vHPC hub: %s", e)
            return {"neurons_seeded": 0, "synapses_seeded": 0}

        # Persist projection synapses to the 4 targets
        synapses_count = 0
        for target, weight in state.target_weights.items():
            edge_id = f"syn_vhpc_{target}_{step_id}".replace(":", "_")
            q_edge = (
                f"RELATE neuron:`vhpc_hub_{step_id}`->synapse:`{edge_id}`->neuron:`{target}` SET "
                f"weight = {weight}, "
                f"target_structure = '{target}', "
                f"created_at = time::now();"
            )
            try:
                await self.client.query(q_edge)
                synapses_count += 1
            except Exception as e:
                logger.warning("Failed to relate vHPC projection to %s: %s", target, e)

        return {"neurons_seeded": 1, "synapses_seeded": synapses_count}
