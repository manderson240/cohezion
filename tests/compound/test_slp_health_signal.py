"""CB14 S_LP (Learning-Potential Score) health signal tests.

Tests for the S_LP pipeline in the autonomous loop:
  - _compute_slp is None-safe for FLM/NPU responses (no logprobs)
  - _compute_slp produces correct positive values from logprob sequences
  - CB14: S_LP is sign-correct and discriminating (distinct inputs → distinct outputs)
  - Coordinator _record_result wires DegradationDetector without phantom cache/coherence alerts
"""

from __future__ import annotations

from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    LoopTask,
    RunReport,
    SprintResult,
)
from cohezion.compound.autonomous_loop.local_executor import _compute_slp, _error_result
from cohezion.compound.degradation_detector import DegradationDetector


# ── S_LP helper — None-safety (FLM/NPU tier) ─────────────────────────────────


class TestComputeSlpNoneSafety:
    """_compute_slp must never raise; returns None for all degenerate API shapes."""

    def test_flm_logprobs_none_returns_none(self):
        """FLM-backed NPU tier returns logprobs:None — must not raise or compute."""
        resp = {"choices": [{"logprobs": None, "message": {"content": "ok"}}]}
        assert _compute_slp(resp) is None

    def test_empty_choices_returns_none(self):
        resp = {"choices": []}
        assert _compute_slp(resp) is None

    def test_missing_choices_key_returns_none(self):
        assert _compute_slp({}) is None

    def test_empty_logprobs_content_returns_none(self):
        resp = {"choices": [{"logprobs": {"content": []}}]}
        assert _compute_slp(resp) is None

    def test_null_logprobs_content_returns_none(self):
        resp = {"choices": [{"logprobs": {"content": None}}]}
        assert _compute_slp(resp) is None


# ── CB14: S_LP sign-correct and discriminating ───────────────────────────────


class TestComputeSlpCB14:
    """CB14: S_LP is positive, non-trivial, and discriminating across different inputs."""

    def _make_resp(self, logprobs: list[float]) -> dict:
        return {
            "choices": [
                {
                    "logprobs": {
                        "content": [
                            {"token": f"t{i}", "logprob": lp} for i, lp in enumerate(logprobs)
                        ]
                    },
                    "message": {"content": "output"},
                }
            ]
        }

    def test_slp_is_positive(self):
        """Logprobs are negative → S_LP = -mean(logprobs) > 0."""
        resp = self._make_resp([-0.1, -0.2, -0.05, -0.3, -0.15, -0.08])
        slp = _compute_slp(resp)
        assert slp is not None and slp > 0.0

    def test_slp_anchored_to_empirical_baseline(self):
        """Six tokens with mean logprob -0.1040 → S_LP ≈ 0.1040 (measured baseline)."""
        resp = self._make_resp([-0.1040] * 6)
        slp = _compute_slp(resp)
        assert slp is not None
        assert abs(slp - 0.1040) < 1e-6

    def test_cb14_distinct_inputs_produce_distinct_outputs(self):
        """S_LP is discriminating: different logprob distributions → different scores."""
        high = self._make_resp([-0.5, -0.6, -0.7, -0.4, -0.55])
        low = self._make_resp([-0.05, -0.02, -0.01, -0.03, -0.04])
        slp_high = _compute_slp(high)
        slp_low = _compute_slp(low)
        assert slp_high is not None and slp_low is not None
        assert slp_high > slp_low, f"high={slp_high:.4f} should exceed low={slp_low:.4f}"

    def test_slp_single_token(self):
        """Edge case: one output token — must compute, not divide-by-zero."""
        resp = self._make_resp([-0.25])
        slp = _compute_slp(resp)
        assert slp is not None
        assert abs(slp - 0.25) < 1e-9


# ── _error_result includes token_surprisal and tried_models ──────────────────


class TestErrorResultFields:
    def test_error_result_has_token_surprisal_none(self):
        result = _error_result("t1", "Gemma-4-E4B-it-GGUF", "gpu", "timeout", returncode=2)
        assert "token_surprisal" in result
        assert result["token_surprisal"] is None

    def test_error_result_has_tried_models(self):
        result = _error_result("t1", "llama3.2-1b-FLM", "npu", "HTTP 500", returncode=2)
        assert "tried_models" in result
        assert result["tried_models"] == ["llama3.2-1b-FLM"]


# ── Coordinator wiring — no phantom cache/coherence alerts ───────────────────


def _make_task(task_id: str = "t-001") -> LoopTask:
    return LoopTask(
        id=task_id,
        description="Test task",
        category="test",
        priority=5,
        verification="Check result",
        estimated_tokens=100,
    )


