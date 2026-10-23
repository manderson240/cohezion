"""A Git LFS pointer where a checkpoint should be is "no checkpoint", not corruption.

CI runners and fresh clones do not run ``git lfs pull``; the ~130-byte pointer text is
what ``data/rl/checkpoints/policy_final.pt`` contains there. Before this guard,
``torch.load`` raised an UnpicklingError that read like a corrupt file and took the
whole ``/rl/*`` API surface down with it (PR #327, 2026-10-23).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.api import _helpers


POINTER = (
    "version https://git-lfs.github.com/spec/v1\n"
    "oid sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n"
    "size 123456\n"
)


def test_pointer_text_is_detected(tmp_path: Path) -> None:
    p = tmp_path / "policy_final.pt"
    p.write_text(POINTER)
    assert _helpers._is_lfs_pointer(p) is True


def test_binary_checkpoint_is_not_a_pointer(tmp_path: Path) -> None:
    p = tmp_path / "policy_final.pt"
    p.write_bytes(b"PK\x03\x04" + b"\x00" * 60)  # torch zip-format magic
    assert _helpers._is_lfs_pointer(p) is False


def test_missing_file_is_not_a_pointer(tmp_path: Path) -> None:
    assert _helpers._is_lfs_pointer(tmp_path / "absent.pt") is False


def test_rl_policy_loads_random_weights_over_a_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discriminating: without the guard this raises _pickle.UnpicklingError."""
    import cohezion.api as api_module

    ckpt = tmp_path / "data" / "rl" / "checkpoints" / "policy_final.pt"
    ckpt.parent.mkdir(parents=True)
    ckpt.write_text(POINTER)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api_module, "_rl_policy", None, raising=False)

    policy = _helpers.get_rl_policy()

    assert policy is not None
    monkeypatch.setattr(api_module, "_rl_policy", None, raising=False)
