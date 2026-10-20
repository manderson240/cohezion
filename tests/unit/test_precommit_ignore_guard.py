"""Discriminating tests for the gitignore guard in scripts/hooks/pre-commit.py.

The guard claims to block commits that STAGE an ignored file. Until 2026-09-21 it ran
`git ls-files -i -c` with no pathspec, which lists every TRACKED ignored file, so any tree
carrying tracked-then-ignored files could not commit anything. Each test builds a real git
repo, so git's path handling is exercised, not mocked.

Lives in tests/unit/ deliberately: tests/scripts/ runs only in a continue-on-error CI step and
not at all in automerge_guard.sh, so a regression there would gate nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "pre-commit.py"
GUARD_MSG = "match .gitignore patterns"
SECRET_MSG = "Secrets detected"


@pytest.fixture
def git_env(tmp_path: Path) -> dict[str, str]:
    """Isolate from the machine's git config: a global core.excludesFile (e.g. `*.py`) would
    otherwise change which fixture files are ignored and make cases pass vacuously."""
    home = tmp_path / "home"
    home.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(HOME=str(home), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return env


def _git(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout


def _stage(repo: Path, env: dict[str, str], name: str, *, force: bool = False) -> None:
    _git(repo, env, "add", *(["-f"] if force else []), "--", name)
    staged = _git(repo, env, "diff", "--cached", "--name-only", "-z").split("\0")
    assert name in staged, f"fixture did not stage {name!r}: {staged}"  # no vacuous passes


def _run_hook(repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)], cwd=repo, env=env, capture_output=True, text=True
    )


def _assert_blocked_by(result: subprocess.CompletedProcess[str], message: str) -> None:
    """A crash also exits non-zero; require the guard's own message so a traceback cannot
    pass for a block."""
    assert result.returncode == 1, result.stderr
    assert message in result.stdout, (result.stdout, result.stderr)


@pytest.fixture
def repo(tmp_path: Path, git_env: dict[str, str]) -> Path:
    """A repo whose tree already carries tracked-then-ignored files (the observed state)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, git_env, "init", "-q")
    _git(repo, git_env, "config", "user.email", "t@t")
    _git(repo, git_env, "config", "user.name", "t")
    (repo / "tracked.log").write_text("keep\n")
    _git(repo, git_env, "add", "tracked.log")
    _git(repo, git_env, "commit", "-qm", "init")
    (repo / ".gitignore").write_text("*.log\nx1.py\n")
    (repo / "x1.py").write_text("tracked but ignored\n")
    _git(repo, git_env, "add", "-f", ".gitignore", "x1.py")
    _git(repo, git_env, "commit", "-qm", "ignore")
    return repo


def test_unrelated_staged_file_is_not_blocked_by_tracked_ignored_files(
    repo: Path, git_env: dict[str, str]
) -> None:
    """The regression: the pre-fix hook blocked this, citing tracked.log / x1.py."""
    (repo / "a.py").write_text("x = 1\n")
    _stage(repo, git_env, "a.py")
    result = _run_hook(repo, git_env)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_nothing_staged_is_not_blocked(repo: Path, git_env: dict[str, str]) -> None:
    assert _run_hook(repo, git_env).returncode == 0


def test_force_added_ignored_file_is_blocked(repo: Path, git_env: dict[str, str]) -> None:
    """The guard's real job must survive the fix."""
    (repo / "new.log").write_text("artifact\n")
    _stage(repo, git_env, "new.log", force=True)
    _assert_blocked_by(_run_hook(repo, git_env), GUARD_MSG)


def test_staging_a_tracked_ignored_file_is_blocked(repo: Path, git_env: dict[str, str]) -> None:
    (repo / "tracked.log").write_text("keep\nmore\n")
    _stage(repo, git_env, "tracked.log")
    _assert_blocked_by(_run_hook(repo, git_env), GUARD_MSG)


def test_glob_characters_in_a_staged_name_are_literal(repo: Path, git_env: dict[str, str]) -> None:
    """`x[1].py` read as a glob pathspec matches the tracked-ignored `x1.py` and falsely blocks."""
    (repo / "x[1].py").write_text("y = 2\n")
    _stage(repo, git_env, "x[1].py")
    assert _run_hook(repo, git_env).returncode == 0


@pytest.mark.parametrize("name", ["café.log", "t\tx.log", 'q"uote.log'])
def test_force_added_ignored_file_with_a_git_quoted_name_is_blocked(
    repo: Path, git_env: dict[str, str], name: str
) -> None:
    """Without -z, git prints these names quoted ("caf\\303\\251.log"), the quoted string
    matches nothing, and the guard silently passes. Found by adversarial review 2026-09-21:
    the first scoped fix let exactly these through while the unscoped original caught them."""
    (repo / name).write_text("artifact\n")
    _stage(repo, git_env, name, force=True)
    _assert_blocked_by(_run_hook(repo, git_env), GUARD_MSG)


def test_secret_in_a_git_quoted_filename_is_still_scanned(
    repo: Path, git_env: dict[str, str]
) -> None:
    """Same root cause, pre-existing: a quoted name failed os.path.isfile, so its content was
    never read and a token in `héllo.txt` passed the secret scan."""
    (repo / "héllo.txt").write_text("token = ghp_" + "a" * 36 + "\n")
    _stage(repo, git_env, "héllo.txt")
    _assert_blocked_by(_run_hook(repo, git_env), SECRET_MSG)
