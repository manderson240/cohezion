"""Tests for cohezion.inference.lynx_gate — LYNX escalation probe and gate."""

from __future__ import annotations

import math

import numpy as np
import pytest

from cohezion.inference.lynx_gate import (
    EscalationProbe,
    LYNXGate,
    RouteResult,
    _extract_features,
    _N_FEATURES,
)
from cohezion.inference.orchestrator import QualityGate


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# ---------------------------------------------------------------------------
# _extract_features
# ---------------------------------------------------------------------------


def test_extract_features_returns_8d_float32_array():
    feats = _extract_features("hello world.")
    assert isinstance(feats, np.ndarray)
    assert feats.shape == (_N_FEATURES,)
    assert feats.shape == (8,)
    assert feats.dtype == np.float32


def test_extract_features_empty_string():
    # Empty text: no words, n_words clamps to 1, no ZeroDivisionError.
    feats = _extract_features("")
    f0, f1, f2, f3, f4 = feats[0], feats[1], feats[2], feats[3], feats[4]
    assert f0 == 0.0  # log1p(0) / 10 == 0
    assert f1 == 0.0  # no terminator (empty text guarded)
    assert f2 == 0.0  # 0 unique / 1
    assert f3 == 0.0  # sum(len) == 0
    assert f4 == 0.0  # no question word


def test_extract_features_completeness_terminator_flag():
    # Ends in '.' -> f1 == 1.0
    feats_dot = _extract_features("This is a sentence.")
    assert feats_dot[1] == 1.0
    # Ends in a letter -> f1 == 0.0
    feats_letter = _extract_features("This is incomplete")
    assert feats_letter[1] == 0.0


def test_extract_features_vocabulary_diversity():
    feats_dup = _extract_features("a a a")
    assert feats_dup[2] == pytest.approx(1.0 / 3.0, abs=1e-6)
    feats_uniq = _extract_features("a b c")
    assert feats_uniq[2] == pytest.approx(1.0)


def test_extract_features_avg_word_length_normalization():
    # Two words each of length 8 -> sum(len)=16, n_words=2 -> 16/(2*8) == 1.0
    feats = _extract_features("aaaaaaaa bbbbbbbb")
    assert feats[3] == pytest.approx(1.0, abs=1e-6)


def test_extract_features_question_word_detection_first_100_chars():
    # Question word within first 100 chars -> f4 == 1.0
    feats_in = _extract_features("What is the meaning of life?")
    assert feats_in[4] == 1.0
    # Question word only after char 100 -> f4 == 0.0
    filler = "x" * 105
    feats_out = _extract_features(filler + " how")
    assert feats_out[4] == 0.0


def test_extract_features_output_type_one_hot():
    cat = _extract_features("foo", output_type="short_categorical")
    assert (cat[5], cat[6], cat[7]) == (1.0, 0.0, 0.0)
    ans = _extract_features("foo", output_type="short_answer")
    assert (ans[5], ans[6], ans[7]) == (0.0, 1.0, 0.0)
    other = _extract_features("foo", output_type="reasoning")
    assert (other[5], other[6], other[7]) == (0.0, 0.0, 1.0)


def test_extract_features_strips_whitespace():
    # Leading/trailing whitespace stripped before feature computation.
    raw = "   hello world.   "
    stripped = "hello world."
    feats_raw = _extract_features(raw)
    feats_stripped = _extract_features(stripped)
    # f0 reflects stripped length
    assert feats_raw[0] == pytest.approx(math.log1p(len(stripped)) / 10.0, abs=1e-6)
    # f1 terminator reflects stripped text (ends in '.')
    assert feats_raw[1] == 1.0
    assert feats_raw[0] == pytest.approx(feats_stripped[0], abs=1e-6)


# ---------------------------------------------------------------------------
# EscalationProbe.load
# ---------------------------------------------------------------------------


def test_probe_load_returns_fallback_when_file_missing(tmp_path):
    missing = tmp_path / "does_not_exist.npz"
    probe = EscalationProbe.load(missing)
    assert probe.weights is None
    assert probe.fallback_gate == QualityGate(min_chars=200)


def test_probe_load_reads_weights_bias_threshold_from_npz(tmp_path):
    path = tmp_path / "probe.npz"
    weights = np.arange(8, dtype=np.float64)
    np.savez(path, weights=weights, bias=1.5, threshold=0.7)
    probe = EscalationProbe.load(path)
    assert probe.weights is not None
    np.testing.assert_array_equal(probe.weights, weights)
    assert probe.bias == pytest.approx(1.5)
    assert probe.threshold == pytest.approx(0.7)


