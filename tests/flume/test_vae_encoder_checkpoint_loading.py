"""FlumeVAEEncoder must load real training checkpoints, and refuse the ones it cannot use.

Before this fix the loader could never enable a VAE: it built ``SimpleEncoder`` with
kwargs it does not accept, so every checkpoint fell into the ``except Exception`` hash
fallback. Its default path was also CWD-relative (``./data/...``), so a daemon started
from any other directory never found the file. Both failures were silent.

Checkpoints here use the training format (``cohezion.flume.training``): ``encoder`` is a
``Sequential`` state dict (``0.*`` / ``2.*``) and ``mu_head`` is a ``Linear``.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from cohezion.flume import vae_encoder as ve
from cohezion.flume.vae_encoder import FlumeVAEEncoder


torch = pytest.importorskip("torch")
pytestmark = pytest.mark.skipif(not ve.TORCH_AVAILABLE, reason="torch unavailable")

REPO_ROOT = Path(__file__).resolve().parents[2]
TEXTS = ["the cat sat on the mat", "SELECT * FROM users", "def f(x): return x + 1"]


def _write_ckpt(
    path: Path, *, input_dim: int = 256, hidden: int = 512, mu_bias: float = 0.0
) -> Path:
    """Identity-like trunk (out == in for non-negative inputs) plus a constant mu bias.

    mu_bias=0 keeps the hash inputs' own geometry (mean cosine ~0.77), a usable encoder.
    A large mu_bias swamps the text-dependent signal: every latent points one way.
    """
    w0 = torch.zeros(hidden, input_dim)
    w0[:input_dim, :input_dim] = torch.eye(input_dim)
    encoder = {
        "0.weight": w0,
        "0.bias": torch.zeros(hidden),
        "2.weight": torch.eye(hidden),
        "2.bias": torch.zeros(hidden),
    }
    k = min(256, hidden)
    mu_w = torch.zeros(256, hidden)
    mu_w[:k, :k] = torch.eye(k)
    mu_head = {"weight": mu_w, "bias": torch.full((256,), mu_bias)}
    torch.save({"encoder": encoder, "mu_head": mu_head}, path)
    return path


def test_healthy_checkpoint_enables_and_is_used(tmp_path):
    enc = FlumeVAEEncoder(model_path=_write_ckpt(tmp_path / "ok.pt"))

    assert enc.enabled, "a loadable, non-degenerate checkpoint must enable the VAE"
    out = enc.encode(TEXTS[0])
    assert out.shape == (256,)
    assert np.isclose(np.linalg.norm(out), 1.0, atol=1e-5)


def test_vae_output_differs_from_hash_when_trunk_transforms(tmp_path):
    """Discriminating: a loader that silently falls back to hashing returns the hash vector."""
    path = _write_ckpt(tmp_path / "ok.pt", mu_bias=0.01)
    enc = FlumeVAEEncoder(model_path=path)

    assert enc.enabled
    assert not np.allclose(enc.encode(TEXTS[1]), FlumeVAEEncoder._hash_encode(TEXTS[1]))


def test_wrong_input_width_is_refused(tmp_path):
    """ep2-style toy checkpoints take 64-dim input; the hash frontend emits 256."""
    enc = FlumeVAEEncoder(model_path=_write_ckpt(tmp_path / "w64.pt", input_dim=64, hidden=128))

    assert not enc.enabled
    assert np.allclose(enc.encode(TEXTS[0]), FlumeVAEEncoder._hash_encode(TEXTS[0]))


def test_degenerate_checkpoint_is_refused(tmp_path):
    """Latents that all point one way would make the semantic cache match everything."""
    enc = FlumeVAEEncoder(model_path=_write_ckpt(tmp_path / "degenerate.pt", mu_bias=100.0))

    assert not enc.enabled
    assert enc.encoder is None and enc.mu_head is None


def test_default_path_is_anchored_at_repo_root_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    default = FlumeVAEEncoder.DEFAULT_MODEL_PATH
    assert default.is_absolute()
    assert default.parent == REPO_ROOT / "data" / "flume" / "checkpoints"
    assert Path(os.getcwd()) not in default.parents


def test_tracked_ep2_checkpoint_falls_back_to_hash():
    """The only checkpoint tracked in git is ep2 (64-dim input). It must not enable."""
    ep2 = REPO_ROOT / "data" / "flume" / "checkpoints" / "flume_vae_ep2.pt"
    if not ep2.exists():
        pytest.skip("ep2 checkpoint not present")
    enc = FlumeVAEEncoder(model_path=ep2)

    assert not enc.enabled
    assert np.allclose(enc.encode(TEXTS[2]), FlumeVAEEncoder._hash_encode(TEXTS[2]))
