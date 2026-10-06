"""Tests for scripts/codegraph — the generator CLI and the SessionStart watcher.

Both are exercised as subprocesses under a FAKE ``HOME`` so nothing here can touch the
real vault artifact (``~/vaults/cohezion-vault/graph/codegraph.json``). The generator
tests are the discriminating ones: before the argparse fix, ``--help`` ran the full
build and OVERWROTE the artifact.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "scripts" / "codegraph" / "build_graph.py"
WATCH = REPO / "scripts" / "codegraph" / "codegraph-watch.sh"
REL_ARTIFACT = Path("vaults") / "cohezion-vault" / "graph" / "codegraph.json"


def _env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run_build(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILD), *args],
        cwd=REPO,
        env=_env(home),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _run_watch(home: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(WATCH)],
        cwd=REPO,
        env=_env(home),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _head_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


# --------------------------------------------------------------------------- generator


def test_help_does_not_build_or_write(tmp_path: Path) -> None:
    proc = _run_build(tmp_path, "--help")
    assert proc.returncode == 0, proc.stderr
    assert "usage:" in proc.stdout
    assert "--dry-run" in proc.stdout
    assert not (tmp_path / REL_ARTIFACT).exists(), "--help must never write the artifact"
    assert "wrote " not in proc.stdout


def test_dry_run_prints_summary_and_writes_nothing(tmp_path: Path) -> None:
    pytest.importorskip("networkx")
    proc = _run_build(tmp_path, "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("dry-run:"), proc.stdout
    assert "spine:" in proc.stdout and "communities:" in proc.stdout
    assert not (tmp_path / REL_ARTIFACT).exists(), "--dry-run must never write the artifact"
    assert "SyntaxWarning" not in proc.stderr, "tree SyntaxWarnings must be silenced"


def test_print_writes_artifact_under_home_and_watcher_reports_ready(tmp_path: Path) -> None:
    pytest.importorskip("networkx")
    proc = _run_build(tmp_path, "--print")
    assert proc.returncode == 0, proc.stderr
    artifact = tmp_path / REL_ARTIFACT
    assert artifact.exists(), proc.stdout
    art = json.loads(artifact.read_text(encoding="utf-8"))
    for key in ("head_sha", "import_spine", "communities", "isolated_count", "nodes", "edges"):
        assert key in art, f"artifact missing {key}"
    assert art["head_sha"] == _head_sha()
    assert art["nodes"] > 100 and art["edges"] > 100
    assert "wrote " in proc.stdout and "spine:" in proc.stdout

    watch = _run_watch(tmp_path)
    assert watch.returncode == 0
    assert watch.stdout.startswith("[codegraph:ready] "), watch.stdout


# ----------------------------------------------------------------------------- watcher


def _write_artifact(home: Path, payload: dict) -> Path:
    path = home / REL_ARTIFACT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_watcher_absent_when_no_artifact(tmp_path: Path) -> None:
    proc = _run_watch(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.startswith("[codegraph:absent]"), proc.stdout


def test_watcher_stale_when_head_moved(tmp_path: Path) -> None:
    _write_artifact(tmp_path, {"head_sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"})
    proc = _run_watch(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.startswith("[codegraph:stale]"), proc.stdout
    assert "deadbeefd" in proc.stdout and _head_sha()[:9] in proc.stdout


def test_watcher_ready_when_head_matches(tmp_path: Path) -> None:
    _write_artifact(tmp_path, {"head_sha": _head_sha()})
    proc = _run_watch(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.startswith("[codegraph:ready] "), proc.stdout


def test_watcher_artifact_without_head_sha_is_not_ready(tmp_path: Path) -> None:
    """Fail-closed edge: a JSON with no head_sha cannot be trusted as current."""
    _write_artifact(tmp_path, {"nodes": 1, "edges": 0})
    proc = _run_watch(tmp_path)
    assert proc.returncode == 0
    assert not proc.stdout.startswith("[codegraph:ready]"), proc.stdout
    assert proc.stdout.startswith("[codegraph:absent]"), proc.stdout
    assert "no head_sha" in proc.stdout
