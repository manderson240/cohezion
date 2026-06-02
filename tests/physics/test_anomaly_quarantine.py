"""Tests for AnomalyQuarantine (Anomaly Gate Phases 4-5: graph quarantine + Obsidian handoff)."""

from __future__ import annotations

from cohezion.physics.anomaly_quarantine import AnomalyQuarantine, QuarantineRecord


def _survived_adjudication():
    return {
        "verdict": {
            "domain": "mhd",
            "verdict": "anomaly",
            "physical_failed": ["energy"],
            "reason": "energy violated tau while integrity held",
        },
        "skeptic": {
            "survived": True,
            "refutation": None,
            "model": "DeepSeek-Qwen3-8B-GGUF",
            "note": "not dismissable — pending human review",
        },
        "final": "human_review",
    }


def _quarantine(tmp_path):
    captured = []
    q = AnomalyQuarantine(
        surreal_writer=lambda sql: captured.append(sql) or True, vault_dir=tmp_path
    )
    return q, captured


# -- surviving anomaly is quarantined (P4 + P5) -------------------------------


def test_surviving_anomaly_writes_graph_and_markdown(tmp_path):
    q, captured = _quarantine(tmp_path)
    rec = q.quarantine(
        _survived_adjudication(),
        anomaly_id="mhd_energy_run42",
        params={"dt": 0.01, "grid": 64},
        code_ref="hiho_worker.py@abc123",
        frameworks=["Matsumoto_EVO", "My_Big_TOE"],
    )
    assert isinstance(rec, QuarantineRecord) and rec.quarantined and rec.surreal_ok
    # P4: SurrealDB node + framework RELATE edges
    sql = captured[0]
    assert "UPSERT anomaly:mhd_energy_run42 CONTENT" in sql
    assert '"type": "anomaly"' in sql
    assert "generated_under->framework:Matsumoto_EVO" in sql
    # P5: Obsidian markdown exists with review tags + content
    md = (tmp_path / "anomaly-mhd_energy_run42.md").read_text()
    assert "anomaly-review" in md and "requires-human-validation" in md
    assert "energy" in md and "DeepSeek-Qwen3-8B-GGUF" in md
    assert "My_Big_TOE" in md and "0.01" in md


def test_markdown_path_returned(tmp_path):
    q, _ = _quarantine(tmp_path)
    rec = q.quarantine(_survived_adjudication(), anomaly_id="x1")
    assert rec.markdown_path.endswith("anomaly-x1.md")
    assert (tmp_path / "anomaly-x1.md").exists()


# -- non-surviving results are NOT quarantined --------------------------------


def test_rejected_by_skeptic_is_not_quarantined(tmp_path):
    q, captured = _quarantine(tmp_path)
    adj = _survived_adjudication()
    adj["final"] = "rejected_by_skeptic"
    rec = q.quarantine(adj, anomaly_id="x2")
    assert rec.quarantined is False and not captured
    assert not (tmp_path / "anomaly-x2.md").exists()


def test_standard_run_is_not_quarantined(tmp_path):
    q, captured = _quarantine(tmp_path)
    rec = q.quarantine({"verdict": {"domain": "mhd"}, "final": "standard"}, anomaly_id="x3")
    assert rec.quarantined is False and not captured


def test_reject_artifact_is_not_quarantined(tmp_path):
    q, captured = _quarantine(tmp_path)
    rec = q.quarantine({"verdict": {"domain": "gauge"}, "final": "reject"}, anomaly_id="x4")
    assert rec.quarantined is False and not captured


# -- robustness ---------------------------------------------------------------


def test_surreal_failure_still_writes_markdown(tmp_path):
    q = AnomalyQuarantine(surreal_writer=lambda sql: False, vault_dir=tmp_path)
    rec = q.quarantine(_survived_adjudication(), anomaly_id="x5")
    assert rec.quarantined is True  # human handoff still happens
    assert rec.surreal_ok is False
    assert (tmp_path / "anomaly-x5.md").exists()  # P5 independent of P4


def test_identifier_sanitization(tmp_path):
    q, captured = _quarantine(tmp_path)
    q.quarantine(_survived_adjudication(), anomaly_id="mhd/energy:run 42!")
    # slashes/colons/spaces -> underscores in both the surreal id and the filename
    assert "anomaly:mhd_energy_run_42_" in captured[0]
    assert (tmp_path / "anomaly-mhd_energy_run_42_.md").exists()
