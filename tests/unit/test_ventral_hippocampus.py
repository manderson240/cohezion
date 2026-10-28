"""Unit tests for the Ventral Hippocampus (vHPC) Affective-Motivational Circuit.

Based on Biane, Wagner-Carena & Kheirbek (Nature Reviews Neuroscience, 2026).
"""

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from cohezion.neuro.ventral_hippocampus import (
    HippocampalAxis,
    VentralBehavioralMode,
    VentralHippocampalState,
    VentralHippocampusCircuit,
    VentralProjectionTarget,
)


def test_ventral_hippocampal_enums():
    assert HippocampalAxis.VENTRAL == "ventral"
    assert HippocampalAxis.DORSAL == "dorsal"
    assert VentralProjectionTarget.BLA == "basolateral_amygdala"
    assert VentralProjectionTarget.MPFC == "medial_prefrontal_cortex"
    assert VentralProjectionTarget.NAC == "nucleus_accumbens"
    assert VentralProjectionTarget.HYPOTHALAMUS == "hypothalamus"
    assert VentralBehavioralMode.MOTIVATED_EXPLORATION == "motivated_exploration"


def test_compute_affective_vector():
    circuit = VentralHippocampusCircuit(spatial_dim=12)
    spatial_coords = [0.5] * 12
    affective_v = circuit.compute_affective_vector(
        spatial_coordinates=spatial_coords,
        interoceptive_energy=0.9,
        interoceptive_stress=0.1,
    )

    assert isinstance(affective_v, np.ndarray)
    assert len(affective_v) == 14  # 12 spatial + 2 interoceptive
    # All values compressed by tanh into [-1.0, 1.0]
    assert np.all(affective_v >= -1.0)
    assert np.all(affective_v <= 1.0)


def test_compute_affective_vector_padding_and_truncation():
    circuit = VentralHippocampusCircuit(spatial_dim=12)

    # Short input (padded to 12)
    short_coords = [0.2, 0.4]
    v_short = circuit.compute_affective_vector(short_coords)
    assert len(v_short) == 14

    # Long input (truncated to 12)
    long_coords = [0.1] * 20
    v_long = circuit.compute_affective_vector(long_coords)
    assert len(v_long) == 14


def test_infer_latent_context():
    circuit = VentralHippocampusCircuit()

    # Initial prior is uniform
    math_close = pytest.approx(1.0 / 3.0, abs=1e-3)
    for p in circuit.belief.values():
        assert p == math_close

    # Strong evidence for HIGH_THREAT_RISK
    obs = {"SAFE_EXPLOIT": 0.05, "AMBIGUOUS_CONFLICT": 0.15, "HIGH_THREAT_RISK": 0.90}
    posterior, entropy = circuit.infer_latent_context(obs)

    assert posterior["HIGH_THREAT_RISK"] > posterior["SAFE_EXPLOIT"]
    assert pytest.approx(sum(posterior.values()), abs=1e-5) == 1.0
    assert entropy >= 0.0


def test_arbitrate_approach_avoidance_regimes():
    circuit = VentralHippocampusCircuit(conflict_sensitivity=2.0)

    # 1. Motivated exploration (high reward, low risk)
    mode, targets, c = circuit.arbitrate_approach_avoidance(
        reward_expectation=0.85, threat_risk=0.15, uncertainty_entropy=0.2
    )
    assert mode == VentralBehavioralMode.MOTIVATED_EXPLORATION
    assert c > 0.5
    assert (
        targets[VentralProjectionTarget.NAC.value]
        > targets[VentralProjectionTarget.HYPOTHALAMUS.value]
    )

    # 2. Defensive consolidation (high threat)
    mode_def, targets_def, _ = circuit.arbitrate_approach_avoidance(
        reward_expectation=0.2, threat_risk=0.85, uncertainty_entropy=0.5
    )
    assert mode_def == VentralBehavioralMode.DEFENSIVE_CONSOLIDATION
    assert (
        targets_def[VentralProjectionTarget.HYPOTHALAMUS.value]
        > targets_def[VentralProjectionTarget.NAC.value]
    )

    # 3. mPFC arbitration (balanced conflict)
    mode_arb, _, _ = circuit.arbitrate_approach_avoidance(
        reward_expectation=0.70, threat_risk=0.68, uncertainty_entropy=0.3
    )
    assert mode_arb == VentralBehavioralMode.MPFC_ARBITRATION


def test_process_step_end_to_end():
    circuit = VentralHippocampusCircuit(spatial_dim=12)
    state = circuit.process_step(
        spatial_coordinates=[0.1 * i for i in range(12)],
        interoceptive_energy=0.8,
        interoceptive_stress=0.2,
        observation_likelihoods={
            "SAFE_EXPLOIT": 0.7,
            "AMBIGUOUS_CONFLICT": 0.2,
            "HIGH_THREAT_RISK": 0.1,
        },
        reward_expectation=0.75,
        threat_risk=0.20,
    )

    assert isinstance(state, VentralHippocampalState)
    assert len(state.affective_vector) == 14
    assert state.mode == VentralBehavioralMode.MOTIVATED_EXPLORATION
    assert state.conflict_signal == pytest.approx(0.55, abs=1e-4)
    assert VentralProjectionTarget.BLA.value in state.target_weights
    assert VentralProjectionTarget.MPFC.value in state.target_weights


@pytest.mark.asyncio
async def test_persist_circuit_state():
    mock_client = MagicMock()
    mock_client.query = AsyncMock(return_value=[{"result": []}])

    circuit = VentralHippocampusCircuit(surreal_client=mock_client)
    state = circuit.process_step(
        spatial_coordinates=[0.5] * 12,
        reward_expectation=0.6,
        threat_risk=0.3,
    )

    counts = await circuit.persist_circuit_state(state, step_id="test_step_001")
    assert counts["neurons_seeded"] == 1
    assert counts["synapses_seeded"] == 4  # 4 projection targets (BLA, mPFC, NAc, Hyp)
    # Hub UPSERT + 4 target RELATE calls
    assert mock_client.query.call_count == 5
