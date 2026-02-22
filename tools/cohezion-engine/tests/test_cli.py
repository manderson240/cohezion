"""Tests for the cohezion-engine CLI entry point."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cz(*args: str) -> subprocess.CompletedProcess:
    """Run the cz CLI with given args and return the result."""
    project_root = Path(__file__).parent.parent
    return subprocess.run(
        [sys.executable, "-m", "cohezion_engine.cli", *args],
        capture_output=True,
        text=True,
        cwd=project_root,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(project_root / "src"),
        },
    )


class TestCLIHelp:
    def test_help_shows_subcommands(self):
        result = run_cz("--help")
        assert result.returncode == 0
        assert "context" in result.stdout
        assert "session" in result.stdout
        assert "worktree" in result.stdout
        assert "plan" in result.stdout

    def test_version_shows_version(self):
        result = run_cz("--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_status_json_output(self):
        result = run_cz("status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "version" in data
        assert data["version"] == "0.1.0"
        assert "config_dir" in data

    def test_status_human_output(self):
        result = run_cz("status")
        assert result.returncode == 0
        assert "cohezion-engine" in result.stdout.lower() or "version" in result.stdout.lower()

    def test_unknown_command_exits_nonzero(self):
        result = run_cz("nonexistent-command")
        assert result.returncode != 0