def test_probe_load_threshold_defaults_to_half_when_absent(tmp_path):
    path = tmp_path / "probe_nothreshold.npz"
    np.savez(path, weights=np.zeros(8), bias=0.0)
    probe = EscalationProbe.load(path)
    assert probe.threshold == pytest.approx(0.5)


def test_probe_load_corrupt_file_falls_back(tmp_path):
    path = tmp_path / "corrupt.npz"
    path.write_text("this is not a valid npz file")
    probe = EscalationProbe.load(path)  # must not raise
    assert probe.weights is None


# ---------------------------------------------------------------------------
# EscalationProbe.predict_escalate — fallback mode
# ---------------------------------------------------------------------------


def test_predict_escalate_fallback_short_text_escalates():
    probe = EscalationProbe(weights=None)  # fallback gate min_chars=200
    should_escalate, conf = probe.predict_escalate("short answer")
    assert should_escalate is True
    assert conf == 0.5


def test_predict_escalate_fallback_long_text_accepts():
    probe = EscalationProbe(weights=None)
    long_text = "x" * 250
    should_escalate, conf = probe.predict_escalate(long_text)
    assert should_escalate is False
    assert conf == 0.5


def test_predict_escalate_fallback_empty_text_escalates():
    probe = EscalationProbe(weights=None)
    should_escalate, conf = probe.predict_escalate("   ")
    assert should_escalate is True
    assert conf == 0.5


# ---------------------------------------------------------------------------
# EscalationProbe.predict_escalate — categorical override
# ---------------------------------------------------------------------------


def test_predict_escalate_categorical_override_short_accepts():
    # Trained weights present but categorical + short bypasses probe.
    probe = EscalationProbe(weights=np.ones(8, dtype=np.float64), bias=100.0)
    should_escalate, conf = probe.predict_escalate("A", output_type="short_categorical")
    assert should_escalate is False
    assert conf == 0.05


def test_predict_escalate_categorical_override_boundary_len_10():
    probe = EscalationProbe(weights=np.zeros(8, dtype=np.float64), bias=0.0, threshold=0.5)
    # Exactly 10 chars -> override applies.
    ten = "1234567890"
    assert len(ten) == 10
    se10, conf10 = probe.predict_escalate(ten, output_type="short_categorical")
    assert se10 is False
    assert conf10 == 0.05
    # 11 chars -> falls through to probe (logit 0 -> prob 0.5 >= 0.5 -> escalate True).
    eleven = "12345678901"
    assert len(eleven) == 11
    se11, conf11 = probe.predict_escalate(eleven, output_type="short_categorical")
    assert se11 is True
    assert conf11 == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# EscalationProbe.predict_escalate — probe / sigmoid math
# ---------------------------------------------------------------------------


def test_predict_escalate_probe_sigmoid_threshold_boundary():
    threshold = 0.6
    target_logit = math.log(threshold / (1 - threshold))  # logit s.t. sigmoid == threshold
    text = "answer."
    feats = _extract_features(text, "short_answer")
    # Use a single active weight on f0 (length feature) to control the logit precisely.
    # logit = w0*f0 + bias. Set w0=0, drive logit purely with bias.
    weights = np.zeros(8, dtype=np.float64)

    # Just above threshold -> escalate True.
    probe_above = EscalationProbe(weights=weights, bias=target_logit + 0.05, threshold=threshold)
    se_above, conf_above = probe_above.predict_escalate(text, "short_answer")
    assert se_above is True
    assert conf_above == pytest.approx(_sigmoid(target_logit + 0.05), abs=1e-9)
    assert conf_above >= threshold

    # Just below threshold -> escalate False.
    probe_below = EscalationProbe(weights=weights, bias=target_logit - 0.05, threshold=threshold)
    se_below, conf_below = probe_below.predict_escalate(text, "short_answer")
    assert se_below is False
    assert conf_below == pytest.approx(_sigmoid(target_logit - 0.05), abs=1e-9)
    assert conf_below < threshold

    # Confidence equals the sigmoid value (sanity: independent of feats since w=0).
    _ = feats  # feats unused for math because weights are zero; documents intent


def test_predict_escalate_probe_zero_weights_returns_sigmoid_of_bias():
    probe = EscalationProbe(weights=np.zeros(8, dtype=np.float64), bias=0.0, threshold=0.5)
    should_escalate, conf = probe.predict_escalate("some answer", "short_answer")
    assert conf == pytest.approx(0.5)
    assert should_escalate is True  # 0.5 >= 0.5


