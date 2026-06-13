"""Coverage batch Z31: failure_analyzer, mps_compressor, tda_detector, kaggle_training, shadow_worktree."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: ouroboros/failure_analyzer.py
# ---------------------------------------------------------------------------


class TestOuroborosFailureAnalyzer:
    def test_analyze_oom_error(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("OutOfMemoryError: failed to allocate 2GB", "gpu_task")
        assert "OOM" in result.root_cause or "VRAM" in result.root_cause
        assert result.is_recoverable is True

    def test_analyze_cuda_oom(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("CUDA out of memory. Tried to allocate 500MiB", "inference")
        assert "OOM" in result.root_cause or "VRAM" in result.root_cause

    def test_analyze_timeout(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("Timeout: exceeded the timeout of 120 seconds", "timeout_task")
        assert "timeout" in result.root_cause.lower()
        assert (
            "timeout" in result.suggested_mutation.lower()
            or "budget" in result.suggested_mutation.lower()
        )

    def test_analyze_module_not_found(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("ModuleNotFoundError: No module named 'torch_npu'", "import_task")
        assert "torch_npu" in result.root_cause
        assert "torch_npu" in result.suggested_mutation

    def test_analyze_undefined_symbol(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("undefined symbol: _ZN5torch8autograd", "link_task")
        assert "mismatch" in result.root_cause.lower() or "Binary" in result.root_cause

    def test_analyze_unknown_error_default(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("generic application error", "unknown_task")
        assert result.root_cause == "Unknown failure"
        assert result.is_recoverable is True

    def test_analyze_learning_id_format(self):
        from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

        analyzer = OuroborosFailureAnalyzer()
        result = analyzer.analyze("some log", "my_task")
        assert result.learning_id.startswith("ouro_my_task_")

    def test_failure_analysis_dataclass(self):
        from cohezion.ouroboros.failure_analyzer import FailureAnalysis

        fa = FailureAnalysis(
            root_cause="OOM",
            suggested_mutation="reduce batch",
            learning_id="ouro_task_123",
            is_recoverable=True,
        )
        assert fa.root_cause == "OOM"


# ---------------------------------------------------------------------------
# Module 2: flume/mps_compressor.py
# ---------------------------------------------------------------------------


class TestMPSCompressor:
    def test_compress_returns_d_minus_1_cores(self):
        from cohezion.flume.mps_compressor import MPSCompressor

        comp = MPSCompressor(bond_dim=4)
        matrix = np.random.randn(64, 1)
        cores = comp.compress_matrix(matrix, (4, 4, 4))
        assert len(cores) == 3  # d=3 → d-1+1 cores

    def test_compress_raises_on_size_mismatch(self):
        from cohezion.flume.mps_compressor import MPSCompressor

        comp = MPSCompressor(bond_dim=4)
        matrix = np.random.randn(64, 1)
        with pytest.raises(ValueError, match="does not match"):
            comp.compress_matrix(matrix, (8, 8, 8))  # 512 != 64

    def test_reconstruct_restores_shape(self):
        from cohezion.flume.mps_compressor import MPSCompressor

        comp = MPSCompressor(bond_dim=16)
        matrix = np.random.randn(64, 1)
        cores = comp.compress_matrix(matrix, (4, 4, 4))
        reconstructed = comp.reconstruct_matrix(cores, (64, 1))
        assert reconstructed.shape == (64, 1)

    def test_bond_dim_limits_core_rank(self):
        from cohezion.flume.mps_compressor import MPSCompressor

        comp = MPSCompressor(bond_dim=2)  # Very small bond dim
        matrix = np.random.randn(256, 1)
        cores = comp.compress_matrix(matrix, (4, 4, 4, 4))
        # Each core's internal dim should be capped at bond_dim=2
        for core in cores[:-1]:  # skip last
            assert core.shape[-1] <= 2

    def test_reconstruct_approximates_original(self):
        from cohezion.flume.mps_compressor import MPSCompressor

        comp = MPSCompressor(bond_dim=64)  # Large bond = better fidelity
        matrix = np.random.randn(16, 1)
        cores = comp.compress_matrix(matrix, (4, 4))
        reconstructed = comp.reconstruct_matrix(cores, (16, 1))
        # With large bond dim, reconstruction should be close to original
        np.testing.assert_allclose(reconstructed, matrix, atol=1e-5)


# ---------------------------------------------------------------------------
# Module 3: flume/tda_detector.py
# ---------------------------------------------------------------------------


class TestTDADetector:
    def test_too_few_embeddings_returns_false(self):
        from cohezion.flume.tda_detector import TDADetector

        det = TDADetector()
        result = det.detect_circular_logic([np.random.randn(8)] * 3)
        assert result is False

    def test_no_circular_logic_linear_trajectory(self):
        from cohezion.flume.tda_detector import TDADetector

        det = TDADetector()
        embs = [np.array([i * 0.1, 0.0]) for i in range(8)]
        assert det.detect_circular_logic(embs) is False

    def test_circular_logic_detected_when_snap(self):
        from cohezion.flume.tda_detector import TDADetector

        det = TDADetector()
        embs = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([1.0, 0.0, 0.0]),  # snaps back to step 0
            np.array([0.5, 0.5, 0.5]),
        ]
        assert det.detect_circular_logic(embs) is True

    def test_custom_threshold_used(self):
        from cohezion.flume.tda_detector import TDADetector

        det = TDADetector(threshold=0.5)
        assert det.threshold == pytest.approx(0.5)

    def test_calculate_coherence_single_embedding(self):
        from cohezion.flume.tda_detector import TDADetector

        det = TDADetector()
        result = det.calculate_coherence([np.array([1.0, 0.0])])
        assert result == pytest.approx(1.0)

    def test_calculate_coherence_stable_trajectory(self):
        from cohezion.flume.tda_detector import TDADetector

        det = TDADetector()
        # Stable trajectory (constant step size) → high coherence
        embs = [np.array([i * 0.1]) for i in range(5)]
        coherence = det.calculate_coherence(embs)
        assert coherence > 0.9  # very stable → near 1.0

    def test_calculate_coherence_unstable_trajectory(self):
        from cohezion.flume.tda_detector import TDADetector

        rng = np.random.default_rng(seed=42)
        det = TDADetector()
        # Wildly varying step sizes → lower coherence
        embs = [rng.standard_normal(16) * (2**i) for i in range(8)]
        coherence = det.calculate_coherence(embs)
        assert coherence < 0.5


# ---------------------------------------------------------------------------
# Module 4: integrations/kaggle_training.py
# ---------------------------------------------------------------------------


class TestKaggleTrainingManager:
    def test_generate_lora_config_defaults(self):
        from cohezion.integrations.kaggle_training import KaggleTrainingManager

        mgr = KaggleTrainingManager()
        config = mgr.generate_lora_config()
        assert config["r"] == 8
        assert config["lora_alpha"] == 16
        assert config["lora_dropout"] == pytest.approx(0.05)
        assert config["task_type"] == "CAUSAL_LM"

    def test_generate_lora_config_custom(self):
        from cohezion.integrations.kaggle_training import KaggleTrainingManager

        mgr = KaggleTrainingManager()
        config = mgr.generate_lora_config(r=32, alpha=64, dropout=0.1, target_modules=["q", "v"])
        assert config["r"] == 32
        assert config["target_modules"] == ["q", "v"]

    def test_generate_lora_config_default_target_modules(self):
        from cohezion.integrations.kaggle_training import KaggleTrainingManager

        mgr = KaggleTrainingManager()
        config = mgr.generate_lora_config()
        assert "x_proj" in config["target_modules"]

    def test_generate_adapter_config(self):
        from cohezion.integrations.kaggle_training import KaggleTrainingManager

        mgr = KaggleTrainingManager()
        config = mgr.generate_adapter_config("nvidia/Nemotron-3-Nano")
        assert config["base_model_name_or_path"] == "nvidia/Nemotron-3-Nano"
        assert config["peft_type"] == "LORA"

    def test_prepare_notebook_creates_valid_json(self, tmp_path):
        from cohezion.integrations.kaggle_training import KaggleTrainingManager

        mgr = KaggleTrainingManager()
        out = tmp_path / "notebook.ipynb"
        asyncio.run(mgr.prepare_notebook("print('hello')", out))
        nb = json.loads(out.read_text())
        assert nb["nbformat"] == 4
        assert nb["cells"][0]["source"] == ["print('hello')"]

    def test_get_training_script_template_returns_string(self):
        from cohezion.integrations.kaggle_training import KaggleTrainingManager

        mgr = KaggleTrainingManager()
        script = mgr.get_training_script_template()
        assert isinstance(script, str)
        assert "LoraConfig" in script


# ---------------------------------------------------------------------------
# Module 5: sandbox/shadow_worktree.py
# ---------------------------------------------------------------------------


class TestShadowWorktree:
    @pytest.fixture
    def worktree(self, tmp_path):
        from cohezion.sandbox.shadow_worktree import ShadowWorktree

        return ShadowWorktree(base_repo=tmp_path, sandbox_root=tmp_path / "sandbox")

    def test_init_creates_sandbox_root(self, tmp_path):
        from cohezion.sandbox.shadow_worktree import ShadowWorktree

        sandbox = tmp_path / "my_sandbox"
        ShadowWorktree(base_repo=tmp_path, sandbox_root=sandbox)
        assert sandbox.exists()

    def test_create_sandbox_calls_git_commands(self, worktree):
        with patch("cohezion.sandbox.shadow_worktree.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            path = worktree.create_sandbox("agent-123")
        assert mock_run.call_count == 3  # checkout -b, worktree add, checkout -
        assert isinstance(path, Path)

    def test_create_sandbox_raises_on_git_failure(self, worktree):
        with patch("cohezion.sandbox.shadow_worktree.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr=b"branch exists")
            with pytest.raises(subprocess.CalledProcessError):
                worktree.create_sandbox("agent-456")

    def test_execute_in_sandbox_runs_command(self, worktree, tmp_path):
        sandbox_path = tmp_path / "sandbox_dir"
        sandbox_path.mkdir()
        with patch("cohezion.sandbox.shadow_worktree.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")
            worktree.execute_in_sandbox(sandbox_path, ["echo", "hello"])
        mock_run.assert_called_once_with(
            ["echo", "hello"], cwd=sandbox_path, capture_output=True, text=True
        )

    def test_cleanup_sandbox_calls_git_commands(self, worktree, tmp_path):
        wt_path = tmp_path / "shadow/agent_abc12345"
        with patch("cohezion.sandbox.shadow_worktree.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            worktree.cleanup_sandbox(wt_path)
        assert mock_run.call_count == 2  # worktree remove + branch -D

    def test_cleanup_sandbox_handles_exception(self, worktree, tmp_path):
        wt_path = tmp_path / "shadow/agent_xyz"
        with patch("cohezion.sandbox.shadow_worktree.subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("cleanup failed")
            # Should not raise — logs error
            worktree.cleanup_sandbox(wt_path)

    def test_precipitate_to_main_returns_true(self, worktree, tmp_path):
        result = worktree.precipitate_to_main(tmp_path / "shadow_path")
        assert result is True
