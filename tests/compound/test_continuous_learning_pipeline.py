"""Unit tests for ContinuousLearningPipeline, RetrospectiveManager, SkillExtractor, and SkillRefinementBridge."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from cohezion.compound.continuous_learning_pipeline import (
    ContinuousLearningPipeline,
    RetrospectiveManager,
    SkillExtractor,
    SkillRefinementBridge,
)


class TestContinuousLearningPipeline:
    """Test suite verifying continuous retrospective, skill extraction, and skill refinement."""

    def test_retrospective_manager_generates_and_persists(self, tmp_path: Path):
        vault_dir = tmp_path / "vault_retros"
        manager = RetrospectiveManager(vault_dir=vault_dir)

        portfolio_summary = {
            "rsna-knee-abnormality-detection": {
                "score": 0.9430,
                "baseline": 0.9410,
                "status": "SubmissionStatus.COMPLETE",
                "metric_direction": "higher",
            },
            "arc-prize-2026-arc-agi-2": {
                "score": 31.81,
                "baseline": 30.56,
                "status": "SubmissionStatus.COMPLETE",
                "metric_direction": "higher",
            },
        }
        sprint_result = MagicMock()
        sprint_result.topic.value = "arc3_macro_planner"
        sprint_result.success = True
        sprint_result.invariants_found = ["Zobrist collision free", "BFS path bounded"]

        reflection_result = {
            "avg_coherence": 0.5000,
            "restoring_force": 0.0000,
            "conformal_factor": 2.00,
        }

        with patch("cohezion.compound.continuous_learning_pipeline._surreal_http_upsert", return_value=True):
            res = manager.generate_and_persist(
                cycle_number=1,
                portfolio_summary=portfolio_summary,
                sprint_result=sprint_result,
                reflection_result=reflection_result,
            )

        assert res["cycle_number"] == 1
        assert res["invariants_count"] == 2
        assert len(res["sota_advancements"]) == 2

        # Verify vault markdown file
        created_files = list(vault_dir.glob("retro_cycle_0001_*.md"))
        assert len(created_files) == 1
        content = created_files[0].read_text()
        assert "Retrospective #1" in content
        assert "HIHO Coherence" in content
        assert "Zobrist collision free" in content

    def test_skill_extractor_synthesizes_prime_file_and_registry(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        registry_file = tmp_path / "registry.json"
        extractor = SkillExtractor(skills_dir=skills_dir, registry_file=registry_file)

        skill_file = extractor.extract_from_invariants(
            skill_name="TEST_AUTO_SYNTHESIS_PRIME",
            domain_expertise="Automated testing of mathematical invariant synthesis.",
            concepts=["Invariant A", "Invariant B"],
            instructions=["Step 1: Check invariants.", "Step 2: Assert state."],
            version="v0.1",
        )

        assert skill_file is not None
        assert skill_file.exists()
        content = skill_file.read_text()
        assert "# SKILL: TEST_AUTO_SYNTHESIS_PRIME" in content
        assert "## DOMAIN EXPERTISE" in content
        assert "* **Invariant A**" in content
        assert "1. Step 1: Check invariants." in content

        # Verify registry entry
        assert registry_file.exists()
        reg_data = json.loads(registry_file.read_text())
        assert "TEST_AUTO_SYNTHESIS_PRIME" in reg_data
        assert reg_data["TEST_AUTO_SYNTHESIS_PRIME"]["version"] == "v0.1"

    def test_skill_refinement_bridge_appends_learning(self, tmp_path: Path):
        key_learnings_file = tmp_path / "KEY_LEARNINGS.md"
        key_learnings_file.write_text("# KEY LEARNINGS\n\n## Learning 444: Previous Learning (2026-09-19)\nOld text\n")

        bridge = SkillRefinementBridge(key_learnings_file=key_learnings_file)
        next_num = bridge.get_next_learning_number()
        assert next_num == 445

        with patch("cohezion.compound.continuous_learning_pipeline._surreal_http_upsert", return_value=True):
            assigned_num = bridge.append_learning(
                title="Continuous Retrospective and Skill Synthesis Test",
                summary="Verified integration of experiential loop.",
                points=["Point 1: Retrospectives recorded.", "Point 2: Skills extracted."],
                state_vector_12d="[12D State: Space=Test, Time=Now, Physics=Verified, Brane=Cohezion]",
            )

        assert assigned_num == 445
        updated_content = key_learnings_file.read_text()
        assert "## Learning 445: Continuous Retrospective and Skill Synthesis Test" in updated_content
        assert "*12D State Vector*: `[12D State: Space=Test, Time=Now, Physics=Verified, Brane=Cohezion]`" in updated_content

    def test_continuous_learning_pipeline_end_to_end(self, tmp_path: Path):
        pipeline = ContinuousLearningPipeline()
        pipeline.retrospectives = RetrospectiveManager(vault_dir=tmp_path / "vault_retros")
        pipeline.extractor = SkillExtractor(skills_dir=tmp_path / "skills", registry_file=tmp_path / "registry.json")
        pipeline.refiner_bridge = SkillRefinementBridge(key_learnings_file=tmp_path / "KEY_LEARNINGS.md")

        portfolio_summary = {
            "arc-prize-2026-arc-agi-3": {
                "score": 0.25,
                "baseline": 0.25,
                "status": "SubmissionStatus.COMPLETE",
            }
        }
        sprint_result = MagicMock()
        sprint_result.topic.value = "arc3_macro_planner"
        sprint_result.success = True
        sprint_result.invariants_found = ["Macro planning BFS path"]

        reflection_result = {"avg_coherence": 0.50, "restoring_force": 0.0, "conformal_factor": 2.0}

        with patch("cohezion.compound.continuous_learning_pipeline._surreal_http_upsert", return_value=True):
            cycle_output = pipeline.process_cycle(
                cycle_number=5,
                portfolio_summary=portfolio_summary,
                sprint_result=sprint_result,
                reflection_result=reflection_result,
            )

        assert cycle_output["cycle_number"] == 5
        assert cycle_output["retrospective"] is not None
        assert len(cycle_output["extracted_skills"]) >= 1
        assert cycle_output["learning_entry"] == 445
