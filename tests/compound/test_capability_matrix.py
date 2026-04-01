"""Tests for capability_matrix.py and workflow_manager.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.capability_matrix import (
    CapabilityEntry,
    CapabilityGap,
    CapabilityMatrix,
    FinetuneCandidate,
)
from cohezion.compound.workflow_manager import (
    FinetuneResult,
    GapReport,
    ReassessmentReport,
    WorkflowManager,
)


class TestCapabilityEntry:
    """Tests for CapabilityEntry dataclass."""

    def test_default_values_p0(self):
        """[P0] Entry has sensible defaults."""
        entry = CapabilityEntry(entity_type="model", entity_id="test:latest")
        assert entry.quality_score == 0.0
        assert entry.speed_tier == 3
        assert entry.source == "static"
        assert entry.capabilities == []

    def test_affinity_dict_p1(self):
        """[P1] Affinity scores are per-task-type floats."""
        entry = CapabilityEntry(
            entity_type="model",
            entity_id="test:latest",
            affinity={"coding": 0.9, "reasoning": 0.3},
        )
        assert entry.affinity["coding"] == 0.9
        assert entry.affinity.get("creative", 0.0) == 0.0


class TestCapabilityMatrix:
    """Tests for CapabilityMatrix unified registry."""

    def test_loads_models_from_smart_router_p0(self):
        """[P0] Matrix loads model entries from SmartRouter LOCAL_MODELS."""
        matrix = CapabilityMatrix()
        models = matrix.get_matrix()["model"]
        assert len(models) > 0
        # SmolLM3 should be present (added earlier this session)
        ids = [m.entity_id for m in models]
        assert any("smollm3" in m for m in ids)

    def test_loads_agents_from_directory_p0(self):
        """[P0] Matrix loads agent entries from .claude/agents/."""
        matrix = CapabilityMatrix()
        agents = matrix.get_matrix()["agent"]
        # At minimum code-reviewer and security-reviewer exist
        names = [a.entity_id for a in agents]
        assert "code-reviewer" in names

    def test_recommend_for_task_returns_sorted_p0(self):
        """[P0] Recommendations are sorted by affinity + quality descending."""
        matrix = CapabilityMatrix()
        recs = matrix.recommend_for_task("coding")
        assert len(recs) > 0
        # First result should have highest combined score
        if len(recs) >= 2:
            score_0 = recs[0].affinity.get("coding", 0.0) + recs[0].quality_score
            score_1 = recs[1].affinity.get("coding", 0.0) + recs[1].quality_score
            assert score_0 >= score_1

    def test_recommend_with_constraints_p1(self):
        """[P1] Constraints filter out entries that don't match."""
        matrix = CapabilityMatrix()
        recs = matrix.recommend_for_task("coding", {"min_quality": 0.99})
        # Very high bar should exclude most or all
        assert len(recs) <= len(matrix.get_matrix()["model"])

    def test_gap_analysis_p0(self):
        """[P0] Gap analysis identifies task types below threshold."""
        matrix = CapabilityMatrix()
        gaps = matrix.run_gap_analysis()
        # Should find at least one gap (e.g., multilingual has no strong model)
        assert isinstance(gaps, list)
        for gap in gaps:
            assert gap.best_available_score < gap.threshold

    def test_export_report_markdown_p1(self):
        """[P1] Export produces valid markdown with headers and tables."""
        matrix = CapabilityMatrix()
        report = matrix.export_report()
        assert "# Capability Matrix Report" in report
        assert "| ID |" in report

    def test_update_from_execution_p1(self):
        """[P1] Execution results update quality via EMA."""
        matrix = CapabilityMatrix()
        models = matrix.get_matrix()["model"]
        if not models:
            pytest.skip("No models loaded")
        model_id = models[0].entity_id
        old_quality = models[0].quality_score
        matrix.update_from_execution(model_id, {"coherence": 1.0, "success": True})
        new_quality = matrix.assess_model(model_id).quality_score
        # EMA should move quality toward 1.0
        assert new_quality >= old_quality or abs(new_quality - old_quality) < 0.01

    def test_finetune_targets_p1(self):
        """[P1] Fine-tune suggestions include mode based on data count."""
        matrix = CapabilityMatrix()
        targets = matrix.suggest_finetune_targets()
        assert isinstance(targets, list)
        for t in targets:
            assert t.finetune_mode in ("soft", "qlora", "call")
            assert isinstance(t.feasible, bool)


