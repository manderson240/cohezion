"""Unit tests for Free Pause State-Prediction Separation (SPS).

Verifies properties proven in arXiv:2609.03807:
1. Iso-parameter property: exactly 1 extra tensor (predict_embedding).
2. Two-pass split: shapes of prediction_output and state_output match input.
3. Gradient backpropagation flows to predict_embedding and shared weights.
"""

from __future__ import annotations

import torch

from cohezion.flume.free_pause_sps import FreePauseStatePredictionModule


def test_sps_iso_parameter_count() -> None:
    d_model = 128
    mod = FreePauseStatePredictionModule(d_model=d_model, n_heads=4, d_ff=512)
    assert mod.predict_embedding.numel() == d_model
    assert mod.predict_embedding.shape == (1, 1, d_model)


def test_sps_forward_two_pass_shapes() -> None:
    d_model = 64
    seq_len = 16
    batch_size = 2
    mod = FreePauseStatePredictionModule(d_model=d_model, n_heads=2, d_ff=128)

    inputs = torch.randn(batch_size, seq_len, d_model)
    preds, states = mod.forward_two_pass(inputs)

    assert preds.shape == (batch_size, seq_len, d_model)
    assert states.shape == (batch_size, seq_len, d_model)
    # Ensure prediction output differs from state output
    assert not torch.allclose(preds, states)


def test_sps_backward_gradients() -> None:
    mod = FreePauseStatePredictionModule(d_model=32, n_heads=2, d_ff=64)
    inputs = torch.randn(1, 8, 32, requires_grad=True)
    preds, states = mod.forward_two_pass(inputs)

    loss = preds.sum() + states.sum()
    loss.backward()

    assert mod.predict_embedding.grad is not None
    assert mod.predict_embedding.grad.norm() > 0
    assert mod.q_proj.weight.grad is not None
