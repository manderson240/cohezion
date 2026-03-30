"""Tests for cohezion.cli.main — CLI framework, subcommands, and arg parsing.

Phase 3c coverage push.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


# Pre-mock missing modules that the CLI import chain requires
_MOCKED_MODULES = [
    "cohezion.models",
    "cohezion.models.model_registry",
]

for _mod_name in _MOCKED_MODULES:
    if _mod_name not in sys.modules:
        mock_mod = ModuleType(_mod_name)
        mock_mod.ModelRegistry = MagicMock()  # type: ignore[attr-defined]
        sys.modules[_mod_name] = mock_mod

from typer.testing import CliRunner

from cohezion.cli.main import app


runner = CliRunner()


class TestHelloCommand:
    """Tests for the hello subcommand."""

    def test_hello_default(self):
        """Should greet World by default."""
        result = runner.invoke(app, ["hello"])
        assert result.exit_code == 0
        assert "Hello" in result.output or "Cohezion" in result.output

    def test_hello_custom_name(self):
        """Should greet custom name."""
        result = runner.invoke(app, ["hello", "--name", "Anthropic"])
        assert result.exit_code == 0
        assert "Anthropic" in result.output

    def test_hello_no_color(self):
        """Should output without rich formatting."""
        result = runner.invoke(app, ["hello", "--no-color"])
        assert result.exit_code == 0
        assert "Hello" in result.output


class TestVersionCommand:
    """Tests for the version subcommand."""

    def test_version_runs(self):
        """Should display version info without error."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Cohezion" in result.output or "0.1.0" in result.output


class TestQuickstartCommand:
    """Tests for the quickstart subcommand."""

    def test_quickstart_runs(self):
        """Should display quickstart guide."""
        result = runner.invoke(app, ["quickstart"])
        assert result.exit_code == 0
        assert "Welcome" in result.output or "Quick Start" in result.output


class TestMainCallback:
    """Tests for the main callback (global options)."""

    def test_no_args_is_help(self):
        """Should show help when no args provided (exit 0 from Typer help)."""
        result = runner.invoke(app, [])
        # no_args_is_help=True makes Typer show help; exit code may be 0 or 2
        assert result.exit_code in (0, 2)
        assert "Cohezion" in result.output or "Usage" in result.output

    def test_verbose_flag(self):
        """Should accept --verbose flag."""
        result = runner.invoke(app, ["--verbose", "hello"])
        assert result.exit_code == 0

    def test_help_flag(self):
        """Should show help with --help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Cohezion" in result.output


class TestSwarmSubcommands:
    """Tests for swarm subcommand group."""

    def test_swarm_help(self):
        """Should show swarm help."""
        result = runner.invoke(app, ["swarm", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output or "swarm" in result.output.lower()

    def test_swarm_debate(self):
        """Should run debate subcommand."""
        result = runner.invoke(app, ["swarm", "debate", "AI safety"])
        assert result.exit_code == 0
        assert "Debate" in result.output or "debate" in result.output.lower()

    def test_swarm_simulate(self):
        """Should run simulate subcommand."""
        result = runner.invoke(app, ["swarm", "simulate", "--iterations", "10", "--agents", "5"])
        assert result.exit_code == 0
        assert "Simulation" in result.output or "simulate" in result.output.lower()


class TestDashboardSubcommands:
    """Tests for dashboard subcommand group."""

    def test_dashboard_start(self):
        """Should attempt to start dashboard."""
        result = runner.invoke(app, ["dashboard", "start", "--port", "9999"])
        assert result.exit_code == 0
        assert "9999" in result.output or "Dashboard" in result.output


class TestExploreSubcommands:
    """Tests for explore subcommand group."""

    def test_explore_skills(self):
        """Should show skills explorer."""
        result = runner.invoke(app, ["explore", "skills"])
        assert result.exit_code == 0

    def test_explore_journey(self):
        """Should show journey explorer."""
        result = runner.invoke(app, ["explore", "journey"])
        assert result.exit_code == 0


class TestOuroborosSubcommands:
    """Tests for ouroboros subcommand group."""

    def test_ouroboros_status(self):
        """Should show system status."""
        result = runner.invoke(app, ["ouroboros", "status"])
        assert result.exit_code == 0
        assert "Healthy" in result.output or "Status" in result.output

    def test_ouroboros_status_detailed(self):
        """Should show detailed status."""
        result = runner.invoke(app, ["ouroboros", "status", "--detailed"])
        assert result.exit_code == 0
        assert "Component" in result.output or "Swarm" in result.output

    def test_ouroboros_heal_dry_run(self):
        """Should simulate healing without action."""
        result = runner.invoke(app, ["ouroboros", "heal", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output or "simulated" in result.output.lower()

    def test_ouroboros_heal_no_flags(self):
        """Should trigger normal healing."""
        result = runner.invoke(app, ["ouroboros", "heal"])
        assert result.exit_code == 0
        assert "Heal" in result.output

    def test_ouroboros_history(self):
        """Should show evolution history."""
        result = runner.invoke(app, ["ouroboros", "history", "--limit", "5"])
        assert result.exit_code == 0
        assert "History" in result.output or "Timestamp" in result.output


class TestDemoSubcommands:
    """Tests for demo subcommand group."""

    def test_demo_nexus(self):
        """Should run nexus demo."""
        result = runner.invoke(app, ["demo", "nexus", "--complexity", "3"])
        assert result.exit_code == 0
        assert "Nexus" in result.output or "NEXUS" in result.output

    def test_demo_journey(self):
        """Should run journey demo."""
        result = runner.invoke(app, ["demo", "journey", "agent-001", "--steps", "10"])
        assert result.exit_code == 0
        assert "Journey" in result.output or "journey" in result.output.lower()
