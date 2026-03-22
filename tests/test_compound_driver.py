"""Tests for the compound engineering driver script."""

from __future__ import annotations

# Import from the scripts directory
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from cohezion.core.instruction_expander import InstructionExpander
from cohezion.core.template_engine import SkillSpec
from scripts.compound_driver import (
    build_team_plan,
    parse_args,
    run_compound_cycle,
    select_skills,
)


# ---------------------------------------------------------------------------
# Skill selection
# ---------------------------------------------------------------------------


class TestSkillSelection:
    def test_select_skills_returns_list(self):
        """select_skills returns a list of SkillSpec."""
        specs = select_skills(3)
        assert isinstance(specs, list)
        assert len(specs) <= 3
        for s in specs:
            assert isinstance(s, SkillSpec)

    def test_select_skills_prefers_instructions(self):
        """Skills with instructions are returned first."""
        specs = select_skills(5)
        # First skills should have instructions (if any exist)
        with_instr = [s for s in specs if s.instructions]
        without_instr = [s for s in specs if not s.instructions]
        # All with-instructions should appear before without
        if with_instr and without_instr:
            last_instr_idx = max(specs.index(s) for s in with_instr)
            first_no_instr_idx = min(specs.index(s) for s in without_instr)
            assert last_instr_idx < first_no_instr_idx


# ---------------------------------------------------------------------------
# Team plan building
# ---------------------------------------------------------------------------


class TestBuildTeamPlan:
    def test_build_team_plan(self):
        """build_team_plan creates a TeamPlan from specs."""
        specs = select_skills(2)
        if not specs:
            pytest.skip("No PRIME skills available")
        expander = InstructionExpander()
        plan = build_team_plan(specs, expander)
        assert plan.name == "compound-cycle"
        assert len(plan.tasks) == len(specs)
        for task in plan.tasks:
            assert task.id.startswith("skill-")


# ---------------------------------------------------------------------------
# Full cycle (dry-run)
# ---------------------------------------------------------------------------


class TestDryRunCycle:
    @pytest.mark.asyncio
    async def test_dry_run_completes(self):
        """Dry-run cycle completes without errors."""
        report = await run_compound_cycle(num_skills=2, dry_run=True, threshold=1.0)
        assert isinstance(report, dict)
        assert report["mode"] == "dry-run"

    @pytest.mark.asyncio
    async def test_dry_run_produces_report(self):
        """Dry-run report contains expected keys."""
        report = await run_compound_cycle(num_skills=2, dry_run=True, threshold=1.0)
        assert "skills_selected" in report
        assert "total_steps" in report
        assert "tasks_completed" in report
        assert "compound_score_delta" in report
        assert "total_cycle_duration_s" in report

    @pytest.mark.asyncio
    async def test_threshold_controls_refinement(self):
        """With threshold=999, no refinements are applied."""
        report = await run_compound_cycle(num_skills=2, dry_run=True, threshold=999.0)
        assert report["refinements_applied"] == 0

    @pytest.mark.asyncio
    async def test_zero_threshold_allows_refinement(self):
        """With threshold=0.0, refinement is attempted."""
        report = await run_compound_cycle(num_skills=2, dry_run=True, threshold=0.0)
        # May or may not find suggestions, but should not error
        assert "refinements_applied" in report


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_default_args(self):
        """Default arguments are sensible."""
        args = parse_args([])
        assert args.skills == 5
        assert args.threshold == 0.5
        assert args.dry_run is False
        assert args.model == "phi3:mini"

    def test_dry_run_flag(self):
        """--dry-run sets the flag."""
        args = parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_custom_args(self):
        """Custom arguments are parsed correctly."""
        args = parse_args(["--skills", "10", "--model", "qwen3:8b", "--threshold", "0.7"])
        assert args.skills == 10
        assert args.model == "qwen3:8b"
        assert args.threshold == 0.7
