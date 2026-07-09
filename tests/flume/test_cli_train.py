"""Tests for FLUME CLI training script (US-001).

Covers:
  - Argument parsing (all flags)
  - --epochs 0 skips training
  - Mocked pipeline integration
  - Exit code 0 on success, 1 on failure
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


# ROCm/AMD GPU subprocess tests crash with SIGSEGV when amdgpu.ids is missing
_AMDGPU_IDS_MISSING = not Path("/usr/share/misc/amdgpu.ids").exists()
_skip_amd_subprocess = pytest.mark.skipif(
    _AMDGPU_IDS_MISSING,
    reason="amdgpu.ids missing — GPU subprocess tests segfault on this hardware",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "train_flume.py"
_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_build_parser():
    """Import build_parser from scripts/train_flume.py without running main()."""
    spec = importlib.util.spec_from_file_location("train_flume_cli", _SCRIPT_PATH)
    assert spec is not None, f"Could not find {_SCRIPT_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.build_parser


def _run_script(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI script as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )


# ---------------------------------------------------------------------------
# Argument Parsing Tests
# ---------------------------------------------------------------------------


class TestArgumentParsing:
    """All CLI flags parse correctly."""

    @pytest.fixture(autouse=True)
    def _parser(self):
        self.build_parser = _load_build_parser()

    def _parse(self, args: list[str]):
        return self.build_parser().parse_args(args)

    def test_default_epochs(self):
        assert self._parse([]).epochs == 50

    def test_epochs_flag(self):
        assert self._parse(["--epochs", "2"]).epochs == 2

    def test_epochs_zero_allowed(self):
        """--epochs 0 must be accepted (skips training)."""
        assert self._parse(["--epochs", "0"]).epochs == 0

    def test_batch_size_flag(self):
        assert self._parse(["--batch-size", "32"]).batch_size == 32

    def test_batch_size_default(self):
        assert self._parse([]).batch_size == 64

    def test_lr_flag(self):
        args = self._parse(["--lr", "5e-4"])
        assert abs(args.lr - 5e-4) < 1e-10

    def test_n_samples_flag(self):
        assert self._parse(["--n-samples", "50"]).n_samples == 50

    def test_evaluate_flag(self):
        assert self._parse(["--evaluate"]).evaluate is True

    def test_evaluate_default_false(self):
        assert self._parse([]).evaluate is False

    def test_checkpoint_dir_flag(self):
        assert self._parse(["--checkpoint-dir", "/tmp/ckpts"]).checkpoint_dir == "/tmp/ckpts"

    def test_require_ollama_flag(self):
        assert self._parse(["--require-ollama"]).require_ollama is True

    def test_require_ollama_default_false(self):
        assert self._parse([]).require_ollama is False

    def test_save_data_flag(self):
        assert self._parse(["--save-data", "/tmp/data.npz"]).save_data == "/tmp/data.npz"

    def test_save_data_default_none(self):
        assert self._parse([]).save_data is None

    def test_load_data_flag(self):
        assert self._parse(["--load-data", "/tmp/data.npz"]).load_data == "/tmp/data.npz"

    def test_load_data_default_none(self):
        assert self._parse([]).load_data is None

    def test_load_checkpoint_flag(self):
        assert self._parse(["--load-checkpoint", "/tmp/ckpt.pt"]).load_checkpoint == "/tmp/ckpt.pt"

    def test_load_checkpoint_default_none(self):
        assert self._parse([]).load_checkpoint is None

    def test_combined_flags(self):
        args = self._parse(
            [
                "--epochs",
                "10",
                "--batch-size",
                "32",
                "--lr",
                "1e-4",
                "--n-samples",
                "100",
                "--evaluate",
                "--checkpoint-dir",
                "/tmp/ck",
            ]
        )
        assert args.epochs == 10
        assert args.batch_size == 32
        assert abs(args.lr - 1e-4) < 1e-12
        assert args.n_samples == 100
        assert args.evaluate is True
        assert args.checkpoint_dir == "/tmp/ck"


# ---------------------------------------------------------------------------
# Integration Tests (subprocess) — use --load-data to avoid Ollama
# ---------------------------------------------------------------------------


def _make_npz(tmp_path: Path, n: int = 20, dim: int = 256) -> Path:
    """Create a small .npz with random float32 embeddings + contrastive pairs."""
    rng = np.random.default_rng(42)
    embs = rng.standard_normal((n, dim)).astype(np.float32)
    # Normalize
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    embs /= np.where(norms > 0, norms, 1.0)
    pairs = np.array([[i, i + 1] for i in range(0, min(n - 1, 10), 2)], dtype=np.int32)
    path = tmp_path / "data.npz"
    np.savez_compressed(path, embeddings=embs, pairs=pairs)
    return path


@pytest.mark.timeout(60)
@_skip_amd_subprocess
class TestMockedPipelineIntegration:
    """End-to-end pipeline tests using subprocess with pre-made hash embeddings.

    All tests use --load-data to avoid Ollama latency and make runs deterministic.
    """

    def test_exit_code_0_on_success(self, tmp_path):
        """Basic run with --epochs 0 --load-data should return exit code 0."""
        npz = _make_npz(tmp_path)
        result = _run_script(
            "--epochs",
            "0",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_epochs_zero_skips_training(self, tmp_path):
        """--epochs 0 must not write a checkpoint."""
        npz = _make_npz(tmp_path)
        result = _run_script(
            "--epochs",
            "0",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert not (tmp_path / "flume_vae_latest.pt").exists()

    def test_training_saves_checkpoint(self, tmp_path):
        """epochs > 0 should save flume_vae_latest.pt in checkpoint-dir."""
        npz = _make_npz(tmp_path, n=32)
        result = _run_script(
            "--epochs",
            "1",
            "--batch-size",
            "8",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert (tmp_path / "flume_vae_latest.pt").exists()

    def test_evaluate_flag_produces_json(self, tmp_path):
        """--evaluate should write evaluation_results.json with required keys."""
        npz = _make_npz(tmp_path, n=32)
        result = _run_script(
            "--epochs",
            "1",
            "--batch-size",
            "8",
            "--evaluate",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        eval_json = tmp_path / "evaluation_results.json"
        assert eval_json.exists()
        import json

        data = json.loads(eval_json.read_text())
        assert "kl_value" in data
        assert "reconstruction_cosine_sim" in data
        assert "n_passed" in data

    def test_save_data_creates_npz(self, tmp_path):
        """--save-data should write a .npz with 'embeddings' and 'pairs' arrays."""
        src = _make_npz(tmp_path, n=15)
        save_path = tmp_path / "saved.npz"
        result = _run_script(
            "--epochs",
            "0",
            "--load-data",
            str(src),
            "--save-data",
            str(save_path),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert save_path.exists()
        d = np.load(save_path)
        assert "embeddings" in d
        assert d["embeddings"].shape[0] == 15

    def test_load_data_and_train(self, tmp_path):
        """--load-data loads pre-computed embeddings and training succeeds."""
        npz = _make_npz(tmp_path, n=20, dim=256)
        result = _run_script(
            "--epochs",
            "1",
            "--batch-size",
            "8",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert (tmp_path / "flume_vae_latest.pt").exists()

    def test_exit_code_1_on_bad_checkpoint(self, tmp_path):
        """Loading a nonexistent checkpoint should exit with code 1."""
        npz = _make_npz(tmp_path)
        result = _run_script(
            "--epochs",
            "1",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
            "--load-checkpoint",
            str(tmp_path / "nonexistent.pt"),
        )
        assert result.returncode == 1

    def test_full_pipeline_n50_epochs2_evaluate(self, tmp_path):
        """AC requirement: equivalent of --n-samples 50 --epochs 2 --evaluate, via --load-data."""
        # Use 50 pre-made embeddings to simulate the AC requirement without Ollama
        npz = _make_npz(tmp_path, n=50, dim=256)
        result = _run_script(
            "--epochs",
            "2",
            "--batch-size",
            "16",
            "--evaluate",
            "--load-data",
            str(npz),
            "--checkpoint-dir",
            str(tmp_path),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert (tmp_path / "flume_vae_latest.pt").exists()
        assert (tmp_path / "evaluation_results.json").exists()
