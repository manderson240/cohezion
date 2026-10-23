"""Tests for scripts/ci/repo_hygiene_ratchet.py.

Two tracked-file hygiene checks that nothing enforced before 2026-10-22:
ignore debt (tracked files that match .gitignore) and LFS debt (tracked files
whose attributes route them to LFS but whose blob is the raw content).
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ci" / "repo_hygiene_ratchet.py"

spec = importlib.util.spec_from_file_location("repo_hygiene_ratchet", SCRIPT)
assert spec is not None and spec.loader is not None
rhr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rhr)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _fixture_repo(tmp_path: Path) -> Path:
    """One tracked ignored file, one untracked ignored file, one raw and one pointer LFS file.

    Files are committed before .gitattributes exists so no installed LFS filter can
    rewrite the raw blob; the attributes file is committed afterwards.
    """
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / ".gitignore").write_text("*.log\n")
    (repo / "tracked.log").write_text("debt\n")
    (repo / "clean.py").write_text("x = 1\n")
    (repo / "raw.bin").write_bytes(b"\x00raw bytes, not a pointer")
    (repo / "pointer.bin").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 5\n"
    )
    _git(repo, "add", "-f", ".gitignore", "tracked.log", "clean.py", "raw.bin", "pointer.bin")
    _git(repo, "commit", "-q", "-m", "fixture")
    (repo / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n")
    _git(repo, "add", ".gitattributes")
    _git(repo, "commit", "-q", "-m", "attributes")
    (repo / "untracked.log").write_text("not debt\n")
    return repo


# ── T1: the measurements discriminate ────────────────────────────────────────
def test_t1_ignore_debt_counts_only_tracked_ignored_files(tmp_path):
    repo = _fixture_repo(tmp_path)
    assert rhr.ignore_debt(repo) == ["tracked.log"]


def test_t1_lfs_debt_counts_only_raw_blobs_under_lfs_attributes(tmp_path):
    repo = _fixture_repo(tmp_path)
    assert rhr.lfs_debt(repo) == ["raw.bin"]


# ── T2: the gate can go both ways ────────────────────────────────────────────
def test_t2_gate_fails_when_ignore_debt_exceeds_measured_baseline(tmp_path, capsys):
    repo = _fixture_repo(tmp_path)
    baseline = tmp_path / "b.txt"
    baseline.write_text(f"0\n{rhr.PROVENANCE}\n")
    assert rhr.gate(repo, baseline) == 1
    assert "adds new ignore debt" in capsys.readouterr().out


def test_t2_gate_fails_on_lfs_debt_regardless_of_baseline(tmp_path, capsys):
    repo = _fixture_repo(tmp_path)
    baseline = tmp_path / "b.txt"
    baseline.write_text(f"1\n{rhr.PROVENANCE}\n")
    assert rhr.gate(repo, baseline) == 1
    assert "raw.bin" in capsys.readouterr().out


def test_t2_gate_passes_at_baseline_once_lfs_debt_is_gone(tmp_path):
    repo = _fixture_repo(tmp_path)
    _git(repo, "rm", "--cached", "-q", "raw.bin")
    _git(repo, "commit", "-q", "-m", "drop raw")
    baseline = tmp_path / "b.txt"
    baseline.write_text(f"1\n{rhr.PROVENANCE}\n")
    assert rhr.gate(repo, baseline) == 0


def test_t2_unstamped_baseline_is_reported_as_unverified_not_as_author_debt(tmp_path, capsys):
    repo = _fixture_repo(tmp_path)
    _git(repo, "rm", "--cached", "-q", "raw.bin")
    _git(repo, "commit", "-q", "-m", "drop raw")
    baseline = tmp_path / "b.txt"
    baseline.write_text("0\n")
    assert rhr.gate(repo, baseline) == 1
    out = capsys.readouterr().out
    assert "UNVERIFIED" in out and "adds new ignore debt" not in out


def test_t2_update_refuses_to_raise_a_measured_baseline(tmp_path):
    repo = _fixture_repo(tmp_path)
    baseline = tmp_path / "b.txt"
    baseline.write_text(f"0\n{rhr.PROVENANCE}\n")
    assert rhr.update(repo, baseline) == 1
    assert baseline.read_text().startswith("0\n")


def test_t2_update_writes_measured_count_with_provenance(tmp_path):
    repo = _fixture_repo(tmp_path)
    baseline = tmp_path / "b.txt"
    baseline.write_text(f"5\n{rhr.PROVENANCE}\n")
    assert rhr.update(repo, baseline) == 0
    assert baseline.read_text() == f"1\n{rhr.PROVENANCE}\n"


# ── T3 CONSUMPTION: a gate nothing runs is dormant ───────────────────────────
@pytest.mark.parametrize(
    "gate",
    ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"],
)
def test_t3_ratchet_is_wired_into_the_gate(gate):
    text = (REPO / gate).read_text(encoding="utf-8")
    assert "repo_hygiene_ratchet.py" in text, f"{gate} does not run the ratchet"
    assert "repo_hygiene_ratchet.py --self-test" in text, (
        f"{gate} runs the ratchet without --self-test; an unverified gate's green is not evidence"
    )


def test_t3_committed_baseline_is_measured_and_tree_is_within_it():
    count, measured = rhr.read_baseline(rhr.BASELINE_FILE)
    assert measured, "baseline was typed, not measured; run --update"
    assert len(rhr.ignore_debt(REPO)) <= count


def test_t3_repo_has_no_lfs_debt():
    assert rhr.lfs_debt(REPO) == []


def test_t3_self_test_passes():
    proc = subprocess.run(
        [rhr.sys.executable, str(SCRIPT), "--self-test"], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
