"""Unit tests for scripts/session_end.py.

Network + git + cohezion imports are mocked. Covers the pure logic: aggregation,
CycleMetrics construction, execution_result shape, dry-run path.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import session_end


def test_fetch_session_signals_aggregates_gates_narratives_drifts() -> None:
    """Surreal calls are mocked; verify the aggregate math."""
    gates = [{"passed": True}, {"passed": True}, {"passed": False}]
    narratives = [
        {"latency_ms": 500.0, "tokens_used": 30},
        {"latency_ms": 750.0, "tokens_used": 45},
    ]
    drifts = [{"drift_count": 2}, {"drift_count": 1}]

    responses = [gates, narratives, drifts]

    def fake_query(_sql: str):
        return responses.pop(0)

    with patch.object(session_end, "_surreal_query", side_effect=fake_query):
        signals = session_end.fetch_session_signals("sess-xyz")

    assert signals["total_gates"] == 3
    assert signals["passed_gates"] == 2
    assert signals["pass_rate"] == 2 / 3
    assert signals["narrative_count"] == 2
    assert signals["narrative_latency_ms_total"] == 1250.0
    assert signals["narrative_tokens_total"] == 75  # 30 + 45 from tokens_used field
    assert signals["drift_count"] == 3
    # anomaly_score = min(1.0, 3 / max(1, 2*2)) = 0.75
    assert signals["anomaly_score"] == 0.75


def test_fetch_session_signals_handles_no_data() -> None:
    with patch.object(session_end, "_surreal_query", return_value=None):
        signals = session_end.fetch_session_signals("sess-empty")
    assert signals["total_gates"] == 0
    assert signals["narrative_count"] == 0
    assert signals["pass_rate"] == 1.0  # default when no gates recorded


def test_build_execution_result_shape_matches_skill_refiner_contract() -> None:
    """SkillRefiner._extract_metrics reads specific keys. The shape produced
    here must match that contract or refinement silently no-ops."""
    signals = {
        "pass_rate": 0.9,
        "narrative_latency_ms_total": 2500.0,
        "narrative_tokens_total": 150,
        "narrative_count": 2,
        "anomaly_score": 0.1,
        "drift_count": 0,
    }
    er = session_end.build_execution_result(signals)
    assert er["success"] is True  # pass_rate >= 0.8 AND drift_count == 0
    assert er["duration_seconds"] == 2.5
    assert er["metrics"]["anomaly_score"] == 0.1
    # Real token count preferred over latency-as-proxy
    assert er["token_metrics"]["tokens_used"] == 150
    assert er["token_metrics"]["cache_hits"] == 0


def test_build_execution_result_falls_back_to_latency_for_legacy_records() -> None:
    """Records written before tokens_used was added have narrative_tokens_total=0.
    The builder falls back to latency_ms as a rough proxy so old sessions still
    produce SOME signal for SkillRefiner."""
    signals = {
        "pass_rate": 0.9,
        "narrative_latency_ms_total": 2500.0,
        "narrative_tokens_total": 0,  # legacy — field didn't exist at write time
        "narrative_count": 2,
        "anomaly_score": 0.1,
        "drift_count": 0,
    }
    er = session_end.build_execution_result(signals)
    # Fallback: use latency as tokens proxy (the pre-2026-04-22 behavior)
    assert er["token_metrics"]["tokens_used"] == 2500


def test_build_execution_result_zero_tokens_when_no_narratives() -> None:
    """If there are no narratives at all, tokens_used is 0 — we don't fabricate
    a fake token count from latency when there's nothing to count."""
    signals = {
        "pass_rate": 1.0,
        "narrative_latency_ms_total": 0.0,
        "narrative_tokens_total": 0,
        "narrative_count": 0,
        "anomaly_score": 0.0,
        "drift_count": 0,
    }
    er = session_end.build_execution_result(signals)
    assert er["token_metrics"]["tokens_used"] == 0


def test_build_execution_result_marks_failure_on_drift() -> None:
    """Even with a high pass rate, ANY import drift marks the session as
    unsuccessful so SkillRefiner skips (refinement is success-only)."""
    signals = {
        "pass_rate": 0.95,
        "narrative_latency_ms_total": 100.0,
        "narrative_tokens_total": 5,
        "narrative_count": 1,
        "anomaly_score": 0.3,
        "drift_count": 1,  # one drift = failure
    }
    er = session_end.build_execution_result(signals)
    assert er["success"] is False


def test_build_execution_result_marks_failure_on_low_pass_rate() -> None:
    signals = {
        "pass_rate": 0.5,
        "narrative_latency_ms_total": 100.0,
        "narrative_tokens_total": 5,
        "narrative_count": 1,
        "anomaly_score": 0.4,
        "drift_count": 0,
    }
    er = session_end.build_execution_result(signals)
    assert er["success"] is False


