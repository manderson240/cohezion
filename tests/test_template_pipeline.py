"""Tests for the dynamic template pipeline.

Covers TemplatePipeline (batch generation, regeneration, registry sync,
stale detection), VersionTracker (record, check, retrieve), config template
version header, and factory auto-regeneration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.agents.template_pipeline import (
    GenerationResult,
    StaleAgent,
    SyncResult,
    TemplatePipeline,
)
from cohezion.agents.version_tracker import VersionTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_skills(tmp_path: Path) -> Path:
    """Create a temp skills directory with test skill files."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    for i in range(3):
        md = skills_dir / f"SKILL_{i}_PRIME.md"
        md.write_text(
            f"# SKILL: SKILL_{i}_PRIME\n\n## VERSION\n\n1.{i}\n\n## INSTRUCTION\n\n1. Do step one\n2. Do step two\n",
            encoding="utf-8",
        )
    # One skill without instructions
    no_instr = skills_dir / "NO_INSTRUCTIONS_PRIME.md"
    no_instr.write_text(
        "# SKILL: NO_INSTRUCTIONS_PRIME\n\n## VERSION\n\n1.0\n",
        encoding="utf-8",
    )
    return skills_dir


@pytest.fixture()
def versions_path(tmp_path: Path) -> Path:
    """Return a temp path for versions.json."""
    generated = tmp_path / "generated"
    generated.mkdir()
    return generated / "versions.json"


@pytest.fixture()
def tracker(versions_path: Path) -> VersionTracker:
    """Create a VersionTracker with a temp versions file."""
    return VersionTracker(versions_path=versions_path)


@pytest.fixture()
def pipeline(tmp_skills: Path) -> TemplatePipeline:
    """Create a TemplatePipeline with temp skills dir."""
    return TemplatePipeline(skills_dir=tmp_skills)


# ---------------------------------------------------------------------------
# VersionTracker tests
# ---------------------------------------------------------------------------


class TestVersionTracker:
    def test_record_and_get(self, tracker: VersionTracker) -> None:
        tracker.record_generation("SKILL_A", "1.0", "/path/to/agent.py")
        entry = tracker.get_version("SKILL_A")
        assert entry is not None
        assert entry["version"] == "1.0"
        assert entry["agent_path"] == "/path/to/agent.py"
        assert "generated_at" in entry

    def test_get_nonexistent(self, tracker: VersionTracker) -> None:
        assert tracker.get_version("MISSING") is None

    def test_needs_regeneration_no_record(self, tracker: VersionTracker) -> None:
        assert tracker.needs_regeneration("SKILL_A", "1.0") is True

    def test_needs_regeneration_same_version(self, tracker: VersionTracker) -> None:
        tracker.record_generation("SKILL_A", "1.0", "/path/a.py")
        assert tracker.needs_regeneration("SKILL_A", "1.0") is False

    def test_needs_regeneration_different_version(self, tracker: VersionTracker) -> None:
        tracker.record_generation("SKILL_A", "1.0", "/path/a.py")
        assert tracker.needs_regeneration("SKILL_A", "1.1") is True

    def test_get_all_versions(self, tracker: VersionTracker) -> None:
        tracker.record_generation("A", "1.0", "/a.py")
        tracker.record_generation("B", "2.0", "/b.py")
        versions = tracker.get_all_versions()
        assert "A" in versions
        assert "B" in versions
        assert len(versions) == 2

    def test_overwrite_existing(self, tracker: VersionTracker) -> None:
        tracker.record_generation("A", "1.0", "/a.py")
        tracker.record_generation("A", "2.0", "/a_v2.py")
        entry = tracker.get_version("A")
        assert entry is not None
        assert entry["version"] == "2.0"
        assert entry["agent_path"] == "/a_v2.py"

    def test_empty_file(self, versions_path: Path) -> None:
        versions_path.write_text("", encoding="utf-8")
        tracker = VersionTracker(versions_path=versions_path)
        assert tracker.get_all_versions() == {}

    def test_corrupt_file(self, versions_path: Path) -> None:
        versions_path.write_text("{bad json", encoding="utf-8")
        tracker = VersionTracker(versions_path=versions_path)
        assert tracker.get_all_versions() == {}


# ---------------------------------------------------------------------------
# TemplatePipeline.generate_all tests
# ---------------------------------------------------------------------------


