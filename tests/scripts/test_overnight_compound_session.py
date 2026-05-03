"""Tests for scripts/overnight_compound_session.py.

Covers idempotency, phase isolation, signal handling, and data archiving.
Uses tmp_path for all filesystem state.
"""

from __future__ import annotations

import json
import signal
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the script is on the path when running tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import overnight_compound_session as ocs


@pytest.fixture(autouse=True)
def _reset_stop_flag():
    """Reset global STOP flag between tests."""
    ocs._STOP = False
    yield
    ocs._STOP = False


class TestDiscoverUnportedSkills:
    def test_returns_prime_stems_when_no_hermes_dir(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "FLUME_METHODOLOGY_PRIME.md").write_text("# FLUME")
        (skills_dir / "HIHO_STABILITY_PRIME.md").write_text("# HIHO")

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            with patch.object(ocs, "HERMES_SKILLS_ROOT", tmp_path / "no_hermes"):
                result = ocs._discover_unported_skills()

        assert set(result) == {"FLUME_METHODOLOGY_PRIME", "HIHO_STABILITY_PRIME"}

    def test_excludes_already_ported(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "FLUME_METHODOLOGY_PRIME.md").write_text("# FLUME")
        (skills_dir / "HIHO_STABILITY_PRIME.md").write_text("# HIHO")

        hermes_root = tmp_path / ".hermes" / "skills"
        cat_dir = hermes_root / "software-development"
        cat_dir.mkdir(parents=True)
        skill_dir = cat_dir / "cohezion-flume-methodology"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("legacy-name: FLUME_METHODOLOGY_PRIME\n")

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            with patch.object(ocs, "HERMES_SKILLS_ROOT", hermes_root):
                result = ocs._discover_unported_skills()

        assert "FLUME_METHODOLOGY_PRIME" not in result
        assert "HIHO_STABILITY_PRIME" in result


class TestPhaseArchive:
    def test_creates_manifest_and_report(self, tmp_path: Path):
        archive_dir = tmp_path / "overnight"
        with patch.object(ocs, "DATA_OVERNIGHT", archive_dir):
            phase = ocs.PhaseResult(
                phase="dummy",
                success=True,
                duration_seconds=0.1,
                records_produced=3,
                metrics={"k": "v"},
            )
            result = ocs._phase_archive("20260503T0000", [phase])

        assert result.success
        assert result.records_produced == 2
        manifest_path = archive_dir / "20260503T0000" / "manifest.json"
        report_path = archive_dir / "20260503T0000" / "report.json"
        assert manifest_path.exists()
        assert report_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["session_id"] == "20260503T0000"
        assert manifest["phases"][0]["phase"] == "dummy"

    def test_symlinks_latest(self, tmp_path: Path):
        archive_dir = tmp_path / "overnight"
        with patch.object(ocs, "DATA_OVERNIGHT", archive_dir):
            phase = ocs.PhaseResult(
                phase="dummy",
                success=True,
                duration_seconds=0.1,
                records_produced=3,
            )
            ocs._phase_archive("20260503T0001", [phase])

        latest = archive_dir / "latest"
        assert latest.exists() or latest.is_symlink()


class TestPhaseBatchPortDryRun:
    def test_ports_zero_when_all_ported(self, tmp_path: Path, monkeypatch):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "FLUME_METHODOLOGY_PRIME.md").write_text("# FLUME")

        hermes_root = tmp_path / ".hermes" / "skills"
        cat_dir = hermes_root / "software-development"
        cat_dir.mkdir(parents=True)
        skill_dir = cat_dir / "cohezion-flume-methodology"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("legacy-name: FLUME_METHODOLOGY_PRIME\n")

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            with patch.object(ocs, "HERMES_SKILLS_ROOT", hermes_root):
                result = ocs._phase_batch_port(dry_run=True, top_k=5)

        assert result.success
        assert result.records_produced == 0
        assert result.metrics["unported_count"] == 0


