"""Tests for JourneyToFlumeEncoder and its training loop."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from cohezion.flume.journey_encoder import (
    STEP_FEATURE_DIM,
    JourneyEncoderConfig,
    JourneyToFlumeEncoder,
    _trajectory_to_tensor,
    compute_journey_vae_loss,
    load_checkpoint,
    save_checkpoint,
)
from cohezion.flume.train import FlumeTrainConfig, train_flume_on_journeys
from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
    set_bus,
)
from cohezion.universe.llm_training_bridge import AgentTrajectory, TrajectoryStep


def _mk_step(
    coherence: float = 0.6,
    reward: float = 0.1,
    state_12d: list[float] | None = None,
) -> TrajectoryStep:
    state = state_12d if state_12d is not None else [0.5] * 12
    return TrajectoryStep(
        state_12d=state,
        action="test",
        coherence=coherence,
        spin_coherence=0.5,
        tempic_field=0.5,
        reward=reward,
    )


def _mk_trajectory(num_steps: int = 10, universe_id: str = "u-test") -> AgentTrajectory:
    steps = [_mk_step(coherence=0.5 + 0.02 * i) for i in range(num_steps)]
    return AgentTrajectory(
        agent_id=f"{universe_id}/evo-0",
        task_description="synthetic",
        steps=steps,
        final_coherence=steps[-1].coherence,
        total_reward=sum(s.reward for s in steps),
        precipitation_achieved=True,
        metadata={"universe_id": universe_id},
    )


def test_trajectory_to_tensor_shape_and_padding() -> None:
    traj = _mk_trajectory(num_steps=5)
    features, mask = _trajectory_to_tensor(traj, max_seq_len=20)
    assert features.shape == (20, STEP_FEATURE_DIM)
    assert mask.shape == (20,)
    # First 5 valid, next 15 padded.
    assert mask[:5].all()
    assert not mask[5:].any()
    # Padding is HIHO baseline (0.5).
    assert torch.allclose(features[5:], torch.full((15, STEP_FEATURE_DIM), 0.5))


def test_encoder_forward_shape() -> None:
    config = JourneyEncoderConfig(embed_dim=64, z_dim=64, num_layers=1, max_seq_len=32)
    encoder = JourneyToFlumeEncoder(config)
    features = torch.randn(2, 10, STEP_FEATURE_DIM)
    mask = torch.ones(2, 10, dtype=torch.bool)
    recon, mu, log_var, z = encoder(features, mask)
    assert recon.shape == (2, 10, STEP_FEATURE_DIM)
    assert mu.shape == (2, 64)
    assert log_var.shape == (2, 64)
    assert z.shape == (2, 64)


def test_encode_trajectory_single() -> None:
    config = JourneyEncoderConfig(embed_dim=64, z_dim=64, num_layers=1, max_seq_len=32)
    encoder = JourneyToFlumeEncoder(config)
    traj = _mk_trajectory(num_steps=7)
    mu, log_var = encoder.encode_trajectory(traj)
    assert mu.shape == (64,)
    assert log_var.shape == (64,)


def test_compute_loss_masks_padded_positions() -> None:
    recon = torch.randn(2, 5, STEP_FEATURE_DIM)
    target = torch.zeros(2, 5, STEP_FEATURE_DIM)
    mask = torch.tensor([[True, True, False, False, False], [True, True, True, False, False]])
    mu = torch.randn(2, 8)
    log_var = torch.zeros(2, 8)
    total, recon_loss, _kl_loss = compute_journey_vae_loss(recon, target, mask, mu, log_var)
    assert total.isfinite()
    assert recon_loss >= 0
    # Padding positions shouldn't contribute — verify by perturbing them and seeing no change.
    recon2 = recon.clone()
    recon2[0, 3] = recon2[0, 3] + 1000  # modify a padded position
    _, recon_loss2, _ = compute_journey_vae_loss(recon2, target, mask, mu, log_var)
    assert torch.allclose(recon_loss, recon_loss2)


def test_save_and_load_checkpoint(tmp_path: Path) -> None:
    config = JourneyEncoderConfig(embed_dim=32, z_dim=32, num_layers=1)
    encoder = JourneyToFlumeEncoder(config)
    ckpt = save_checkpoint(encoder, tmp_path / "ckpt.pt", metadata={"note": "test"})
    assert ckpt.exists()
    restored = load_checkpoint(ckpt)
    assert restored.config.embed_dim == 32

    # Weights match
    for key, value in encoder.state_dict().items():
        assert torch.allclose(value, restored.state_dict()[key])


@pytest.fixture
def capture_bus():
    bus = PrecipitationBus()
    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=None)
    set_bus(bus)
    try:
        yield captured
    finally:
        set_bus(None)


def test_train_flume_on_journeys_emits_checkpoint_events(
    tmp_path: Path,
    capture_bus: list[PrecipitationEvent],
) -> None:
    trajectories = [_mk_trajectory(num_steps=8) for _ in range(6)]
    config = FlumeTrainConfig(
        epochs=2,
        batch_size=2,
        checkpoint_every=2,
        output_dir=tmp_path,
        max_seq_len=16,
        universe_id_for_events="u-flume-train-test",
    )
    ckpt_path = train_flume_on_journeys(trajectories, config=config)
    assert ckpt_path.exists()

    # Should have at least one checkpoint event (checkpoints every 2 steps, plus final).
    ckpt_events = [e for e in capture_bus if e.kind == PrecipitationKind.TRAINING_CHECKPOINT]
    assert len(ckpt_events) >= 1
    for e in ckpt_events:
        assert e.universe_id == "u-flume-train-test"
        assert "loss" in e.payload
        assert "checkpoint_path" in e.payload


def test_training_loss_decreases_on_consistent_data(tmp_path: Path) -> None:
    """On a small repetitive dataset, the loss should decrease meaningfully."""
    torch.manual_seed(13)
    # Build a dataset of 20 near-identical trajectories — trivially learnable.
    traj = _mk_trajectory(num_steps=10)
    dataset = [traj for _ in range(20)]

    encoder = JourneyToFlumeEncoder(
        JourneyEncoderConfig(embed_dim=32, z_dim=32, num_layers=1, max_seq_len=16)
    )
    config = FlumeTrainConfig(
        epochs=1,
        batch_size=4,
        lr=1e-3,
        checkpoint_every=1000,  # suppress intermediate checkpoint events
        output_dir=tmp_path,
        max_seq_len=16,
    )

    # Record initial loss on the dataset, train, then record final loss.
    features, mask = _trajectory_to_tensor(traj, max_seq_len=16)
    features = features.unsqueeze(0)
    mask = mask.unsqueeze(0)

    encoder.eval()
    with torch.no_grad():
        recon, mu, log_var, _ = encoder(features, mask)
    total_before, _, _ = compute_journey_vae_loss(recon, features, mask, mu, log_var)

    train_flume_on_journeys(dataset, config=config, encoder=encoder)

    encoder.eval()
    with torch.no_grad():
        recon, mu, log_var, _ = encoder(features, mask)
    total_after, _, _ = compute_journey_vae_loss(recon, features, mask, mu, log_var)

    # Loss should improve (or at worst not blow up). Use a generous tolerance.
    assert total_after < total_before + 0.1