def test_session_id_prefers_env_var(monkeypatch) -> None:
    monkeypatch.setenv("COHEZION_SESSION_ID", "custom-session")
    assert session_end._session_id() == "custom-session"


def test_session_id_falls_back_to_pid(monkeypatch) -> None:
    monkeypatch.delenv("COHEZION_SESSION_ID", raising=False)
    sid = session_end._session_id()
    assert sid.startswith("pid-")
    assert sid[4:].isdigit()


def test_main_dry_run_exits_0_without_side_effects(capsys, monkeypatch, tmp_path) -> None:
    """--dry-run shows the aggregation but never touches vault / SurrealDB / skills."""
    signals = {
        "session_id": "sess-xyz",
        "total_gates": 3,
        "passed_gates": 3,
        "pass_rate": 1.0,
        "narrative_count": 2,
        "narrative_latency_ms_total": 1000.0,
        "narrative_tokens_total": 100,
        "drift_count": 0,
        "anomaly_score": 0.0,
        "_raw_narratives": [],
        "_raw_gates": [],
    }
    with (
        patch.object(session_end, "fetch_session_signals", return_value=signals),
        patch.object(session_end, "session_commits_touching_skills", return_value=[]),
    ):
        rc = session_end.main(["--session-id", "sess-xyz", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "gates=3" in out
    assert "dry-run" in out


def test_main_returns_1_when_no_session_data(capsys, monkeypatch) -> None:
    empty = {
        "session_id": "sess-empty",
        "total_gates": 0,
        "passed_gates": 0,
        "pass_rate": 1.0,
        "narrative_count": 0,
        "narrative_latency_ms_total": 0.0,
        "narrative_tokens_total": 0,
        "drift_count": 0,
        "anomaly_score": 0.0,
        "_raw_narratives": [],
        "_raw_gates": [],
    }
    with patch.object(session_end, "fetch_session_signals", return_value=empty):
        rc = session_end.main(["--session-id", "sess-empty"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no per-commit signals" in err


def test_build_cycle_metrics_reflects_signals_in_coherence_and_anomalies() -> None:
    """CycleMetrics fields feed directly into RetrospectionEngine.summarize()
    narrative — shape them so the narrative is actually informative."""
    signals = {
        "pass_rate": 1.0,  # clean session
        "narrative_latency_ms_total": 3000.0,
        "narrative_tokens_total": 200,
        "narrative_count": 3,
        "drift_count": 0,
        "anomaly_score": 0.0,
    }
    metrics = session_end.build_cycle_metrics(signals, "test-skill")
    assert metrics.skill_name == "test-skill"
    assert metrics.phase == "reflecting"
    assert metrics.success is True
    assert metrics.coherence_end > metrics.coherence_start  # moved up from 0.5
    assert metrics.anomalies == []
    assert metrics.tokens_used == 200  # uses real tokens_used, not latency proxy


def test_build_cycle_metrics_records_anomalies_on_bad_session() -> None:
    signals = {
        "pass_rate": 0.5,
        "narrative_latency_ms_total": 500.0,
        "narrative_tokens_total": 20,
        "narrative_count": 1,
        "drift_count": 3,
        "anomaly_score": 0.75,
    }
    metrics = session_end.build_cycle_metrics(signals, "bad-skill")
    assert metrics.success is False
    assert any("drift" in a for a in metrics.anomalies)
    assert any("pass_rate" in a for a in metrics.anomalies)


def test_write_retrospection_to_vault_writes_markdown(tmp_path) -> None:
    """Happy path: given a summary + signals + tmp vault root, a frontmatter-
    prefixed markdown file appears at retrospections/<session-id>.md."""
    from dataclasses import dataclass

    from cohezion.compound.retrospection_summary import CycleMetrics

    @dataclass
    class FakeSummary:
        cycle_id: str = "session-test"
        narrative: str = "I refined the skill cleanly."
        metrics: CycleMetrics = None
        insights: list[str] = None

    summary = FakeSummary(
        metrics=CycleMetrics(
            coherence_start=0.5,
            coherence_end=0.7,
            tokens_used=100,
            skill_name="test",
            phase="reflecting",
            success=True,
        ),
        insights=["insight A", "insight B"],
    )
    signals = {
        "pass_rate": 1.0,
        "total_gates": 5,
        "passed_gates": 5,
        "narrative_count": 3,
        "drift_count": 0,
        "anomaly_score": 0.0,
    }
    path = session_end.write_retrospection_to_vault("sess-x", summary, signals, vault_root=tmp_path)
    assert path is not None
    content = path.read_text()
    assert "title: Session retrospection" in content
    assert "I refined the skill cleanly." in content
    assert "insight A" in content
    assert "Gates recorded: 5 (5 passed)" in content