def _call_record(
    coordinator: LoopCoordinator,
    result: dict,
    task: LoopTask,
    is_cloud: bool = False,
) -> RunReport:
    report = RunReport()
    fail_counts: dict[str, int] = {}
    category_stats: dict[str, dict[str, int]] = {}
    sprint = SprintResult()
    coordinator._record_result(
        result,
        task,
        is_cloud,
        result.get("tokens_used", 0),
        report,
        fail_counts,
        category_stats,
        sprint,
    )
    return report


class TestCoordinatorDetectorWiring:
    """_record_result wires DegradationDetector correctly without phantom alerts."""

    def test_detector_wired_by_default(self):
        """LoopCoordinator auto-creates DegradationDetector when none provided."""
        coord = LoopCoordinator(LoopConfig(use_local_inference=False))
        assert coord._degradation_detector is not None

    def test_custom_detector_accepted(self):
        """Caller-provided detector is stored and used."""
        detector = DegradationDetector()
        coord = LoopCoordinator(
            LoopConfig(use_local_inference=False), degradation_detector=detector
        )
        assert coord._degradation_detector is detector

    def test_no_phantom_cache_alerts_after_many_tasks(self):
        """20 tasks without cache data must not fire cache_hit_rate alerts."""
        detector = DegradationDetector()
        coord = LoopCoordinator(
            LoopConfig(use_local_inference=False), degradation_detector=detector
        )
        for i in range(20):
            result = {
                "task_id": f"t-{i:03d}",
                "success": True,
                "tokens_used": 50,
                "model": "Gemma-4-E4B-it-GGUF",
                "node": "gpu",
                "elapsed_ms": 200.0,
                "tried_models": ["Gemma-4-E4B-it-GGUF"],
                "token_surprisal": 0.1040,
            }
            _call_record(coord, result, _make_task(f"t-{i:03d}"))
        summary = detector.get_alert_summary()
        assert "cache_hit_rate" not in summary["by_metric"], (
            f"Phantom cache_hit_rate alerts fired: {summary['by_metric']}"
        )

    def test_no_phantom_coherence_alerts_after_many_tasks(self):
        """20 successful tasks must not fire coherence alerts (success≠coherence)."""
        detector = DegradationDetector()
        coord = LoopCoordinator(
            LoopConfig(use_local_inference=False), degradation_detector=detector
        )
        for i in range(20):
            result = {
                "task_id": f"t-{i:03d}",
                "success": True,
                "tokens_used": 50,
                "model": "Gemma-4-E4B-it-GGUF",
                "node": "gpu",
                "elapsed_ms": 200.0,
                "tried_models": ["Gemma-4-E4B-it-GGUF"],
                "token_surprisal": 0.1040,
            }
            _call_record(coord, result, _make_task(f"t-{i:03d}"))
        summary = detector.get_alert_summary()
        assert "coherence" not in summary["by_metric"], (
            f"Phantom coherence alerts fired: {summary['by_metric']}"
        )

    def test_token_surprisal_baseline_established_after_sufficient_calls(self):
        """After 6 tasks with token_surprisal, the S_LP baseline is established."""
        detector = DegradationDetector()
        coord = LoopCoordinator(
            LoopConfig(use_local_inference=False), degradation_detector=detector
        )
        for i in range(6):
            result = {
                "task_id": f"t-{i:03d}",
                "success": True,
                "tokens_used": 50,
                "model": "Gemma-4-E4B-it-GGUF",
                "node": "gpu",
                "elapsed_ms": 200.0,
                "tried_models": ["Gemma-4-E4B-it-GGUF"],
                "token_surprisal": 0.1040 + i * 0.002,
            }
            _call_record(coord, result, _make_task(f"t-{i:03d}"))
        stats = detector.get_baseline_stats()
        assert stats["token_surprisal"]["is_established"], (
            "token_surprisal baseline not established after 6 calls"
        )
        assert stats["token_surprisal"]["num_samples"] == 6

    def test_npu_none_surprisal_excluded_from_baseline(self):
        """NPU tasks with token_surprisal=None must not pollute the S_LP baseline."""
        detector = DegradationDetector()
        coord = LoopCoordinator(
            LoopConfig(use_local_inference=False), degradation_detector=detector
        )
        for i in range(10):
            result = {
                "task_id": f"t-{i:03d}",
                "success": True,
                "tokens_used": 10,
                "model": "llama3.2-1b-FLM",
                "node": "npu",
                "elapsed_ms": 24.0,
                "tried_models": ["llama3.2-1b-FLM"],
                "token_surprisal": None,  # FLM — no logprobs
            }
            _call_record(coord, result, _make_task(f"t-{i:03d}"))
        stats = detector.get_baseline_stats()
        assert not stats["token_surprisal"]["is_established"], (
            "token_surprisal baseline must NOT be established from None-only samples"
        )
        assert stats["token_surprisal"]["num_samples"] == 0
