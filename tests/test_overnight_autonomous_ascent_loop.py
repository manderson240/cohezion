"""Unit tests for the Overnight Autonomous Kaggle Ascent Loop."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from scripts.kaggle.overnight_autonomous_ascent_loop import (
    OvernightAscentEngine,
    classify_score_delta,
)


def test_classify_score_delta():
    # Higher is better competitions (ARC, CASMI26, ROC-AUC)
    res_gain = classify_score_delta(current=0.350, baseline=0.328, metric_direction="higher")
    assert res_gain["is_sota"] is True
    assert res_gain["delta"] == pytest.approx(0.022)
    assert res_gain["verdict"] == "IMPROVED"

    res_drop = classify_score_delta(current=0.310, baseline=0.328, metric_direction="higher")
    assert res_drop["is_sota"] is False
    assert res_drop["delta"] == pytest.approx(-0.018)
    assert res_drop["verdict"] == "REGRESSED"

    # Lower is better competitions (Log-Loss)
    res_loss_gain = classify_score_delta(current=0.935, baseline=0.943, metric_direction="lower")
    assert res_loss_gain["is_sota"] is True
    assert res_loss_gain["delta"] == pytest.approx(-0.008)
    assert res_loss_gain["verdict"] == "IMPROVED"


@patch("scripts.kaggle.overnight_autonomous_ascent_loop.KaggleApi")
def test_overnight_ascent_engine_cycle(mock_api_cls):
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    sub_pending = MagicMock(
        ref="56786335",
        status="SubmissionStatus.PENDING",
        public_score=None,
        description="RSNA v22",
    )
    sub_complete = MagicMock(
        ref="56786015",
        status="SubmissionStatus.COMPLETE",
        public_score="0.25",
        description="ARC-3 v1",
    )

    def mock_subs(slug):
        if "rsna" in slug:
            return [sub_pending]
        elif "arc-agi-3" in slug:
            return [sub_complete]
        return []

    mock_api.competition_submissions.side_effect = mock_subs

    engine = OvernightAscentEngine(api=mock_api)
    with patch.object(engine.adversarial_engine, "audit_competition", return_value=MagicMock()):
        summary = engine.run_audit_cycle()

    assert "rsna-knee-abnormality-detection" in summary
    assert summary["rsna-knee-abnormality-detection"]["status"] == "SubmissionStatus.PENDING"

    assert "arc-prize-2026-arc-agi-3" in summary
    assert summary["arc-prize-2026-arc-agi-3"]["status"] == "SubmissionStatus.COMPLETE"
    assert summary["arc-prize-2026-arc-agi-3"]["score"] == 0.25


@patch("scripts.kaggle.bleeding_edge_research_engine.persist_to_surrealdb", return_value=True)
@patch("scripts.kaggle.bleeding_edge_research_engine.persist_to_obsidian_vault", return_value=True)
def test_bleeding_edge_research_theorems_ast(mock_obsidian, mock_surreal):
    from scripts.kaggle.bleeding_edge_research_engine import BleedingEdgeResearchEngine, ResearchTopic

    engine = BleedingEdgeResearchEngine()
    dummy_code = (
        "Here are the invariants:\n"
        "```python\n"
        "def verify_euler(v: int, e: int, f: int) -> bool:\n"
        "    return (v - e + f) == 2\n"
        "```\n"
    )
    with patch.object(engine, "query_ollama", return_value=dummy_code):
        res = engine.sprint_arc2_theorems(timeout_sec=5)
        assert res.success is True
        assert res.ast_verified is True
        assert res.topic == ResearchTopic.ARC2_THEOREMS
        assert len(res.invariants_found) == 2


@patch("scripts.kaggle.bleeding_edge_research_engine.persist_to_surrealdb", return_value=True)
@patch("scripts.kaggle.bleeding_edge_research_engine.persist_to_obsidian_vault", return_value=True)
def test_bleeding_edge_research_discussions_sprint(mock_obsidian, mock_surreal):
    from scripts.kaggle.bleeding_edge_research_engine import BleedingEdgeResearchEngine, ResearchTopic

    engine = BleedingEdgeResearchEngine()
    mock_topics = [
        {
            "competition": "arc-prize-2026-arc-agi-2",
            "title": "New LoRA TTT Baseline",
            "signal_score": 85,
            "category": "SOTA_RECIPE",
            "url": "/c/arc-prize-2026-arc-agi-2/discussion/123",
        }
    ]
    with patch("cohezion.researcher.kaggle_discussion_learner.KaggleDiscussionLearner.fetch_competition_discussions", return_value=mock_topics):
        res = engine.sprint_discussions(timeout_sec=5)
        assert res.success is True
        assert res.topic == ResearchTopic.DISCUSSIONS
        assert len(res.invariants_found) >= 1


@patch("scripts.kaggle.overnight_autonomous_ascent_loop.KaggleApi")
def test_overnight_ascent_engine_calls_research_sprint(mock_api_cls):
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api
    mock_api.competition_submissions.return_value = []

    engine = OvernightAscentEngine(api=mock_api)
    mock_sprint = MagicMock(topic=MagicMock(value="discussions_miner"), success=True, invariants_found=["inv1"])
    with patch.object(engine.research_engine, "step", return_value=mock_sprint) as mock_step:
        engine.run_forever(poll_interval_sec=1, max_cycles=1)
        mock_step.assert_called_once()


@patch("cohezion.competitions.adversarial_review_engine.persist_audit_to_surrealdb", return_value=True)
@patch("cohezion.competitions.adversarial_review_engine.persist_audit_to_obsidian", return_value=True)
def test_multiperspective_adversarial_review_engine(mock_obsidian, mock_surreal):
    from cohezion.competitions.adversarial_review_engine import (
        MultiperspectiveAdversarialReviewEngine,
        AdversarialPersona,
    )
    engine = MultiperspectiveAdversarialReviewEngine()
    mock_critique = (
        "Here is the adversarial review:\n"
        "```python\n"
        "def verify_monotonicity(p_abnormal: float, p_acl: float) -> bool:\n"
        "    return p_abnormal >= p_acl\n"
        "```\n"
    )
    with patch.object(engine, "query_persona", return_value=mock_critique):
        report = engine.audit_competition(
            competition_slug="rsna-knee-abnormality-detection",
            current_score=0.939,
            baseline_score=0.943,
            context_notes="Regressed due to rank distortion",
            timeout_per_persona=5.0,
        )
        assert len(report.findings) == 4
        assert len(report.actionable_patches) == 4
        assert report.is_deployable is True
        assert report.competition_slug == "rsna-knee-abnormality-detection"


@patch("scripts.kaggle.bleeding_edge_research_engine.persist_to_surrealdb", return_value=True)
@patch("scripts.kaggle.bleeding_edge_research_engine.persist_to_obsidian_vault", return_value=True)
def test_bleeding_edge_research_adversarial_sprint(mock_obsidian, mock_surreal):
    from scripts.kaggle.bleeding_edge_research_engine import BleedingEdgeResearchEngine, ResearchTopic
    from cohezion.competitions.adversarial_review_engine import AdversarialAuditReport, VulnerabilityFinding, AdversarialPersona

    engine = BleedingEdgeResearchEngine()
    mock_finding = VulnerabilityFinding(
        severity="P1_HIGH",
        persona=AdversarialPersona.CYNICAL_GRANDMASTER,
        title="Rank distortion on log-loss",
        description="Rank transforms Brier probabilities into uniform",
        theoretical_counterexample="Expected loss 1.000 nats",
        proposed_remediation="Remove rank averaging",
        code_patch="def fix(): pass",
        ast_verified=True,
    )
    mock_report = AdversarialAuditReport(
        competition_slug="rsna-knee-abnormality-detection",
        timestamp=12345.0,
        current_score=0.939,
        baseline_score=0.943,
        findings=[mock_finding],
        actionable_patches=["def fix(): pass"],
        is_deployable=True,
    )
    with patch.object(engine.adversarial_reviewer, "audit_competition", return_value=mock_report):
        res = engine.sprint_adversarial_review(summary={}, timeout_sec=5.0)
        assert res.success is True
        assert res.ast_verified is True
        assert res.topic == ResearchTopic.ADVERSARIAL_REVIEW
        assert len(res.invariants_found) >= 1


@patch("scripts.kaggle.overnight_autonomous_ascent_loop.KaggleApi")
def test_overnight_ascent_engine_adversarial_trigger_on_regression(mock_api_cls):
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    sub_regressed = MagicMock(
        ref="56811789",
        status="SubmissionStatus.COMPLETE",
        public_score="0.11",
        description="ARC-3 v28",
    )
    def mock_subs(slug):
        if "arc-agi-3" in slug:
            return [sub_regressed]
        return []

    mock_api.competition_submissions.side_effect = mock_subs

    engine = OvernightAscentEngine(api=mock_api)
    with patch.object(engine.adversarial_engine, "audit_competition") as mock_audit:
        mock_audit.return_value = MagicMock(findings=[1], actionable_patches=[1])
        summary = engine.run_audit_cycle()
        mock_audit.assert_called_once()


@patch("scripts.kaggle.bleeding_edge_research_engine.run_monadic_keep_on_track_pipeline")
def test_bleeding_edge_research_monadic_sprint(mock_pipeline):
    from scripts.kaggle.bleeding_edge_research_engine import BleedingEdgeResearchEngine, ResearchTopic
    from cohezion.agi.ollama_cloud_monad import Either, KaggleTrackState

    mock_state = KaggleTrackState(
        competition_slug="arc-prize-2026-arc-agi-3",
        current_score=0.25,
        baseline_score=0.25,
        active_invariants=["ZobristAcyclicityInvariant"],
        actionable_patches=["def test_inv(): pass"],
    )
    mock_pipeline.return_value = (Either.right(("ok", mock_state)), ["step1", "step2"])

    engine = BleedingEdgeResearchEngine()
    summary = {
        "arc-prize-2026-arc-agi-3": {
            "score": 0.25,
            "baseline": 0.25,
            "metric_direction": "higher",
        }
    }
    res = engine.sprint_monadic_keep_on_track(summary=summary, timeout_sec=5.0)
    assert res.success is True
    assert res.ast_verified is True
    assert res.topic == ResearchTopic.MONADIC_KEEP_ON_TRACK
    assert "ZobristAcyclicityInvariant" in res.invariants_found


@patch("scripts.kaggle.overnight_autonomous_ascent_loop.KaggleApi")
@patch("subprocess.run")
def test_overnight_ascent_engine_kernel_status_object_dispatch(mock_subproc, mock_api_cls):
    mock_api = MagicMock()
    mock_api_cls.return_value = mock_api

    mock_sub = MagicMock(
        ref="56811789",
        status="SubmissionStatus.COMPLETE",
        public_score="0.11",
        description="Older run",
    )
    mock_api.competition_submissions.return_value = [mock_sub]

    kernel_status_obj = MagicMock()
    kernel_status_obj.status = "KernelWorkerStatus.COMPLETE"
    mock_api.kernels_status.return_value = kernel_status_obj

    mock_subproc.return_value = MagicMock(returncode=0)

    engine = OvernightAscentEngine(api=mock_api)
    with patch.object(engine.adversarial_engine, "audit_competition", return_value=MagicMock()):
        summary = engine.run_audit_cycle()

    assert "arc-prize-2026-arc-agi-3" in summary
    assert "COMPLETE" in summary["arc-prize-2026-arc-agi-3"]["kernel_status"]


