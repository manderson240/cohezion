"""Discriminating tests for the datamesh land scanner (discovery producer).

The census classification is the load-bearing logic: INTEGRATED must be decided
by MERGED-TREE IDENTITY (the only test that survives squash merges), never by
ancestry. Each test builds a throwaway repo so the git plumbing runs for real.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "datamesh_land_scanner.py"
spec = importlib.util.spec_from_file_location("land_scanner", _SCRIPT)
assert spec is not None and spec.loader is not None
land_scanner = importlib.util.module_from_spec(spec)
sys.modules["land_scanner"] = land_scanner
spec.loader.exec_module(land_scanner)


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "a.txt").write_text("base\n")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-m", "base")
    return r


class TestCensusClassification:
    def test_clean_branch_is_clean(self, repo: Path):
        _git(repo, "checkout", "-b", "feat/x")
        (repo / "b.txt").write_text("new\n")
        _git(repo, "add", "b.txt")
        _git(repo, "commit", "-m", "feat: b")
        _git(repo, "checkout", "main")
        v = {x.branch: x for x in land_scanner.census(str(repo))}
        assert v["feat/x"].classification == "CLEAN"
        assert v["feat/x"].ahead == 1
        assert v["feat/x"].files_changed == 1

    def test_squash_merged_branch_is_integrated_despite_ancestry(self, repo: Path):
        """T2 discriminating: ancestry says 'ahead', tree identity says DONE.

        A wrong implementation using rev-list/cherry would classify this CLEAN
        and re-publish an already-landed branch forever.
        """
        _git(repo, "checkout", "-b", "feat/y")
        (repo / "c.txt").write_text("payload\n")
        _git(repo, "add", "c.txt")
        _git(repo, "commit", "-m", "feat: c")
        _git(repo, "checkout", "main")
        # squash-merge: content lands, ancestry does NOT
        _git(repo, "merge", "--squash", "feat/y")
        _git(repo, "commit", "-m", "squash of feat/y")
        assert _git(repo, "rev-list", "--count", "main..feat/y") == "1"  # ancestry lies
        v = {x.branch: x for x in land_scanner.census(str(repo))}
        assert v["feat/y"].classification == "INTEGRATED"

    def test_conflicting_branch_reports_conflict_files(self, repo: Path):
        _git(repo, "checkout", "-b", "feat/z")
        (repo / "a.txt").write_text("branch side\n")
        _git(repo, "commit", "-am", "feat: branch edit")
        _git(repo, "checkout", "main")
        (repo / "a.txt").write_text("main side\n")
        _git(repo, "commit", "-am", "main edit")
        v = {x.branch: x for x in land_scanner.census(str(repo))}
        assert v["feat/z"].classification == "CONFLICTS"
        assert "a.txt" in v["feat/z"].conflict_files

    def test_scaffolding_branches_are_skipped(self, repo: Path):
        for name in ("archive/old", "agent-1234", "worktree-agent-abc", "backup/x"):
            _git(repo, "branch", name)
        names = {x.branch for x in land_scanner.census(str(repo))}
        assert not names & {"archive/old", "agent-1234", "worktree-agent-abc", "backup/x"}


class TestPublishContract:
    def test_publish_sql_carries_float_timestamp_and_ok_check(self, monkeypatch):
        """The two SurrealDB traps: epoch-float timestamp; success != HTTP 200."""
        captured: list[str] = []

        def fake_sql(query: str, timeout: float = 10.0):
            captured.append(query)
            return [{"status": "OK", "result": [{"id": "x"}]}]

        monkeypatch.setattr(land_scanner, "_sql", fake_sql)
        v = land_scanner.BranchVerdict("feat/x", "abc123def456", "CLEAN", ahead=2)
        assert land_scanner.publish_land_ready("/repo", v) is True
        q = captured[0]
        assert 'event_type = "land_ready"' in q
        # timestamp must be a bare float literal, not time::now()
        assert "time::now()" not in q
        assert "timestamp = " in q

    def test_seen_set_failure_is_fail_open(self, monkeypatch):
        """A broken seen-set must not silence discovery (returns not-seen)."""

        def broken_sql(query: str, timeout: float = 10.0):
            raise RuntimeError("db down")

        monkeypatch.setattr(land_scanner, "_sql", broken_sql)
        assert land_scanner.already_seen("feat/x", "abc") is False
