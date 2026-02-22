"""Tests for plan lifecycle module."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


WKDIR = Path(__file__).parent.parent


def run_cz(*args: str, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(WKDIR / "src"), "COHEZION_SESSION_ID": "test-plan-session"}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "cohezion_engine.cli", *args],
        capture_output=True,
        text=True,
        cwd=WKDIR,
        env=env,
    )


SAMPLE_PLAN = """\
# Test Plan

Created: 2026-02-21
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

## Summary

**Goal:** Test plan for testing.
"""


class TestPlanModule:
    def test_parse_plan_frontmatter(self, tmp_path):
        from cohezion_engine.plan import parse_plan_frontmatter

        plan_file = tmp_path / "test.md"
        plan_file.write_text(SAMPLE_PLAN)
        data = parse_plan_frontmatter(plan_file)
        assert data["Status"] == "PENDING"
        assert data["Approved"] == "Yes"
        assert data["Iterations"] == "0"
        assert data["Worktree"] == "Yes"

    def test_parse_plan_returns_empty_for_missing_file(self):
        from cohezion_engine.plan import parse_plan_frontmatter

        data = parse_plan_frontmatter(Path("/nonexistent/plan.md"))
        assert data == {}

    def test_register_plan_creates_association(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-reg-session")
        from cohezion_engine import plan as plan_mod
        import importlib
        importlib.reload(plan_mod)

        plan_file = tmp_path / "my_plan.md"
        plan_file.write_text(SAMPLE_PLAN)
        plan_mod.register_plan(str(plan_file), "PENDING", base_dir=tmp_path)

        # Verify association was persisted
        info = plan_mod.get_plan_status(base_dir=tmp_path)
        assert info["path"] == str(plan_file)
        assert info["registered_status"] == "PENDING"

    def test_get_plan_status_includes_frontmatter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-status-session")
        from cohezion_engine import plan as plan_mod
        import importlib
        importlib.reload(plan_mod)

        plan_file = tmp_path / "plan.md"
        plan_file.write_text(SAMPLE_PLAN)
        plan_mod.register_plan(str(plan_file), "PENDING", base_dir=tmp_path)

        info = plan_mod.get_plan_status(base_dir=tmp_path)
        assert "frontmatter" in info
        assert info["frontmatter"]["Status"] == "PENDING"

    def test_get_plan_status_returns_none_when_no_plan(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-empty-session")
        from cohezion_engine import plan as plan_mod
        import importlib
        importlib.reload(plan_mod)

        info = plan_mod.get_plan_status(base_dir=tmp_path)
        assert info is None

    def test_cli_plan_register(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(SAMPLE_PLAN)
        result = run_cz("plan", "register", str(plan_file), "PENDING",
                        env_overrides={"COHEZION_SESSION_ID": "test-cli-plan"})
        assert result.returncode == 0

    def test_cli_plan_status_json(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(SAMPLE_PLAN)
        # Register first
        run_cz("plan", "register", str(plan_file), "PENDING",
                env_overrides={"COHEZION_SESSION_ID": "test-cli-status"})
        result = run_cz("plan", "status", "--json",
                        env_overrides={"COHEZION_SESSION_ID": "test-cli-status"})
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "path" in data
