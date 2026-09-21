"""The ratchet must never report a violation count from a run that did not happen.

`_count()` parsed `proc.stdout or "[]"` without checking `proc.returncode`. When the
ruff invocation failed -- `uv` unable to build a venv, ruff unable to write
`.ruff_cache` in a read-only worktree -- stdout was empty, `"[]"` parsed to zero
violations, and the gate reported a PASS.

Observed live 2026-09-20 in a read-only git worktree:

    ruff_ratchet: 0 < baseline 905 -- debt reduced by 905!

while `ruff check` on that same tree found 896. The follow-on is the dangerous part:
`--update` would then write a baseline of 0 carrying the `measured-by` provenance
stamp, laundering a failed run into an authoritative number -- precisely what that
stamp was added to prevent.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "ruff_ratchet.py"


def _load():
    spec = importlib.util.spec_from_file_location("ruff_ratchet_uut", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ratchet():
    return _load()


def _completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["ruff"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_failed_ruff_run_refuses_instead_of_reporting_zero(ratchet, monkeypatch):
    """The regression guard. Pre-fix this returned 0 and the gate passed."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _completed(2, "", "error: Read-only file system"),
    )
    with pytest.raises(SystemExit) as exc:
        ratchet._current_count()
    assert "did not run" in str(exc.value)


def test_clean_tree_reports_zero(ratchet, monkeypatch):
    """Discriminating: exit 0 with an empty list is a REAL zero and must be kept.

    A fix that rejected every empty result would pass the test above and break
    the legitimate clean-tree case.
    """
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(0, "[]"))
    assert ratchet._current_count() == 0


def test_violations_found_are_counted(ratchet, monkeypatch):
    """ruff exits 1 when it finds violations -- that is success, not failure."""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(1, '[{"code":"E402"}]'))
    assert ratchet._current_count() == 1


def test_count_is_measured_without_a_writable_cache(ratchet):
    """--no-cache keeps the gate usable in a read-only worktree.

    Without it ruff exits 2 trying to create .ruff_cache, which (post-fix) makes
    the gate refuse -- honest, but unable to measure anywhere under a ro mount.
    """
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed(0, "[]")

    import unittest.mock

    with unittest.mock.patch.object(subprocess, "run", fake_run):
        ratchet._current_count()
    assert "--no-cache" in captured["cmd"]
