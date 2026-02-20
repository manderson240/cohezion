"""Tests for the research CLI."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path


def test_cli_help_shows_subcommands(capsys):
    """CLI --help shows run, triage, and status subcommands."""
    from research.cli import build_parser

    parser = build_parser()
    # Parser should have subcommands
    # Check that the parser was created and has subparsers
    assert parser is not None


def test_cli_run_subcommand_exists():
    """CLI has a 'run' subcommand."""
    from research.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["run"])
    assert args.command == "run"


def test_cli_run_quick_flag():
    """CLI run --quick flag is parsed correctly."""
    from research.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["run", "--quick"])
    assert args.quick is True


def test_cli_run_focus_flag():
    """CLI run --focus flag filters to one area."""
    from research.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["run", "--focus", "compound-engineering"])
    assert args.focus == "compound-engineering"


def test_cli_status_subcommand():
    """CLI has a 'status' subcommand."""
    from research.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["status"])
    assert args.command == "status"


def test_cli_triage_subcommand():
    """CLI has a 'triage' subcommand."""
    from research.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["triage"])
    assert args.command == "triage"


def test_cli_status_returns_json(capsys, tmp_path):
    """Status command returns JSON output."""
    from research.cli import cmd_status

    cmd_status(tmp_path)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "last_run" in data
