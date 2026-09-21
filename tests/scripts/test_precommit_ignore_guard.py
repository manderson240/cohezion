"""Discriminating tests for the gitignore guard in scripts/hooks/pre-commit.py.

The guard claims to block commits that STAGE an ignored file. Until 2026-09-21 it ran
`git ls-files -i -c` with no pathspec, which lists every TRACKED ignored file, so any tree
carrying tracked-then-ignored files could not commit anything. Each test builds a real git
repo, so the pathspec semantics are exercised, not mocked.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "pre-commit.py"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _hook_blocks(repo: Path) -> bool:
    result = subprocess.run([sys.executable, str(HOOK)], cwd=repo, capture_output=True, text=True)
    return result.returncode != 0


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo whose tree already carries a tracked-then-ignored file (the observed state)."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "tracked.log").write_text("keep\n")
    _git(tmp_path, "add", "tracked.log")
    _git(tmp_path, "commit", "-qm", "init")
    (tmp_path / ".gitignore").write_text("*.log\nx1.py\n")
    (tmp_path / "x1.py").write_text("tracked but ignored\n")
    _git(tmp_path, "add", "-f", ".gitignore", "x1.py")
    _git(tmp_path, "commit", "-qm", "ignore")
    return tmp_path


def test_unrelated_staged_file_is_not_blocked_by_tracked_ignored_files(repo: Path) -> None:
    """The regression: the pre-fix hook blocked this, citing tracked.log / x1.py."""
    (repo / "a.py").write_text("x = 1\n")
    _git(repo, "add", "a.py")
    assert not _hook_blocks(repo)


def test_nothing_staged_is_not_blocked(repo: Path) -> None:
    assert not _hook_blocks(repo)


def test_force_added_ignored_file_is_blocked(repo: Path) -> None:
    """The guard's real job must survive the fix."""
    (repo / "new.log").write_text("artifact\n")
    _git(repo, "add", "-f", "new.log")
    assert _hook_blocks(repo)


def test_staging_a_tracked_ignored_file_is_blocked(repo: Path) -> None:
    (repo / "tracked.log").write_text("keep\nmore\n")
    _git(repo, "add", "tracked.log")
    assert _hook_blocks(repo)


def test_glob_characters_in_a_staged_name_are_literal(repo: Path) -> None:
    """`x[1].py` read as a glob matches the tracked-ignored `x1.py` and falsely blocks.

    Only --literal-pathspecs makes this pass; the other tests are indifferent to it.
    """
    (repo / "x[1].py").write_text("y = 2\n")
    _git(repo, "add", "x[1].py")
    assert not _hook_blocks(repo)
