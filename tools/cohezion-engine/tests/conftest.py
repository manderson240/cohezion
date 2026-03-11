"""Shared pytest fixtures for cohezion-engine tests."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with an initial commit on 'main'."""
    env_overrides = {"GIT_CONFIG_NOSYSTEM": "1", "HOME": str(tmp_path)}

    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )

    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "README.md"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "Initial commit"],
        check=True,
        capture_output=True,
    )

    # Ensure we're on a branch named 'main' (git default varies)
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "branch", "--show-current"],
        capture_output=True,
        text=True,
    )
    current_branch = result.stdout.strip()
    if current_branch != "main":
        subprocess.run(
            ["git", "-C", str(tmp_path), "branch", "-m", current_branch, "main"],
            check=True,
            capture_output=True,
        )

    return tmp_path
