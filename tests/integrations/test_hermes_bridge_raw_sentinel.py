"""Tests for the hermes_mcp_bridge._handle_run_cli !raw sentinel (WS3, 2026-06-03)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from cohezion.integrations.hermes_mcp_bridge import _handle_run_cli


def test_default_path_uses_cohezion_prefix():
    """Without the sentinel, _handle_run_cli must still route through
    `python -m cohezion`. We verify by calling with a subcommand that
    does NOT exist; the returned subprocess result will be non-zero with
    a cohezion CLI usage message."""
    result = _handle_run_cli({"command": "definitely_not_a_real_subcommand_xyz", "timeout": 10})
    # Should fail with a cohezion CLI error (not a bash error)
    assert "success" in result
    assert result["success"] is False
    # The cohezion CLI prints "usage: cohezion [-h]" on unknown subcommands
    combined = (result.get("stdout", "") + result.get("stderr", "")).lower()
    assert "cohezion" in combined or "usage" in combined


def test_raw_sentinel_runs_bash_c():
    """`!raw <cmd>` must run the command via bash -c, NOT python -m cohezion.
    The simplest test: `!raw echo ok` should succeed and produce 'ok'."""
    result = _handle_run_cli({"command": "!raw echo ok", "timeout": 10})
    assert result["success"] is True
    assert "ok" in result["stdout"]


def test_raw_sentinel_empty_command_errors():
    """`!raw ` with nothing after the sentinel must error, not silently
    exec bash with empty args."""
    result = _handle_run_cli({"command": "!raw ", "timeout": 5})
    assert "error" in result
    assert "!raw" in result["error"]


def test_raw_sentinel_can_run_python_script():
    """End-to-end smoke: `!raw python3 -c 'print(2+2)'` should output 4
    via bash, proving the sentinel bypasses the cohezion prefix."""
    result = _handle_run_cli({"command": "!raw python3 -c 'print(2+2)'", "timeout": 10})
    assert result["success"] is True
    assert "4" in result["stdout"]


def test_default_path_still_works_for_real_subcommand():
    """Smoke: `!raw pwd` should work and return a path-like string."""
    result = _handle_run_cli({"command": "!raw pwd", "timeout": 5})
    assert result["success"] is True
    assert "/" in result["stdout"] or "cohezion" in result["stdout"]
