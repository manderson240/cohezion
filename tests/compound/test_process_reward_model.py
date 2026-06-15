"""Tests for ProcessRewardModel — step-level quality scorer.

TDD tests for src/cohezion/compound/process_reward_model.py.

Mocking pattern: @patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
All HTTP is mocked — no live Lemonade connection required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.process_reward_model import (
    ProcessRewardModel,
    StepScoreRecord,
    StepVerdict,
    build_process_reward_model,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_lemonade_response(score_text: str) -> MagicMock:
    """Build a mock urlopen context manager returning a Lemonade chat completion."""
    body = json.dumps({"choices": [{"message": {"content": score_text}}]}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# StepVerdict default values
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_step_verdict_defaults():
    """StepVerdict defaults: score=0.5, is_pass=True (neutral)."""
    v = StepVerdict(step_id="1", step_name="foo")
    assert v.score == 0.5
    assert v.is_pass is True
    assert v.reason == ""
    assert v.latency_seconds == 0.0


# ---------------------------------------------------------------------------
# StepScoreRecord properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_step_score_record_empty_verdicts():
    """Empty record returns neutral/safe defaults on all properties."""
    r = StepScoreRecord(record_id="test", task_description="task")
    assert r.dense_reward == 0.5
    assert r.pass_rate == 1.0
    assert r.min_step_score == 0.5


@pytest.mark.unit
def test_step_score_record_dense_reward():
    """dense_reward is the mean of step scores."""
    r = StepScoreRecord(record_id="r1", task_description="task")
    r.verdicts = [
        StepVerdict(step_id="1", step_name="a", score=0.8),
        StepVerdict(step_id="2", step_name="b", score=0.6),
        StepVerdict(step_id="3", step_name="c", score=0.4),
    ]
    assert abs(r.dense_reward - 0.6) < 1e-9


@pytest.mark.unit
def test_step_score_record_pass_rate_and_min():
    """pass_rate counts is_pass; min_step_score finds the minimum."""
    r = StepScoreRecord(record_id="r2", task_description="task")
    r.verdicts = [
        StepVerdict(step_id="1", step_name="a", score=0.9, is_pass=True),
        StepVerdict(step_id="2", step_name="b", score=0.3, is_pass=False),
        StepVerdict(step_id="3", step_name="c", score=0.7, is_pass=True),
    ]
    assert abs(r.pass_rate - 2 / 3) < 1e-9
    assert r.min_step_score == 0.3


# ---------------------------------------------------------------------------
# Disabled mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_score_step_disabled_returns_neutral():
    """When enabled=False, score_step returns neutral verdict without HTTP call."""
    prm = ProcessRewardModel(enabled=False)
    verdict = prm.score_step("3", "execute_fn", "output", "Produce output")
    assert verdict.score == 0.5
    assert verdict.is_pass is True
    assert verdict.reason == "prm_disabled"


@pytest.mark.unit
def test_record_step_disabled_appends_neutral():
    """record_step with disabled PRM still appends a neutral verdict to the record."""
    prm = ProcessRewardModel(enabled=False)
    rid = prm.begin_execution("test task")
    prm.record_step(rid, "3", "execute_fn", "output", "expectation")
    record = prm.finalize(rid)
    assert len(record.verdicts) == 1
    assert record.verdicts[0].score == 0.5


# ---------------------------------------------------------------------------
# HTTP mock — score parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
def test_score_step_parses_seven(mock_urlopen):
    """Model returns '7' → score=0.7, is_pass=True."""
    mock_urlopen.return_value = _mock_lemonade_response("7")
    prm = ProcessRewardModel()
    verdict = prm.score_step("3", "execute_fn", "output", "expected")
    assert abs(verdict.score - 0.7) < 1e-9
    assert verdict.is_pass is True


@pytest.mark.unit
@patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
def test_score_step_parses_ten(mock_urlopen):
    """Model returns '10' → score=1.0."""
    mock_urlopen.return_value = _mock_lemonade_response("10")
    prm = ProcessRewardModel()
    verdict = prm.score_step("1", "step", "out", "exp")
    assert verdict.score == 1.0
    assert verdict.is_pass is True


@pytest.mark.unit
@patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
def test_score_step_parses_zero(mock_urlopen):
    """Model returns '0' → score=0.0, is_pass=False."""
    mock_urlopen.return_value = _mock_lemonade_response("0")
    prm = ProcessRewardModel()
    verdict = prm.score_step("7", "checker", "out", "exp")
    assert verdict.score == 0.0
    assert verdict.is_pass is False


@pytest.mark.unit
@patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
def test_score_step_out_of_range_clamped(mock_urlopen):
    """Score is clamped: '11' maps to 1.0, '-1' would still be 0.0 (no negatives in parse)."""
    # '11' → value=11 → min(1.0, 11/10) = 1.0
    mock_urlopen.return_value = _mock_lemonade_response("11")
    prm = ProcessRewardModel()
    verdict = prm.score_step("2", "step", "out", "exp")
    assert verdict.score == 1.0


@pytest.mark.unit
def test_parse_score_no_digit_returns_neutral():
    """_parse_score with no digits in raw text returns 0.5."""
    prm = ProcessRewardModel()
    assert prm._parse_score("no digits here") == 0.5


# ---------------------------------------------------------------------------
# Network error handling (non-blocking)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
def test_score_step_network_error_returns_neutral(mock_urlopen):
    """Network failure returns neutral verdict without raising."""
    mock_urlopen.side_effect = OSError("Connection refused")
    prm = ProcessRewardModel()
    verdict = prm.score_step("5", "maker_checker", "out", "exp")
    assert verdict.score == 0.5
    assert verdict.is_pass is True
    assert "prm_error" in verdict.reason


# ---------------------------------------------------------------------------
# Record lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_begin_execution_unique_ids():
    """Each begin_execution() call returns a distinct record_id."""
    prm = ProcessRewardModel(enabled=False)
    ids = {prm.begin_execution("task") for _ in range(20)}
    assert len(ids) == 20


@pytest.mark.unit
def test_finalize_removes_record():
    """finalize() removes the record; a second finalize returns an empty record."""
    prm = ProcessRewardModel(enabled=False)
    rid = prm.begin_execution("task")
    prm.record_step(rid, "1", "a", "out", "exp")
    rec1 = prm.finalize(rid)
    assert len(rec1.verdicts) == 1
    # second finalize → warning, empty record
    rec2 = prm.finalize(rid)
    assert rec2.task_description == ""
    assert len(rec2.verdicts) == 0


@pytest.mark.unit
def test_record_step_unknown_record_returns_neutral():
    """record_step with unknown record_id returns neutral StepVerdict without crashing."""
    prm = ProcessRewardModel(enabled=False)
    v = prm.record_step("nonexistent", "1", "step", "out", "exp")
    assert v.score == 0.5
    assert v.step_id == "1"
    assert v.step_name == "step"


# ---------------------------------------------------------------------------
# Metrics dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_metrics_dict_keys():
    """to_metrics_dict returns the four expected PRM metric keys."""
    r = StepScoreRecord(record_id="r", task_description="t")
    m = ProcessRewardModel.to_metrics_dict(r)
    assert set(m.keys()) == {
        "prm_dense_reward",
        "prm_step_count",
        "prm_pass_rate",
        "prm_min_step_score",
    }
    assert m["prm_step_count"] == 0
    assert m["prm_dense_reward"] == 0.5


# ---------------------------------------------------------------------------
# build_process_reward_model factory
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_process_reward_model_returns_instance():
    """build_process_reward_model() returns a ProcessRewardModel."""
    prm = build_process_reward_model()
    assert isinstance(prm, ProcessRewardModel)
    assert prm.enabled is True
    assert prm.lemonade_url == "http://localhost:13305"


@pytest.mark.unit
def test_build_process_reward_model_disabled():
    """build_process_reward_model(enabled=False) creates a disabled PRM."""
    prm = build_process_reward_model(enabled=False)
    assert prm.enabled is False


# ---------------------------------------------------------------------------
# Discriminating test: is_pass threshold is at 0.6 (not 0.5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch("cohezion.compound.process_reward_model.urllib.request.urlopen")
def test_is_pass_threshold_is_0_6(mock_urlopen):
    """Score of 0.5 (5/10) must NOT pass; 0.6 (6/10) must pass.

    Discriminating: a wrong threshold (e.g. 0.5) would make this fail.
    """
    prm = ProcessRewardModel()

    mock_urlopen.return_value = _mock_lemonade_response("5")
    v5 = prm.score_step("1", "s", "o", "e")
    assert v5.is_pass is False, "5/10 = 0.5 should NOT pass (threshold is 0.6)"

    mock_urlopen.return_value = _mock_lemonade_response("6")
    v6 = prm.score_step("2", "s", "o", "e")
    assert v6.is_pass is True, "6/10 = 0.6 should pass (threshold is >=0.6)"