class TestGenerateAll:
    def test_generate_all_calls_manager(self, pipeline: TemplatePipeline) -> None:
        mock_manager = MagicMock()
        mock_manager.generate_executable_and_register.return_value = {
            "agent": Path("/tmp/agent.py")
        }
        pipeline._manager = mock_manager

        mock_tracker = MagicMock()
        pipeline._tracker = mock_tracker

        results = pipeline.generate_all(top_n=5)

        # 3 skills have instructions, 1 doesn't
        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_manager.generate_executable_and_register.call_count == 3

    def test_generate_all_top_n_limit(self, pipeline: TemplatePipeline) -> None:
        mock_manager = MagicMock()
        mock_manager.generate_executable_and_register.return_value = {
            "agent": Path("/tmp/agent.py")
        }
        pipeline._manager = mock_manager
        pipeline._tracker = MagicMock()

        results = pipeline.generate_all(top_n=1)
        assert len(results) == 1

    def test_generate_all_handles_failure(self, pipeline: TemplatePipeline) -> None:
        mock_manager = MagicMock()
        mock_manager.generate_executable_and_register.side_effect = RuntimeError("boom")
        pipeline._manager = mock_manager
        pipeline._tracker = MagicMock()

        results = pipeline.generate_all(top_n=5)
        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all("boom" in r.error for r in results)


# ---------------------------------------------------------------------------
# TemplatePipeline.regenerate_for_skill tests
# ---------------------------------------------------------------------------


class TestRegenerateForSkill:
    def test_regenerate_success(self, pipeline: TemplatePipeline) -> None:
        mock_manager = MagicMock()
        mock_manager.generate_executable_and_register.return_value = {
            "agent": Path("/tmp/agent.py")
        }
        pipeline._manager = mock_manager
        pipeline._tracker = MagicMock()

        result = pipeline.regenerate_for_skill("SKILL_0_PRIME")
        assert result.success
        assert result.skill_name == "SKILL_0_PRIME"
        assert result.version == "1.0"

    def test_regenerate_not_found(self, pipeline: TemplatePipeline) -> None:
        result = pipeline.regenerate_for_skill("NONEXISTENT_SKILL")
        assert not result.success
        assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# TemplatePipeline.sync_registry tests
# ---------------------------------------------------------------------------


class TestSyncRegistry:
    def test_sync_adds_missing(self, pipeline: TemplatePipeline) -> None:
        with (
            patch.object(TemplatePipeline, "_load_registry", return_value={}),
            patch.object(TemplatePipeline, "_write_registry"),
        ):
            result = pipeline.sync_registry()
            # All 4 skills should be added since registry is empty
            assert len(result.added) == 4
            assert len(result.updated) == 0
            assert len(result.errors) == 0

    def test_sync_updates_stale(self, pipeline: TemplatePipeline) -> None:
        old_registry = {
            "SKILL_0_PRIME": {
                "version": "0.9",
                "concepts": [],
                "see_also": [],
                "source": "old.md",
            }
        }

        with (
            patch.object(TemplatePipeline, "_load_registry", return_value=old_registry),
            patch.object(TemplatePipeline, "_write_registry"),
        ):
            result = pipeline.sync_registry()
            assert "SKILL_0_PRIME" in result.updated
            # Others should be added
            assert len(result.added) >= 3

    def test_sync_leaves_unchanged(self, pipeline: TemplatePipeline) -> None:
        # Parse all to know versions, build a matching registry
        specs = pipeline.engine.parse_all()
        existing_registry = {}
        for spec in specs:
            existing_registry[spec.name] = {
                "version": spec.version,
                "concepts": list(spec.concepts.keys()),
                "see_also": spec.see_also,
                "source": str(spec.source_path),
            }

        with (
            patch.object(
                TemplatePipeline,
                "_load_registry",
                return_value=existing_registry,
            ),
            patch.object(TemplatePipeline, "_write_registry"),
        ):
            result = pipeline.sync_registry()
            assert len(result.unchanged) == len(specs)
            assert len(result.added) == 0
            assert len(result.updated) == 0


# ---------------------------------------------------------------------------
# TemplatePipeline.detect_stale_agents tests
# ---------------------------------------------------------------------------


class TestDetectStaleAgents:
    def test_no_versions_no_stale(self, pipeline: TemplatePipeline) -> None:
        mock_tracker = MagicMock()
        mock_tracker.get_all_versions.return_value = {}
        pipeline._tracker = mock_tracker

        stale = pipeline.detect_stale_agents()
        assert stale == []

    def test_detects_stale(self, pipeline: TemplatePipeline) -> None:
        mock_tracker = MagicMock()
        mock_tracker.get_all_versions.return_value = {
            "SKILL_0_PRIME": {
                "version": "0.9",
                "agent_path": "/tmp/old.py",
            }
        }
        pipeline._tracker = mock_tracker

        stale = pipeline.detect_stale_agents()
        assert len(stale) == 1
        assert stale[0].skill_name == "SKILL_0_PRIME"
        assert stale[0].current_version == "1.0"
        assert stale[0].generated_version == "0.9"

    def test_current_not_stale(self, pipeline: TemplatePipeline) -> None:
        mock_tracker = MagicMock()
        mock_tracker.get_all_versions.return_value = {
            "SKILL_0_PRIME": {
                "version": "1.0",
                "agent_path": "/tmp/current.py",
            }
        }
        pipeline._tracker = mock_tracker

        stale = pipeline.detect_stale_agents()
        assert len(stale) == 0


