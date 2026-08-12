import pytest
import numpy as np
from cohezion.flume.jacobian_workspace_engine import JacobianWorkspaceEngine, WorkspaceState


def test_jacobian_workspace_readout():
    engine = JacobianWorkspaceEngine(vocab_size=1000, model_dim=512)
    vec = np.random.randn(512)

    state_mid = engine.compute_j_lens_readout(vec, layer_depth=0.50, top_k=5)
    assert isinstance(state_mid, WorkspaceState)
    assert state_mid.is_workspace_active is True
    assert len(state_mid.active_concepts) == 5
    assert state_mid.j_space_variance_ratio == 0.08

    state_early = engine.compute_j_lens_readout(vec, layer_depth=0.10)
    assert state_early.is_workspace_active is False
    assert state_early.j_space_variance_ratio == 0.01


def test_workspace_steering():
    engine = JacobianWorkspaceEngine(vocab_size=1000, model_dim=512)
    vec = np.random.randn(512)

    steered_vec = engine.steer_workspace(vec, concept_token_id=42, steering_coefficient=5.0)
    assert not np.array_equal(vec, steered_vec)
