"""The pre-commit gitignore gate must inspect STAGED files, not tracked files.

`git ls-files -i -c --exclude-standard` lists every TRACKED file matching
.gitignore, repo-wide -- `-c` means "cached", not "staged". The hook used it
directly while its comment claimed to check "ignored files that are somehow
staged", so it fired on 190 pre-existing tracked-but-ignored files and blocked
EVERY commit in the repo regardless of content.

These tests build throwaway git repos, so they assert the hook's behaviour
rather than re-stating its implementation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "pre-commit.py"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _run_hook(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HOOK)], cwd=repo, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo containing a tracked file that .gitignore later started matching."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")

    # Track it FIRST, while nothing is ignored...
    (tmp_path / "legacy.log").write_text("pre-existing tracked artifact\n")
    _git(tmp_path, "add", "legacy.log")
    _git(tmp_path, "commit", "-qm", "seed")

    # ...then start ignoring it. Now it is tracked AND ignored, but not staged --
    # exactly the repo-wide condition that jammed the real hook.
    (tmp_path / ".gitignore").write_text("*.log\n")
    _git(tmp_path, "add", ".gitignore")
    _git(tmp_path, "commit", "-qm", "ignore logs")
    return tmp_path


def test_tracked_but_ignored_file_does_not_block_an_unrelated_commit(
    repo: Path,
) -> None:
    """The regression guard: this is what blocked every commit in the repo."""
    assert _git(repo, "ls-files", "-i", "-c", "--exclude-standard").stdout.strip(), (
        "fixture is not exercising the bug: no tracked-but-ignored file present"
    )

    (repo / "feature.py").write_text("x = 1\n")
    _git(repo, "add", "feature.py")

    result = _run_hook(repo)
    assert result.returncode == 0, (
        "hook blocked a clean commit because an UNRELATED tracked file matches "
        f".gitignore.\nstdout:\n{result.stdout}"
    )


def test_an_actually_staged_ignored_file_is_still_blocked(repo: Path) -> None:
    """Discriminating: the gate must keep working, not be neutered.

    A fix that simply deleted the check would pass the test above and fail here.
    """
    (repo / "secret.log").write_text("force-added\n")
    _git(repo, "add", "-f", "secret.log")

    result = _run_hook(repo)
    assert result.returncode != 0, "force-added ignored file should be blocked"
    assert "secret.log" in result.stdout


def test_block_message_names_only_the_staged_offender(repo: Path) -> None:
    """The old hook dumped 190 irrelevant paths, burying the real one."""
    (repo / "secret.log").write_text("force-added\n")
    _git(repo, "add", "-f", "secret.log")

    result = _run_hook(repo)
    assert "secret.log" in result.stdout
    assert "legacy.log" not in result.stdout, (
        "unstaged tracked-but-ignored file leaked into the block message"
    )
