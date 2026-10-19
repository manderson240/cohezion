"""Unit tests for Environment-Adaptive Inference Abstraction (EAIA)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.environment_adapter import (
    EnvironmentAdaptiveInferenceManager,
    ExecutionEnvironment,
    InferenceRegistryHook,
    InferSpec,
    PrivacyTier,
)


def test_environment_detection_local():
    with patch("os.path.exists", return_value=False), patch.dict("os.environ", {}, clear=True):
        env = EnvironmentAdaptiveInferenceManager.detect_environment()
        assert env == ExecutionEnvironment.STRIX_HALO_LOCAL


def test_environment_detection_kaggle():
    def mock_exists(p: str) -> bool:
        return p == "/kaggle/input"

    with patch("os.path.exists", side_effect=mock_exists):
        env = EnvironmentAdaptiveInferenceManager.detect_environment()
        assert env == ExecutionEnvironment.KAGGLE_AIRGAPPED_CONTAINER


def test_environment_detection_ci():
    with patch("os.path.exists", return_value=False), patch.dict("os.environ", {"CI": "true"}):
        env = EnvironmentAdaptiveInferenceManager.detect_environment()
        assert env == ExecutionEnvironment.CI_OR_CLOUD_SANDBOX


def test_binding_resolution_kaggle(tmp_path: Path):
    manager = EnvironmentAdaptiveInferenceManager(state_path=tmp_path / "eaia_state.json")
    manager.current_environment = ExecutionEnvironment.KAGGLE_AIRGAPPED_CONTAINER

    spec = InferSpec(task_class="coding", prompt="def test(): pass")
    binding = manager.resolve_binding(spec)

    assert binding.environment == ExecutionEnvironment.KAGGLE_AIRGAPPED_CONTAINER
    assert binding.is_airgapped is True
    assert binding.provider == "embedded_server"
    assert "http://127.0.0.1:13305" in binding.endpoint


def test_binding_resolution_strix_halo_local_vs_cloud(tmp_path: Path):
    manager = EnvironmentAdaptiveInferenceManager(state_path=tmp_path / "eaia_state.json")
    manager.current_environment = ExecutionEnvironment.STRIX_HALO_LOCAL

    # Local strict
    spec_local = InferSpec(task_class="fast_qa", privacy_tier=PrivacyTier.LOCAL_ONLY)
    b_local = manager.resolve_binding(spec_local)
    assert b_local.provider == "lemonade_npu_flm"

    # Cloud permitted
    spec_cloud = InferSpec(task_class="reasoning", privacy_tier=PrivacyTier.CLOUD_PERMITTED)
    b_cloud = manager.resolve_binding(spec_cloud)
    assert b_cloud.provider == "ollama_cloud_tier2"


@pytest.mark.asyncio
async def test_eaia_dispatch_telemetry(tmp_path: Path):
    mock_bus = AsyncMock()
    manager = EnvironmentAdaptiveInferenceManager(
        state_path=tmp_path / "eaia_state.json",
        event_bus=mock_bus,
    )
    spec = InferSpec(task_class="vision", prompt="analyze slice")
    result = await manager.dispatch(spec)

    assert result["status"] == "success"
    assert "binding" in result
    assert mock_bus.publish.called


def test_export_kaggle_freeze_profile(tmp_path: Path):
    manager = EnvironmentAdaptiveInferenceManager(state_path=tmp_path / "eaia_state.json")
    freeze_file = tmp_path / "kaggle_freeze.json"
    profile = manager.export_kaggle_freeze_profile(freeze_file)

    assert freeze_file.exists()
    assert profile["environment"] == "kaggle_airgapped_container"
    assert profile["embedded_daemon"]["default_port"] == 13305
    assert "conformal_world_model" in profile


def test_inference_registry_hook(tmp_path: Path):
    manager = EnvironmentAdaptiveInferenceManager(state_path=tmp_path / "eaia_state.json")
    hook = InferenceRegistryHook(manager=manager)

    # Pre-populate cache
    spec = InferSpec(task_class="general")
    manager.resolve_binding(spec)
    assert len(manager._cached_bindings) > 0

    # Trigger hook on skill registered
    hook.on_skill_registered("NEW_SOTA_PRIME", {"category": "coding"})
    assert len(manager._cached_bindings) == 0