# ---------------------------------------------------------------------------
# Config template version header test
# ---------------------------------------------------------------------------


class TestConfigTemplateVersionHeader:
    def test_version_header_in_generated_agent(self, tmp_path: Path) -> None:
        """After modification, generated agents include a version comment."""
        from cohezion.core.config_templates import ConfigTemplateManager
        from cohezion.core.template_engine import TemplateEngine

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        md = skills_dir / "TEST_SKILL_PRIME.md"
        md.write_text(
            "# SKILL: TEST_SKILL_PRIME\n\n## VERSION\n\n2.5\n\n## INSTRUCTION\n\n1. Do something\n",
            encoding="utf-8",
        )

        engine = TemplateEngine(skills_dir)
        manager = ConfigTemplateManager(engine=engine)

        # Need to create the generated dir
        gen_dir = Path("src/cohezion/agents/generated")
        gen_dir.mkdir(parents=True, exist_ok=True)

        try:
            paths = manager.generate_executable_and_register("TEST_SKILL_PRIME")
            agent_path = paths["agent"]
            content = agent_path.read_text(encoding="utf-8")
            assert content.startswith("# Generated from TEST_SKILL_PRIME v2.5 at ")
        finally:
            # Cleanup generated file
            agent_file = gen_dir / "test_skill_agent.py"
            if agent_file.exists():
                agent_file.unlink()


# ---------------------------------------------------------------------------
# Factory auto_regenerate test
# ---------------------------------------------------------------------------


class TestFactoryAutoRegenerate:
    def test_auto_regenerate_triggers_pipeline(self, tmp_path: Path) -> None:
        from cohezion.agents.factory import AgentFactory

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        md = skills_dir / "REGEN_TEST_PRIME.md"
        md.write_text(
            "# SKILL: REGEN_TEST_PRIME\n\n## VERSION\n\n1.0\n\n## INSTRUCTION\n\n1. Step one\n",
            encoding="utf-8",
        )

        factory = AgentFactory(skills_dir=skills_dir)

        mock_tracker = MagicMock()
        mock_tracker.needs_regeneration.return_value = True

        mock_pipeline = MagicMock()

        with (
            patch(
                "cohezion.agents.version_tracker.VersionTracker",
                return_value=mock_tracker,
            ),
            patch(
                "cohezion.agents.template_pipeline.TemplatePipeline",
                return_value=mock_pipeline,
            ),
        ):
            factory.create_executable(
                "REGEN_TEST_PRIME",
                auto_regenerate=True,
            )
            mock_pipeline.regenerate_for_skill.assert_called_once_with("REGEN_TEST_PRIME")

    def test_auto_regenerate_false_skips(self, tmp_path: Path) -> None:
        from cohezion.agents.factory import AgentFactory

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        md = skills_dir / "SKIP_TEST_PRIME.md"
        md.write_text(
            "# SKILL: SKIP_TEST_PRIME\n\n## VERSION\n\n1.0\n\n## INSTRUCTION\n\n1. Step one\n",
            encoding="utf-8",
        )

        factory = AgentFactory(skills_dir=skills_dir)

        with patch(
            "cohezion.agents.version_tracker.VersionTracker",
        ) as mock_tracker_cls:
            factory.create_executable("SKIP_TEST_PRIME")
            mock_tracker_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_generation_result_defaults(self) -> None:
        r = GenerationResult(skill_name="TEST")
        assert r.skill_name == "TEST"
        assert r.agent_path is None
        assert r.version == ""
        assert r.success is False
        assert r.error == ""

    def test_sync_result_defaults(self) -> None:
        r = SyncResult()
        assert r.added == []
        assert r.updated == []
        assert r.unchanged == []
        assert r.errors == []

    def test_stale_agent_fields(self) -> None:
        s = StaleAgent(
            skill_name="A",
            current_version="2.0",
            generated_version="1.0",
            agent_path="/a.py",
        )
        assert s.skill_name == "A"
        assert s.current_version == "2.0"
        assert s.generated_version == "1.0"
