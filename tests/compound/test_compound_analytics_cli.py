"""Tests for compound analytics CLI."""

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "compound_analytics_cli.py"


def _run_cli(cmd: str, *extra_args: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), cmd, *extra_args],
        capture_output=True,
        text=True,
        cwd=str(SCRIPT.parent.parent),
    )
    return result.returncode, result.stdout + result.stderr


class TestCompoundAnalyticsCLI:
    def test_status_command_exits_zero(self):
        rc, out = _run_cli("status")
        assert rc == 0, f"Exit code {rc}: {out}"

    def test_status_shows_hiho(self):
        rc, out = _run_cli("status")
        assert "HIHO" in out or "COMPOUND" in out

    def test_health_command_exits_zero(self):
        rc, out = _run_cli("health")
        assert rc == 0, f"Exit code {rc}: {out}"

    def test_health_shows_healthy(self):
        rc, out = _run_cli("health")
        assert "HEALTHY" in out

    def test_recommend_command_exits_zero(self):
        rc, out = _run_cli("recommend", "--n", "2")
        assert rc == 0, f"Exit code {rc}: {out}"

    def test_no_command_shows_help(self):
        rc, out = _run_cli("--help")
        # Help exits with 0
        assert "status" in out or "recommend" in out
