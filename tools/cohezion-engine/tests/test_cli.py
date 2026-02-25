"""Tests for the cohezion-engine CLI entry point."""

import json
import subprocess
import sys
from pathlib import Path


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


class TestContextEstimateSubcommand:
    def test_estimate_fits_when_tokens_within_budget(self):
        result = run_cz("context", "estimate", "--tokens", "10000", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "fits" in data
        assert "status_after" in data
        assert "percentage_after" in data

    def test_estimate_fits_false_when_tokens_overflow(self):
        # 199k tokens would push most sessions to CLEAR_NEEDED
        result = run_cz("context", "estimate", "--tokens", "199000", "--limit", "200000", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "fits" in data
        assert "status_after" in data

    def test_context_backward_compat_json_flag_still_works(self):
        """cz context --json must still work after converting to group."""
        result = run_cz("context", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert "percentage" in data

    def test_estimate_requires_tokens_flag(self):
        result = run_cz("context", "estimate")
        assert result.returncode != 0


class TestContextRichOutput:
    def test_human_output_shows_velocity(self):
        result = run_cz("context")
        assert result.returncode == 0
        # Rich output should include velocity info
        assert "Velocity" in result.stdout or "velocity" in result.stdout.lower()

    def test_human_output_shows_turns_remaining(self):
        result = run_cz("context")
        assert result.returncode == 0
        assert "urn" in result.stdout  # "Turns remaining" or "turns"

    def test_human_output_shows_status_bracket(self):
        result = run_cz("context")
        assert result.returncode == 0
        # New format: "Context: X.X% [STATUS]"
        assert "%" in result.stdout
        assert any(s in result.stdout for s in ["[OK]", "[WARNING]", "[CLEAR_NEEDED]", "[UNKNOWN]"])

    def test_json_output_unchanged_structure(self):
        result = run_cz("context", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert "percentage" in data
        assert "output_tokens" in data
        assert "velocity_tokens_per_turn" in data
        assert "turns_remaining" in data
