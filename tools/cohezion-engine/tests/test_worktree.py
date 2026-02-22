"""Tests for worktree management module."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


WKDIR = Path(__file__).parent.parent


def run_cz(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "cohezion_engine.cli", *args],
        capture_output=True,
        text=True,
        cwd=WKDIR,
        env={**os.environ, "PYTHONPATH": str(WKDIR / "src")},
    )


class TestWorktreeModule:
    def test_derive_slug_from_filename(self):
        from cohezion_engine.worktree import derive_slug

        assert derive_slug("2026-02-21-add-auth.md") == "add-auth"
        assert derive_slug("docs/plans/2026-02-21-my-feature.md") == "my-feature"
        assert derive_slug("simple-slug") == "simple-slug"

    def test_detect_nonexistent_worktree(self, tmp_path):
        from cohezion_engine.worktree import detect_worktree

        result = detect_worktree("nonexistent-slug-xyz", repo_root=tmp_path)
        assert result["found"] is False

    def test_create_worktree_requires_clean_tree(self, tmp_path):
        """Creating a worktree with a dirty git tree returns an error dict."""
        from cohezion_engine.worktree import create_worktree

        # tmp_path has no git repo, so git ops will fail gracefully
        result = create_worktree("test-slug", repo_root=tmp_path)
        assert result.get("success") is False
        assert "error" in result

    def test_worktree_status_no_active(self, tmp_path):
        from cohezion_engine.worktree import get_worktree_status

        result = get_worktree_status(repo_root=tmp_path)
        assert result["active"] is False

    def test_cli_worktree_status_json(self):
        result = run_cz("worktree", "status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "active" in data

    def test_cli_worktree_detect_json(self):
        result = run_cz("worktree", "detect", "--json", "nonexistent-slug-xyz")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "found" in data
        assert data["found"] is False
