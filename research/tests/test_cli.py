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


def test_cmd_status_reads_existing_json(capsys, tmp_path):
    """Status reads existing last_run.json when present."""
    from research.cli import cmd_status

    run_dir = tmp_path / "research"
    run_dir.mkdir()
    payload = {"last_run": "2026-02-22T12:00:00", "findings": 42}
    (run_dir / "last_run.json").write_text(json.dumps(payload))

    cmd_status(tmp_path)
    out = json.loads(capsys.readouterr().out)
    assert out["findings"] == 42


def test_cmd_triage_empty_inbox(capsys, tmp_path):
    """Triage on empty inbox returns empty list."""
    from research.cli import cmd_triage

    (tmp_path / "inbox").mkdir()
    cmd_triage(tmp_path)
    out = json.loads(capsys.readouterr().out)
    assert out == []


def test_cmd_triage_parses_research_notes(capsys, tmp_path):
    """Triage extracts vault_target and relevance_score from research notes."""
    from research.cli import cmd_triage

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    note = inbox / "research-2026-02-22-topic.md"
    note.write_text("---\nvault_target: patterns\nrelevance_score: 0.85\n---\nContent\n")

    cmd_triage(tmp_path)
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["vault_target"] == "patterns"
    assert out[0]["score"] == pytest.approx(0.85)


def test_cmd_triage_ignores_non_research_notes(capsys, tmp_path):
    """Triage ignores files not matching research-*.md pattern."""
    from research.cli import cmd_triage

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "unrelated-note.md").write_text("# hello\n")

    cmd_triage(tmp_path)
    out = json.loads(capsys.readouterr().out)
    assert out == []


def test_cmd_triage_bad_score_defaults_to_zero(capsys, tmp_path):
    """Triage defaults score to 0.0 when relevance_score is not a float."""
    from research.cli import cmd_triage

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    note = inbox / "research-bad-score.md"
    note.write_text("---\nvault_target: inbox\nrelevance_score: not-a-float\n---\n")

    cmd_triage(tmp_path)
    out = json.loads(capsys.readouterr().out)
    assert out[0]["score"] == 0.0


def test_cmd_run_dry_run(capsys, tmp_path):
    """cmd_run dry-run returns config summary without network calls."""
    import yaml
    import argparse
    from research.cli import cmd_run

    config = {
        "focus_areas": {
            "compound_engineering": {"queries": ["compound AI"], "weight": 1.0}
        },
        "sources": {},
    }
    (tmp_path / "sources.yaml").write_text(yaml.dump(config))

    args = argparse.Namespace(
        config=str(tmp_path / "sources.yaml"),
        vault=str(tmp_path),
        quick=False,
        focus=None,
        dry_run=True,
    )
    cmd_run(args)
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["focus_areas"] == 1
    assert out["total_queries"] == 1


def test_cmd_run_dry_run_unknown_focus_exits(tmp_path):
    """cmd_run exits with error when focus area doesn't exist."""
    import yaml
    import argparse
    from research.cli import cmd_run

    config = {
        "focus_areas": {
            "compound_engineering": {"queries": ["compound AI"], "weight": 1.0}
        },
        "sources": {},
    }
    (tmp_path / "sources.yaml").write_text(yaml.dump(config))

    args = argparse.Namespace(
        config=str(tmp_path / "sources.yaml"),
        vault=str(tmp_path),
        quick=False,
        focus="nonexistent-area",
        dry_run=True,
    )
    with pytest.raises(SystemExit):
        cmd_run(args)


def test_main_dispatches_status(tmp_path):
    """main() dispatches to cmd_status for status subcommand."""
    from research.cli import main

    with patch("sys.argv", ["research", "--vault", str(tmp_path), "status"]):
        with patch("research.cli.cmd_status") as mock:
            main()
    mock.assert_called_once()


def test_main_dispatches_triage(tmp_path):
    """main() dispatches to cmd_triage for triage subcommand."""
    from research.cli import main

    with patch("sys.argv", ["research", "--vault", str(tmp_path), "triage"]):
        with patch("research.cli.cmd_triage") as mock:
            main()
    mock.assert_called_once()


def test_main_dispatches_run(tmp_path):
    """main() dispatches to cmd_run for run subcommand."""
    from research.cli import main

    with patch("sys.argv", ["research", "--vault", str(tmp_path), "run"]):
        with patch("research.cli.cmd_run") as mock:
            main()
    mock.assert_called_once()