class TestWorkflowManager:
    """Tests for WorkflowManager orchestration."""

    def test_gap_analysis_report_p0(self):
        """[P0] Gap report includes gaps and scout targets."""
        wm = WorkflowManager()
        report = wm.run_gap_analysis()
        assert isinstance(report, GapReport)
        assert isinstance(report.gaps, list)

    def test_generate_router_entries_p0(self):
        """[P0] Router entry generation produces all 5 sections."""
        wm = WorkflowManager()
        entries = wm.generate_router_entries("test/model:latest", quality=0.7)
        assert "smart_router.py" in entries
        assert "cost_aware_router.py" in entries
        assert "dynamic_model_router.py" in entries
        assert "model_quality_classifier.py" in entries
        assert "model_pool_config.py" in entries

    def test_export_gap_report_markdown_p1(self):
        """[P1] Gap report is valid markdown."""
        wm = WorkflowManager()
        report = wm.export_gap_report()
        assert "# Capability Gap Analysis" in report

    @patch("cohezion.compound.workflow_manager.subprocess.run")
    def test_run_model_onboarding_model_found_p0(self, mock_run):
        """[P0] Onboarding succeeds when model is found in ollama list."""
        mock_run.return_value = MagicMock(
            stdout="NAME            SIZE\nphi3:mini       2.3 GB\n",
            returncode=0,
        )
        wm = WorkflowManager()
        result = wm.run_model_onboarding("phi3:mini")
        assert result.pulled is True
        assert result.assessed is True
        assert result.router_entry_generated is True
        assert result.error == ""

    @patch("cohezion.compound.workflow_manager.subprocess.run")
    def test_run_model_onboarding_model_not_found_p0(self, mock_run):
        """[P0] Onboarding reports error when model is not in ollama list."""
        mock_run.return_value = MagicMock(
            stdout="NAME            SIZE\nphi3:mini       2.3 GB\n",
            returncode=0,
        )
        wm = WorkflowManager()
        result = wm.run_model_onboarding("nonexistent:latest")
        assert result.pulled is False
        assert "not found locally" in result.error

    @patch("cohezion.compound.workflow_manager.subprocess.run")
    def test_run_model_onboarding_ollama_unavailable_p1(self, mock_run):
        """[P1] Onboarding handles ollama being unavailable."""
        mock_run.side_effect = FileNotFoundError("ollama not found")
        wm = WorkflowManager()
        result = wm.run_model_onboarding("phi3:mini")
        assert result.pulled is False
        assert "Cannot check Ollama" in result.error

    def test_run_periodic_reassessment_p0(self):
        """[P0] Reassessment returns a valid report with entity counts."""
        wm = WorkflowManager()
        report = wm.run_periodic_reassessment()
        assert isinstance(report, ReassessmentReport)
        assert report.entities_checked >= 0
        assert isinstance(report.degraded, list)
        assert isinstance(report.promoted, list)

    def test_run_periodic_reassessment_checks_entities_p0(self):
        """[P0] Reassessment checks at least 1 entity (models + agents exist)."""
        wm = WorkflowManager()
        report = wm.run_periodic_reassessment()
        assert report.entities_checked > 0

    def test_run_finetune_from_gap_feasible_candidate_p0(self):
        """[P0] Finetune succeeds with a feasible candidate (soft mode)."""
        matrix = MagicMock(spec=CapabilityMatrix)
        matrix.run_gap_analysis.return_value = []
        matrix.get_matrix.return_value = {"model": [], "agent": []}
        matrix.enrich_from_execution_history.return_value = 0
        matrix.suggest_finetune_targets.return_value = [
            FinetuneCandidate(
                base_model="phi3:mini",
                target_capability="coding",
                finetune_mode="soft",
                training_data_count=50,
                estimated_quality_gain=0.15,
                memory_required_gb=4.0,
                feasible=True,
            )
        ]
        wm = WorkflowManager(matrix=matrix)
        gap = CapabilityGap(
            task_type="coding",
            required_capability="coding",
            best_available_score=0.3,
            threshold=0.5,
            suggested_action="finetune",
        )
        with patch("cohezion.compound.workflow_manager.WorkflowManager._run_soft_finetune") as mock_soft:
            mock_soft.return_value = FinetuneResult(
                base_model="phi3:mini",
                target_capability="coding",
                mode="soft",
                success=True,
                new_model_id="cohezion-coding-v1",
                training_samples=50,
            )
            result = wm.run_finetune_from_gap(gap)
        assert isinstance(result, FinetuneResult)
        assert result.success is True
        assert result.new_model_id == "cohezion-coding-v1"
        assert result.error == ""

    def test_run_finetune_from_gap_no_candidate_p0(self):
        """[P0] Finetune returns failure when no candidate matches gap."""
        wm = WorkflowManager()
        gap = CapabilityGap(
            task_type="nonexistent_task",
            required_capability="nonexistent",
            best_available_score=0.1,
            threshold=0.5,
            suggested_action="finetune",
        )
        result = wm.run_finetune_from_gap(gap)
        assert isinstance(result, FinetuneResult)
        assert result.success is False
        assert "No suitable" in result.error

    def test_run_finetune_from_gap_infeasible_p1(self):
        """[P1] Finetune returns failure when candidate is infeasible."""
        matrix = MagicMock(spec=CapabilityMatrix)
        matrix.run_gap_analysis.return_value = []
        matrix.suggest_finetune_targets.return_value = [
            FinetuneCandidate(
                base_model="qwen3.5",
                target_capability="coding",
                finetune_mode="qlora",
                training_data_count=100,
                estimated_quality_gain=0.2,
                memory_required_gb=999.0,
                feasible=False,
            )
        ]
        wm = WorkflowManager(matrix=matrix)
        gap = CapabilityGap(
            task_type="coding",
            required_capability="coding",
            best_available_score=0.3,
            threshold=0.5,
            suggested_action="finetune",
        )
        result = wm.run_finetune_from_gap(gap)
        assert result.success is False
        assert "exceeds capacity" in result.error
