"""Tests for dynamic context policy (breadth/depth control)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from cohezion.compound.context_policy import (
    ContextBudget,
    ContextPolicy,
    ContextSignals,
    TaskProfile,
)
from cohezion.flux.types import FluxSource


def _isolated_policy(
    tmp_path: Path,
    vault_logger: object | None = None,
    seed_data: dict | None = None,
) -> ContextPolicy:
    """Create a ContextPolicy that reads/writes to tmp_path, not the real repo."""
    policy_dir = tmp_path / ".context" / "policy"
    policy_dir.mkdir(parents=True)
    if seed_data is not None:
        frontmatter = yaml.dump(seed_data, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter}---\n\n# Test budgets\n"
        (policy_dir / "learned-budgets.md").write_text(content, encoding="utf-8")
    return ContextPolicy(vault_logger=vault_logger, project_root=tmp_path)


@pytest.mark.unit
class TestClassifyTask:
    """Proactive task classification tests."""

    def setup_method(self) -> None:
        self.policy = ContextPolicy()

    def test_classify_routine_task(self) -> None:
        """Short persist task with high template similarity → ROUTINE."""
        profile = self.policy.classify_task(
            task_description="Save metrics to vault",
            operation_type="persist",
            template_similarity=0.9,
        )
        assert profile == TaskProfile.ROUTINE

    def test_classify_routine_short_search(self) -> None:
        """Short search task without template match → still ROUTINE."""
        profile = self.policy.classify_task(
            task_description="Find active users",
            operation_type="search",
        )
        assert profile == TaskProfile.ROUTINE

    def test_classify_focused_task(self) -> None:
        """Single-domain moderate task → FOCUSED (default)."""
        profile = self.policy.classify_task(
            task_description="Fix the import error in executor.py",
            operation_type="analyze",
        )
        assert profile == TaskProfile.FOCUSED

    def test_classify_exploratory_cross_domain(self) -> None:
        """Cross-domain terms (physics + swarm) → EXPLORATORY."""
        profile = self.policy.classify_task(
            task_description="Redesign the physics engine to integrate with swarm orchestration",
            operation_type="generate",
        )
        assert profile == TaskProfile.EXPLORATORY

    def test_classify_exploratory_high_drift(self) -> None:
        """High drift risk → EXPLORATORY regardless of description."""
        profile = self.policy.classify_task(
            task_description="Update config",
            operation_type="persist",
            drift_risk=0.5,
        )
        assert profile == TaskProfile.EXPLORATORY

    def test_classify_exploratory_multi_intent_long(self) -> None:
        """Multiple intent clusters + long description → EXPLORATORY."""
        long_desc = (
            "Generate a comprehensive analysis report that searches for patterns "
            "across all vault experiments, transforms the data into actionable insights, "
            "and persists the results to SurrealDB for future compound queries. "
            "Include visualizations and cross-reference with existing architecture decisions."
        )
        profile = self.policy.classify_task(
            task_description=long_desc,
            operation_type="generate",
        )
        assert profile == TaskProfile.EXPLORATORY


@pytest.mark.unit
class TestGetBudget:
    """Profile-to-budget mapping tests."""

    def test_focused_budget_values(self) -> None:
        policy = ContextPolicy()
        budget = policy.get_budget(TaskProfile.FOCUSED)
        assert budget.flux_top_k == 5
        assert budget.flux_min_relevance == 0.7
        assert budget.flux_sources == (FluxSource.VAULT, FluxSource.HISTORY)
        assert budget.token_budget == 800
        assert budget.skill_overlay is True

    def test_routine_budget_minimal(self) -> None:
        policy = ContextPolicy()
        budget = policy.get_budget(TaskProfile.ROUTINE)
        assert budget.flux_top_k == 2
        assert budget.token_budget == 300
        assert budget.skill_overlay is False

    def test_exploratory_budget_broad(self) -> None:
        policy = ContextPolicy()
        budget = policy.get_budget(TaskProfile.EXPLORATORY)
        assert budget.flux_top_k == 10
        assert budget.flux_sources is None  # all sources
        assert budget.token_budget == 1500


@pytest.mark.unit
class TestAdjustImmediate:
    """Tier 1 reactive adjustment tests."""

    def setup_method(self) -> None:
        self.policy = ContextPolicy()
        self.base_budget = ContextBudget(
            flux_top_k=5,
            flux_min_relevance=0.7,
            flux_sources=(FluxSource.VAULT,),
            token_budget=800,
            skill_overlay=True,
        )

    def test_adjust_immediate_coherence_drop(self) -> None:
        """Coherence below 0.5 → broadens (more blocks, lower threshold)."""
        signals = ContextSignals(coherence_state=0.3)
        adjusted = self.policy.adjust_immediate(self.base_budget, signals)

        assert adjusted.flux_top_k == 8  # 5 + 3
        assert adjusted.flux_min_relevance == 0.6  # 0.7 - 0.1
        # Other fields unchanged
        assert adjusted.token_budget == 800
        assert adjusted.skill_overlay is True

    def test_adjust_immediate_token_pressure(self) -> None:
        """Token usage > 80% of budget → narrows search."""
        signals = ContextSignals(token_usage=700)  # 700 > 800 * 0.8 = 640
        adjusted = self.policy.adjust_immediate(self.base_budget, signals)

        assert adjusted.flux_top_k == 2
        assert adjusted.flux_min_relevance == pytest.approx(0.8)  # 0.7 + 0.1

    def test_no_adjustment_when_signals_normal(self) -> None:
        """Normal signals → budget unchanged (same object returned)."""
        signals = ContextSignals(coherence_state=0.8, token_usage=100)
        adjusted = self.policy.adjust_immediate(self.base_budget, signals)
        assert adjusted is self.base_budget

    def test_coherence_and_token_conflict_token_wins(self) -> None:
        """When both fire, token narrowing caps the top_k from broadening."""
        signals = ContextSignals(coherence_state=0.3, token_usage=700)
        adjusted = self.policy.adjust_immediate(self.base_budget, signals)

        # Coherence wants top_k=8, token wants top_k=2 → min(8, 2) = 2
        assert adjusted.flux_top_k == 2
        # Relevance: coherence wants 0.6, token wants 0.8 → max(0.6, 0.8) = 0.8
        assert adjusted.flux_min_relevance == pytest.approx(0.8)


@pytest.mark.unit
class TestSoftSignalRecording:
    """Tier 2 vault learning tests."""

    def test_soft_signal_drift_recorded(self, tmp_path: Path) -> None:
        """Alignment < 0.6 → logs drift_prone signal to vault."""
        mock_vault = MagicMock()
        policy = _isolated_policy(tmp_path, vault_logger=mock_vault)

        signals = ContextSignals(alignment_score=0.4)
        policy.record_soft_signal(signals, TaskProfile.FOCUSED, "test task")

        mock_vault.log_experiment.assert_called_once()
        call_kwargs = mock_vault.log_experiment.call_args.kwargs
        assert "drift_prone" in call_kwargs["result"]

    def test_soft_signal_over_classified_recorded(self, tmp_path: Path) -> None:
        """Template hit on EXPLORATORY → logs over_classified signal."""
        mock_vault = MagicMock()
        policy = _isolated_policy(tmp_path, vault_logger=mock_vault)

        signals = ContextSignals(template_hit=True)
        policy.record_soft_signal(signals, TaskProfile.EXPLORATORY, "test task")

        mock_vault.log_experiment.assert_called_once()
        call_kwargs = mock_vault.log_experiment.call_args.kwargs
        assert "over_classified" in call_kwargs["result"]

    def test_soft_signal_no_vault_no_error(self, tmp_path: Path) -> None:
        """No vault logger → silently skips, still persists override to file."""
        policy = _isolated_policy(tmp_path)
        signals = ContextSignals(alignment_score=0.3)
        # Should not raise
        policy.record_soft_signal(signals, TaskProfile.FOCUSED, "test task")

    def test_normal_signals_nothing_recorded(self, tmp_path: Path) -> None:
        """Normal signals → no vault calls, no file writes."""
        mock_vault = MagicMock()
        policy = _isolated_policy(tmp_path, vault_logger=mock_vault)

        signals = ContextSignals(alignment_score=0.9, template_hit=False)
        policy.record_soft_signal(signals, TaskProfile.FOCUSED, "test task")

        mock_vault.log_experiment.assert_not_called()


@pytest.mark.unit
class TestPersistence:
    """Cross-session persistence tests."""

    def test_load_learned_budgets_from_file(self, tmp_path: Path) -> None:
        """Warm start reads custom budget values from YAML frontmatter."""
        seed = {
            "version": "1.0.0",
            "profiles": {
                "focused": {
                    "flux_top_k": 7,
                    "flux_min_relevance": 0.65,
                    "token_budget": 900,
                    "skill_overlay": True,
                }
            },
        }
        policy = _isolated_policy(tmp_path, seed_data=seed)
        budget = policy.get_budget(TaskProfile.FOCUSED)

        assert budget.flux_top_k == 7
        assert budget.flux_min_relevance == 0.65
        assert budget.token_budget == 900

    def test_load_learned_budgets_missing_file(self, tmp_path: Path) -> None:
        """Missing file → hardcoded defaults, no error."""
        # Create .context/policy/ dir but no .md file
        (tmp_path / ".context" / "policy").mkdir(parents=True)
        policy = ContextPolicy(project_root=tmp_path)
        budget = policy.get_budget(TaskProfile.FOCUSED)

        assert budget.flux_top_k == 5  # hardcoded default

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        """Save budgets → load in new instance → values preserved."""
        policy1 = _isolated_policy(tmp_path)
        policy1.record_outcome(
            TaskProfile.FOCUSED,
            policy1.get_budget(TaskProfile.FOCUSED),
            execution_success=True,
            coherence_final=0.85,
        )

        # Create new policy from same directory
        policy2 = ContextPolicy(project_root=tmp_path)
        assert policy2._outcome_summary["total_executions"] == 1
        stats = policy2._outcome_summary["by_profile"]["focused"]
        assert stats["successes"] == 1
        assert stats["avg_coherence"] == pytest.approx(0.85)

    def test_record_outcome_updates_file(self, tmp_path: Path) -> None:
        """record_outcome() writes updated outcome_summary to YAML frontmatter."""
        policy = _isolated_policy(tmp_path)
        budget = policy.get_budget(TaskProfile.ROUTINE)

        policy.record_outcome(TaskProfile.ROUTINE, budget, True, 0.9)
        policy.record_outcome(TaskProfile.ROUTINE, budget, False, 0.4)

        # Read the YAML frontmatter directly
        from cohezion.compound.context_policy import _parse_frontmatter

        path = tmp_path / ".context" / "policy" / "learned-budgets.md"
        data = _parse_frontmatter(path.read_text(encoding="utf-8"))

        assert data["outcome_summary"]["total_executions"] == 2
        assert data["outcome_summary"]["by_profile"]["routine"]["successes"] == 1
        assert data["outcome_summary"]["by_profile"]["routine"]["failures"] == 1

    def test_task_override_persisted(self, tmp_path: Path) -> None:
        """Soft signal creates task_overrides entry in YAML frontmatter."""
        policy = _isolated_policy(tmp_path)
        signals = ContextSignals(alignment_score=0.4)
        policy.record_soft_signal(signals, TaskProfile.FOCUSED, "debug physics module")

        # Read the YAML frontmatter directly
        from cohezion.compound.context_policy import _parse_frontmatter

        path = tmp_path / ".context" / "policy" / "learned-budgets.md"
        data = _parse_frontmatter(path.read_text(encoding="utf-8"))

        assert len(data["task_overrides"]) == 1
        override = data["task_overrides"][0]
        assert override["signal"] == "drift_prone"
        assert override["task_snippet"] == "debug physics module"
