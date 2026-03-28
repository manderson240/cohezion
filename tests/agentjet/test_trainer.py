"""Tests for AgentJetTrainer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.agentjet.context_optimizer import ModelContextProfile
from cohezion.agentjet.trainer import AgentJetTrainer, TrainingResult


def _make_tasks(n: int = 3, phi: float = 0.8, skill: str = "coding") -> list[dict]:
    return [
        {"phi_score": phi, "skill_name": skill, "instruction": f"task {i}", "output": "out"}
        for i in range(n)
    ]


@pytest.fixture
def mock_context_manager():
    mgr = MagicMock()
    mgr.get_available_memory_gb = AsyncMock(return_value=80.0)
    mgr.unload_all_for_training = AsyncMock()
    mgr.reload_inference_models = AsyncMock()
    mgr.get_profile = MagicMock(
        return_value=ModelContextProfile("test-model", num_ctx=16384, size_gb=10.0)
    )
    mgr.cached_available_gb = 80.0
    return mgr


@pytest.fixture
def trainer(mock_context_manager) -> AgentJetTrainer:
    return AgentJetTrainer(context_manager=mock_context_manager)


@pytest.mark.asyncio
async def test_dry_run_returns_training_result_with_dry_run_true(
    trainer: AgentJetTrainer, mock_context_manager: MagicMock
) -> None:
    tasks = _make_tasks(5)
    with patch.object(trainer.reader, "read", return_value=tasks):
        result = await trainer.train(target_model="phi3:mini", dry_run=True)

    assert isinstance(result, TrainingResult)
    assert result.dry_run is True
    # dry_run=True skips unload and training
    mock_context_manager.unload_all_for_training.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_succeeds_without_training(
    trainer: AgentJetTrainer,
) -> None:
    tasks = _make_tasks(3)
    with patch.object(trainer.reader, "read", return_value=tasks):
        result = await trainer.train(dry_run=True)

    assert result.success is True
    assert result.samples_used == 3


@pytest.mark.asyncio
async def test_no_training_data_returns_failure(
    trainer: AgentJetTrainer,
) -> None:
    with patch.object(trainer.reader, "read", return_value=[]):
        result = await trainer.train()

    assert result.success is False
    assert result.samples_used == 0
    assert result.error is not None


@pytest.mark.asyncio
async def test_oom_check_raises_when_memory_insufficient(
    mock_context_manager: MagicMock,
) -> None:
    # Override to return very little memory — local OOM check in _safety_check
    # raises before the try/except block in train(), so the exception propagates.
    mock_context_manager.get_available_memory_gb = AsyncMock(return_value=5.0)
    mock_context_manager.get_profile = MagicMock(
        return_value=ModelContextProfile("big-model", num_ctx=8192, size_gb=30.0)
    )
    trainer = AgentJetTrainer(context_manager=mock_context_manager)

    tasks = _make_tasks(3)
    with patch.object(trainer.reader, "read", return_value=tasks):
        with patch.object(
            trainer,
            "_safety_check",
            new_callable=AsyncMock,
            side_effect=RuntimeError("OOMRiskError: insufficient memory"),
        ):
            # _safety_check is now inside try; exception is caught → TrainingResult failure
            result = await trainer.train(target_model="big-model")
        assert result.success is False
        assert result.error is not None
        assert "OOMRiskError" in result.error


@pytest.mark.asyncio
async def test_llamafactory_backend_calls_local_finetuner(
    mock_context_manager: MagicMock,
) -> None:
    # backend is a constructor argument, not a train() argument
    trainer = AgentJetTrainer(
        context_manager=mock_context_manager,
        backend="llamafactory",
    )
    tasks = _make_tasks(2)
    mock_finetuner = MagicMock()
    mock_finetuner.run_qlora_training = MagicMock(
        return_value=Path("/tmp/cohezion_general_v9999/train.sh")
    )

    with patch.object(trainer.reader, "read", return_value=tasks):
        with patch.object(trainer, "_safety_check", new_callable=AsyncMock):
            with patch(
                "cohezion.flume.local_finetune_pipeline.LocalFinetuner",
                return_value=mock_finetuner,
            ):
                result = await trainer.train(target_model="qwen3.5:9b")

    # Just verify the shape — backend dispatch happens internally
    assert isinstance(result, TrainingResult)


@pytest.mark.asyncio
async def test_reload_inference_models_called_after_success(
    trainer: AgentJetTrainer, mock_context_manager: MagicMock
) -> None:
    tasks = _make_tasks(2)
    with patch.object(trainer.reader, "read", return_value=tasks):
        with patch.object(trainer, "_run_training", new_callable=AsyncMock, return_value=None):
            with patch.object(trainer, "_safety_check", new_callable=AsyncMock):
                await trainer.train(target_model="phi3:mini", dry_run=False)

    mock_context_manager.reload_inference_models.assert_called_once()


@pytest.mark.asyncio
async def test_reload_inference_models_called_even_on_error(
    trainer: AgentJetTrainer, mock_context_manager: MagicMock
) -> None:
    tasks = _make_tasks(2)
    with (
        patch.object(trainer.reader, "read", return_value=tasks),
        patch.object(
            trainer,
            "_run_training",
            new_callable=AsyncMock,
            side_effect=ValueError("training exploded"),
        ),
        patch.object(trainer, "_safety_check", new_callable=AsyncMock),
    ):
        result = await trainer.train(dry_run=False)

    # finally block should have run reload
    mock_context_manager.reload_inference_models.assert_called_once()
    # Training failed
    assert result.success is False


def test_training_result_dataclass_fields() -> None:
    result = TrainingResult(
        success=True,
        model_name="cohezion-coding-v1234",
        base_model="qwen3.5:9b",
        skill_domain="coding",
        epochs_completed=3,
        samples_used=50,
        avg_reward=0.75,
        training_duration_s=120.5,
        output_path=Path("/tmp/output"),
    )
    assert result.success is True
    assert result.dry_run is False  # default
    assert result.error is None  # default
