import numpy as np
import pytest
import torch

from cohezion.model.cohezion_evo_model import (
    CampbellNegentropyLoss,
    CohezionEVOModel,
    EVOAutoHarnessVerifier,
    EVOSolitonTokenizer,
    FLUME12DState,
    GeodesicFlowNeuralODE,
    MarkovStateMonad,
)


def test_flume_12d_state_packing():
    state = FLUME12DState(
        spatial=[1.0, 2.0, 3.0],
        temporal=20.0,
        brane=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    )
    vec = state.to_vector()
    assert len(vec) == 12
    assert vec[3] == 20.0

    unpacked = FLUME12DState.from_vector(vec)
    assert unpacked.spatial == [1.0, 2.0, 3.0]
    assert unpacked.temporal == 20.0
    assert len(unpacked.brane) == 8


def test_evo_soliton_tokenizer_poincare_projection():
    tokenizer = EVOSolitonTokenizer(codebook_size=32, embedding_dim=12)
    # Test batch with out-of-bounds coordinates
    large_batch = torch.randn(4, 12) * 5.0
    projected = tokenizer.project_poincare(large_batch)
    norms = torch.norm(projected, dim=-1)
    assert torch.all(norms < 1.0)

    quantized, token_ids, vq_loss = tokenizer(large_batch)
    assert quantized.shape == (4, 12)
    assert len(token_ids) == 4
    assert vq_loss.item() >= 0.0


def test_geodesic_flow_neural_ode_hiho_050():
    flow = GeodesicFlowNeuralODE(state_dim=12, hidden_dim=32)
    z0 = torch.randn(2, 12) * 0.2
    z_next, flow_residual = flow.step_hiho_050(z0, dt=0.05)

    assert z_next.shape == (2, 12)
    assert flow_residual.shape == (2, 12)
    # Brane dimensions must remain inside Poincaré ball
    brane_norms = torch.norm(z_next[..., 4:12], dim=-1)
    assert torch.all(brane_norms < 1.0)


def test_markov_state_monad_retrospection():
    monad = MarkovStateMonad(transition_kernel_dim=12)
    start_state = FLUME12DState(spatial=[0.1, 0.2, 0.3], temporal=0.0, brane=[0.5] * 8)

    res = monad.transition(start_state, "OBSERVE_STABILITY")
    assert res.value == "OBSERVE_STABILITY"
    assert len(res.trace) == 1
    assert "pre_state" in res.trace[0]
    assert "post_state" in res.trace[0]
    assert res.trace[0]["action"] == "GEODESIC_ADVANCE"


def test_campbell_negentropy_loss():
    loss_fn = CampbellNegentropyLoss()
    task_loss = torch.tensor(0.5)
    traj = torch.randn(2, 8, 12)
    residuals = torch.randn(2, 8, 12) * 0.05
    ds_dt = torch.tensor([-0.1, -0.2])  # Negentropic: dS/dt <= 0

    total_loss, metrics = loss_fn(task_loss, traj, residuals, ds_dt)
    assert total_loss.item() > 0.0
    assert metrics["negentropy_loss"] >= 0.0
    assert "delta_s" in metrics


def test_cohezion_evo_model_full_rollout_and_proof():
    model = CohezionEVOModel(codebook_size=64, hidden_dim=32)
    start_state = FLUME12DState(spatial=[0.0, 0.0, 0.0], temporal=0.0, brane=[0.5] * 8)

    final_state, proof, telemetry = model.execute_and_verify(start_state, steps=4)

    assert isinstance(final_state, FLUME12DState)
    assert len(proof.model_bytecode_hash) == 64
    assert len(proof.trajectory_polynomial_root) == 64
    assert "initial_entropy" in telemetry
    assert "final_entropy" in telemetry
    assert len(telemetry["monad_trace"]) == 1