def test_predict_escalate_probe_negative_logit_low_prob():
    # Strongly negative logit -> prob near 0, no overflow.
    probe = EscalationProbe(weights=np.zeros(8, dtype=np.float64), bias=-50.0, threshold=0.5)
    should_escalate, conf = probe.predict_escalate("some answer", "short_answer")
    assert conf == pytest.approx(0.0, abs=1e-6)
    assert should_escalate is False


# ---------------------------------------------------------------------------
# LYNXGate.from_probe / is_trained
# ---------------------------------------------------------------------------


def test_lynxgate_from_probe_missing_weights_is_not_trained(tmp_path, monkeypatch):
    # EscalationProbe.load() binds _PROBE_PATH as a default arg at def time, so we
    # patch the classmethod's default tuple to point at a nonexistent path.
    missing = tmp_path / "nope.npz"
    monkeypatch.setattr(EscalationProbe.load.__func__, "__defaults__", (missing,))
    gate = LYNXGate.from_probe()
    assert gate.is_trained is False
    assert gate.probe.weights is None


def test_lynxgate_from_probe_with_trained_file_is_trained(tmp_path, monkeypatch):
    path = tmp_path / "trained.npz"
    np.savez(path, weights=np.zeros(8), bias=0.0, threshold=0.5)
    monkeypatch.setattr(EscalationProbe.load.__func__, "__defaults__", (path,))
    gate = LYNXGate.from_probe()
    assert gate.is_trained is True
    assert gate.probe.weights is not None


# ---------------------------------------------------------------------------
# LYNXGate.check
# ---------------------------------------------------------------------------


def test_lynxgate_check_error_result_fails():
    gate = LYNXGate(probe=EscalationProbe(weights=None))
    result = RouteResult(text="anything", model="npu", lane="npu", latency_ms=0.0, error="boom")
    passed, reason = gate.check(result)
    assert passed is False
    assert reason == "error=boom"


def test_lynxgate_check_accept_returns_true_reason():
    # Fallback probe + long text -> do not escalate -> accept.
    gate = LYNXGate(probe=EscalationProbe(weights=None))
    long_text = "y" * 250
    result = RouteResult(text=long_text, model="npu", lane="npu", latency_ms=0.0)
    passed, reason = gate.check(result)
    assert passed is True
    assert reason.startswith("lynx-probe: accept")
    # confidence shown is 1 - confidence == 1 - 0.5 == 0.5
    assert "conf=0.500" in reason


def test_lynxgate_check_escalate_returns_false_reason():
    # Fallback probe + short text -> escalate.
    gate = LYNXGate(probe=EscalationProbe(weights=None))
    result = RouteResult(text="short", model="npu", lane="npu", latency_ms=0.0)
    passed, reason = gate.check(result)
    assert passed is False
    assert reason.startswith("lynx-probe: escalate")


def test_lynxgate_check_records_decision_when_collecting():
    gate = LYNXGate(
        probe=EscalationProbe(weights=None),
        output_type="short_answer",
        collect_data=True,
    )
    result = RouteResult(text="short", model="npu", lane="npu", latency_ms=0.0)
    gate.check(result)
    assert len(gate._decisions) == 1
    d = gate._decisions[0]
    assert set(d.keys()) == {"ts", "text_len", "escalated", "confidence", "output_type"}
    assert d["text_len"] == len("short")
    assert d["escalated"] is True  # short text in fallback escalates
    assert d["output_type"] == "short_answer"


def test_lynxgate_check_no_record_when_collect_disabled():
    gate = LYNXGate(probe=EscalationProbe(weights=None), collect_data=False)
    result = RouteResult(text="short", model="npu", lane="npu", latency_ms=0.0)
    gate.check(result)
    assert gate._decisions == []


def test_lynxgate_check_accepts_plain_string_result():
    # check uses result.text via hasattr, then result.error.
    # A RouteResult (error=None default) drives both branches; the str(result)
    # fallback exists for objects without .text, but .error access still requires
    # an object exposing .error. Document via a RouteResult whose .text is used.
    gate = LYNXGate(probe=EscalationProbe(weights=None))
    long_text = "z" * 250
    result = RouteResult(text=long_text, model="npu", lane="npu", latency_ms=0.0)
    passed, reason = gate.check(result)
    assert passed is True
    assert reason.startswith("lynx-probe: accept")


def test_is_trained_reflects_probe_weights():
    assert LYNXGate(probe=EscalationProbe(weights=None)).is_trained is False
    assert LYNXGate(probe=EscalationProbe(weights=np.zeros(8))).is_trained is True
