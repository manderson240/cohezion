"""Full-cycle compound engineering loop integration test.

Tests the complete pipeline: CompoundExecutor → RetrospectionEngine →
SkillRefiner → SkillConsensusVoter in sequence.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.inflection_detector import AnomalyDetection, Severity
from cohezion.compound.retrospection_summary import CycleMetrics, RetrospectionEngine
from cohezion.compound.skill_consensus_voter import (
    AgentVote,
    SkillConsensusVoter,
    VotingStrategy,
)
from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.compound.skill_selector import SkillScore


_SKILL = "FULL_CYCLE_TEST"
_OP = "generate"

_PRIME_CONTENT = (
    "# FULL_CYCLE_TEST PRIME Skill\n\n"
    "## Version: 1.0.0\n\n"
    "## Keywords: test, integration, compound\n"
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Mock MCPClient with all vault operations stubbed."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = []
    client.vault_log_experiment.return_value = "experiments/test_fc_123.md"
    client.vault_log_decision.return_value = "decisions/test_fc_456.md"
    client.vault_extract_pattern.return_value = "patterns/test_fc_789.md"
    client.vault_add_document.return_value = "voting/test_fc.md"
    return client


@pytest.fixture
def prime_file(tmp_path: Path) -> Path:
    """Temp PRIME skill file that SkillRefiner can find and modify."""
    p = tmp_path / f"{_SKILL}_PRIME.md"
    p.write_text(_PRIME_CONTENT, encoding="utf-8")
    return p


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_skill_score(name: str, score: float = 0.8) -> SkillScore:
    return SkillScore(
        skill_name=name,
        coherence_score=score,
        token_efficiency=score,
        success_rate=score,
        times_used=5,
        composite_score=score,
    )


def _make_executor(mcp_client: MagicMock, **kwargs) -> CompoundExecutor:
    return CompoundExecutor(mcp_client, enable_guardrails=False, **kwargs)


def _cycle_metrics_from_result(result, anomalies: list[str] | None = None) -> CycleMetrics:
    """Build CycleMetrics from an ExecutionResult for retrospection."""
    return CycleMetrics(
        coherence_start=0.5,
        coherence_end=result.metrics.get("coherence", 0.5),
        tokens_used=result.metrics.get("tokens_used", 0),
        skill_name=_SKILL,
        phase="executing",
        success=result.success,
        anomalies=anomalies or [],
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestCompoundFullCycle:
    """Integration test for the complete compound engineering cycle."""

    def test_full_cycle_success_executes_all_stages(
        self, tmp_path: Path, mock_mcp_client: MagicMock, prime_file: Path
    ):
        """Execute → Reflect → Refine → Vote: all 4 stages run end-to-end on success."""
        # ── Phase 1: Setup ────────────────────────────────────────────────────
        # Mock inflection detector so anomaly_score is deterministic (not vault-dependent).
        mock_detector = MagicMock()
        mock_detector.detect_anomaly.return_value = AnomalyDetection(
            severity=Severity.INFO, score=0.05, issues=[], recommendations=[], should_reexecute=False
        )
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,  # disable implicit refiner; Phase 4 calls it directly
            inflection_detector=mock_detector,
        )

        # ── Phase 2: Execute (CompoundExecutor) ───────────────────────────────
        result = executor.execute_task(
            task_description="Full-cycle integration test task",
            skill_name=_SKILL,
            operation_type=_OP,
            execute_fn=lambda guidance: ("cycle-success-output", {"quality": 0.95}),
        )

        assert result.success is True
        assert result.output == "cycle-success-output"
        assert "coherence" in result.metrics
        # With score=0.05: coherence = (0.7 + 0.95) / 2 = 0.825
        assert result.metrics["coherence"] > 0.6
        assert result.duration_seconds >= 0.0

        # ── Phase 3: Retrospect (RetrospectionEngine) ─────────────────────────
        engine = RetrospectionEngine()
        summary = engine.summarize("full-cycle-1", _cycle_metrics_from_result(result))

        assert "I succeeded" in summary.narrative
        assert _SKILL in summary.narrative
        assert isinstance(summary.insights, list)

        # ── Phase 4: SkillRefiner processes executor output → updates PRIME file ──
        # Explicitly feed ExecutionResult into SkillRefiner to test the data flow.
        # token_efficiency=0.0 (no token_client) < 500 threshold → signal generated.
        # Note: token_metrics=None causes AttributeError in _extract_metrics (it calls
        # .get() on it); normalise to {} so the real refiner path runs correctly.
        refiner = SkillRefiner(mock_mcp_client)
        refiner.SKILLS_DIR = tmp_path  # instance-level override; avoids class-level patch
        refined_path = refiner.refine(
            skill_name=_SKILL,
            operation_type=_OP,
            execution_result={
                "success": result.success,
                "metrics": result.metrics,
                "duration_seconds": result.duration_seconds,
                "token_metrics": result.token_metrics or {},
            },
        )
        assert refined_path is not None
        updated_text = prime_file.read_text(encoding="utf-8")
        assert "FULL_CYCLE_TEST" in updated_text  # file integrity maintained
        assert "## Version: 1.0.1" in updated_text  # patch version bumped
        assert "Learned Refinement" in updated_text  # refinement section appended

        # ── Phase 5: Vote (SkillConsensusVoter) ───────────────────────────────
        voter = SkillConsensusVoter(mock_mcp_client)
        skill_a = _make_skill_score(_SKILL, 0.9)
        skill_b = _make_skill_score("FALLBACK_SKILL", 0.5)

        votes = [
            AgentVote(
                agent_id=f"agent-{i}",
                task_description="Full-cycle integration test task",
                operation_type=_OP,
                voted_skills=[skill_a, skill_b],
                agent_coherence_score=result.metrics.get("coherence", 0.7),
            )
            for i in range(3)
        ]
        consensus = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        assert consensus.consensus_skill is not None
        assert consensus.consensus_skill.skill_name == _SKILL
        assert consensus.votes_for_consensus == 3
        assert consensus.confidence_score > 0.5
        assert not consensus.fallback_used

        # ── Phase 6: Chain integrity ──────────────────────────────────────────
        assert summary.metrics.success is True
        assert consensus.strategy_used == VotingStrategy.MAJORITY
        assert len(engine.summaries) == 1

    def test_full_cycle_failure_recovery_no_refine_anomaly_detected(
        self, tmp_path: Path, mock_mcp_client: MagicMock, prime_file: Path
    ):
        """Execute (fail) → Reflect (anomaly) → no-refine → Vote (fallback)."""
        # ── Phase 1: Setup ────────────────────────────────────────────────────
        mock_refiner = MagicMock(spec=SkillRefiner)
        executor = _make_executor(
            mock_mcp_client,
            skill_refiner=mock_refiner,
            enable_skill_refinement=True,
        )

        # ── Phase 2: Execute with failure ─────────────────────────────────────
        def _fail(guidance):
            raise RuntimeError("simulated failure in full-cycle test")

        result = executor.execute_task(
            task_description="Intentionally failing integration test",
            skill_name=_SKILL,
            operation_type=_OP,
            execute_fn=_fail,
        )

        assert result.success is False
        assert "Error:" in result.output
        mock_refiner.refine.assert_not_called()  # executor skips refiner on failure

        # ── Phase 3: Retrospect with failure metrics ───────────────────────────
        engine = RetrospectionEngine()
        failed_metrics = CycleMetrics(
            coherence_start=0.6,
            coherence_end=0.3,  # coherence degraded on failure
            tokens_used=0,
            skill_name=_SKILL,
            phase="executing",
            success=False,
            anomalies=["execution_failure"],
        )
        summary = engine.summarize("full-cycle-fail-1", failed_metrics)

        assert "encountered challenges" in summary.narrative
        # Coherence dropped by 0.3 → rollback suggestion
        assert any("degradation" in i.lower() for i in summary.insights)
        # success=False → freeze-frame insight
        assert any("failed" in i.lower() for i in summary.insights)
        # anomaly present → anomaly insight
        assert any("anomal" in i.lower() for i in summary.insights)

        # ── Phase 4: PRIME file unchanged ────────────────────────────────────
        assert prime_file.read_text(encoding="utf-8") == _PRIME_CONTENT

        # ── Phase 5: Vote still works (split → fallback) ──────────────────────
        voter = SkillConsensusVoter(mock_mcp_client)
        skill_a = _make_skill_score(_SKILL, 0.9)
        skill_b = _make_skill_score("SAFE_FALLBACK", 0.8)

        votes = [
            AgentVote(
                agent_id="agent-0",
                task_description="Failing task",
                operation_type=_OP,
                voted_skills=[skill_a],
                agent_coherence_score=0.3,
            ),
            AgentVote(
                agent_id="agent-1",
                task_description="Failing task",
                operation_type=_OP,
                voted_skills=[skill_b],  # disagrees → no majority
                agent_coherence_score=0.3,
            ),
        ]
        consensus = voter.vote_on_skills(votes, strategy=VotingStrategy.MAJORITY)

        # Split vote: majority threshold not met → fallback used
        assert consensus.fallback_used is True
        assert consensus.total_votes == 2
        assert consensus.consensus_skill is not None  # fallback still selects best

    def test_full_cycle_metrics_propagate_through_all_stages(
        self, mock_mcp_client: MagicMock
    ):
        """Verify coherence and token counts flow correctly executor → retro → vote."""
        # Mock inflection detector so coherence is fully deterministic.
        # anomaly_score=0.1 → coherence = (0.7 + 0.9) / 2 = 0.8
        mock_detector = MagicMock()
        mock_detector.detect_anomaly.return_value = AnomalyDetection(
            severity=Severity.INFO, score=0.1, issues=[], recommendations=[], should_reexecute=False
        )
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
            inflection_detector=mock_detector,
        )

        # ── Phase 2: Execute ──────────────────────────────────────────────────
        result = executor.execute_task(
            task_description="Metrics propagation test",
            skill_name=_SKILL,
            operation_type="analyze",
            execute_fn=lambda guidance: ("metrics-test-output", {"custom_quality": 0.88}),
        )

        assert result.success is True
        # Coherence = avg(0.7_success + (1.0 - anomaly_score)); clean run → > 0.6
        coherence_val = result.metrics["coherence"]
        assert coherence_val > 0.6

        # ── Phase 3: Build CycleMetrics from executor result → retrospect ─────
        engine = RetrospectionEngine()
        cycle_metrics = CycleMetrics(
            coherence_start=0.5,
            coherence_end=coherence_val,
            tokens_used=result.metrics.get("tokens_used", 0),
            skill_name=_SKILL,
            phase="executing",
            success=True,
        )
        summary = engine.summarize("metrics-cycle-1", cycle_metrics)
        serialized = summary.to_dict()

        # coherence_delta must exactly match the delta we fed in
        assert serialized["coherence_delta"] == pytest.approx(coherence_val - 0.5, abs=1e-9)
        assert serialized["success"] is True
        assert serialized["skill_name"] == _SKILL
        assert serialized["tokens_used"] == cycle_metrics.tokens_used

        # ── Phase 4: Coherence from executor flows into vote weights ───────────
        voter = SkillConsensusVoter(mock_mcp_client)
        skill = _make_skill_score(_SKILL, coherence_val)

        votes = [
            AgentVote(
                agent_id=f"weighted-agent-{i}",
                task_description="Metrics propagation test",
                operation_type="analyze",
                voted_skills=[skill],
                agent_coherence_score=coherence_val,  # use live coherence as weight
            )
            for i in range(2)
        ]
        consensus = voter.vote_on_skills(votes, strategy=VotingStrategy.WEIGHTED)

        assert consensus.consensus_skill is not None
        assert consensus.consensus_skill.skill_name == _SKILL
        # With both agents voting for same skill, weighted consensus achieved
        assert not consensus.fallback_used