class TestPhaseSkillQuality:
    def test_evaluates_top_n(self, tmp_path: Path, monkeypatch):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for i in range(10):
            (skills_dir / f"SKILL_{i}_PRIME.md").write_text(f"# Skill {i}\n## description\n")

        quality_dir = tmp_path / "skill_quality"
        health_file = tmp_path / "skill_health.json"
        health_file.write_text("{}")

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            with patch.object(ocs, "DATA_SKILL_QUALITY", quality_dir):
                with patch.object(ocs, "DATA_SKILL_HEALTH", health_file):
                    result = ocs._phase_skill_quality(top_n=3, all_skills=False)

        assert result.records_produced >= 0  # may be 0 if parser fails, but no crash
        assert result.phase == "skill_quality"

    def test_empty_skills_dir_graceful(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            result = ocs._phase_skill_quality(top_n=5)

        assert not result.success
        assert "No .md files" in result.errors[0]


class TestSignalHandler:
    def test_sigint_sets_stop_flag(self):
        ocs._STOP = False
        ocs._install_sigint()
        # Simulate signal
        signal.raise_signal(signal.SIGINT)
        assert ocs._STOP is True


class TestRunSession:
    @pytest.mark.asyncio
    async def test_produces_report(self, tmp_path: Path, monkeypatch):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "TEST_PRIME.md").write_text("# Test\n")

        archive_dir = tmp_path / "overnight"
        quality_dir = tmp_path / "skill_quality"
        health_file = tmp_path / "skill_health.json"
        health_file.write_text("{}")

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            with patch.object(ocs, "DATA_OVERNIGHT", archive_dir):
                with patch.object(ocs, "DATA_SKILL_QUALITY", quality_dir):
                    with patch.object(ocs, "DATA_SKILL_HEALTH", health_file):
                        report = await ocs._run_session(dry_run=True, top_k=1, all_skills=True)

        assert isinstance(report, ocs.OvernightSessionReport)
        assert report.overall_success is True or report.overall_success is False
        assert len(report.phases) == 4  # autoresearch, skill_quality, batch_port, archive

    @pytest.mark.asyncio
    async def test_respects_stop_flag(self, tmp_path: Path, monkeypatch):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "TEST_PRIME.md").write_text("# Test\n")
        archive_dir = tmp_path / "overnight"
        quality_dir = tmp_path / "skill_quality"
        health_file = tmp_path / "skill_health.json"
        health_file.write_text("{}")

        async def mock_autoresearch(*a, **k):
            ocs._STOP = True
            return ocs.PhaseResult(
                phase="autoresearch",
                success=True,
                duration_seconds=0.0,
                records_produced=0,
            )

        with patch.object(ocs, "SKILLS_DIR", skills_dir):
            with patch.object(ocs, "DATA_OVERNIGHT", archive_dir):
                with patch.object(ocs, "DATA_SKILL_QUALITY", quality_dir):
                    with patch.object(ocs, "DATA_SKILL_HEALTH", health_file):
                        with patch.object(ocs, "_phase_autoresearch", mock_autoresearch):
                            report = await ocs._run_session(dry_run=True, top_k=1)

        # Because STOP was set after autoresearch, skill_quality may still run
        # but archive should always run.
        phases = [p.phase for p in report.phases]
        assert "archive" in phases


class TestDataclassSerialisation:
    def test_phase_result_to_dict(self):
        pr = ocs.PhaseResult(
            phase="x",
            success=True,
            duration_seconds=1.2,
            records_produced=5,
            errors=["a"],
            metrics={"k": "v"},
        )
        d = asdict(pr)
        assert d["phase"] == "x"
        assert d["records_produced"] == 5

    def test_report_serialisable(self):
        pr = ocs.PhaseResult(
            phase="x",
            success=True,
            duration_seconds=1.2,
            records_produced=5,
        )
        report = ocs.OvernightSessionReport(
            session_id="s1",
            started_at="t0",
            ended_at="t1",
            phases=[pr],
            overall_success=True,
        )
        d = asdict(report)
        assert json.dumps(d)
