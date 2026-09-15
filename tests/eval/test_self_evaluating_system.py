"""Unit tests for SelfEvaluatingSystem (3-Layer LLM Evaluation & Regression Pipeline)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from cohezion.eval.self_evaluating_system import (
    DeterministicEvaluator,
    EvalRun,
    LocalLLMJudge,
    RegressionPipeline,
    SelfEvaluatingOrchestrator,
    check_judge_drift,
    is_improvement_significant,
    measure_cohens_kappa,
)


class TestDeterministicEvaluator:
    """Test Layer 1 deterministic checks."""

    def setup_method(self):
        self.evaluator = DeterministicEvaluator()

    def test_json_validity_success(self):
        res = self.evaluator.check_json_validity('{"status": "ok", "value": 42}')
        assert res.passed is True
        assert res.score == 1.0

    def test_json_validity_failure(self):
        res = self.evaluator.check_json_validity('{"status": "ok", value: invalid}')
        assert res.passed is False
        assert res.score == 0.0
        assert "Invalid JSON" in res.details

    def test_length_bounds(self):
        short_res = self.evaluator.check_length_bounds("hi", min_chars=10)
        assert short_res.passed is False

        ok_res = self.evaluator.check_length_bounds("hello world this is long enough", min_chars=10)
        assert ok_res.passed is True

        long_res = self.evaluator.check_length_bounds("a" * 100, max_chars=50)
        assert long_res.passed is False

    def test_no_hallucinated_links(self):
        clean_res = self.evaluator.check_no_hallucinated_links("No URLs here at all.")
        assert clean_res.passed is True

        bad_res = self.evaluator.check_no_hallucinated_links(
            "Check out https://fake-domain.xyz/api"
        )
        assert bad_res.passed is False
        assert "Found 1 URLs" in bad_res.details

    def test_required_sections(self):
        text = "# Summary\nAll good.\n# Next Steps\nDo work."
        ok_res = self.evaluator.check_required_sections(text, ["Summary", "Next Steps"])
        assert ok_res.passed is True

        missing_res = self.evaluator.check_required_sections(
            text, ["Summary", "Architecture", "Risks"]
        )
        assert missing_res.passed is False
        assert missing_res.score < 1.0
        assert "Architecture" in missing_res.details

    def test_no_refusal(self):
        ok_res = self.evaluator.check_no_refusal("Here is the requested solution in Python.")
        assert ok_res.passed is True

        refused_res = self.evaluator.check_no_refusal(
            "I'm unable to answer that question as an AI."
        )
        assert refused_res.passed is False

    def test_code_syntax(self):
        valid_code = "```python\ndef add(a: int, b: int) -> int:\n    return a + b\n```"
        res = self.evaluator.check_code_syntax(valid_code)
        assert res.passed is True

        invalid_code = "```python\ndef broken(:\n    return\n```"
        bad_res = self.evaluator.check_code_syntax(invalid_code)
        assert bad_res.passed is False
        assert "SyntaxError" in bad_res.details


class TestLocalLLMJudge:
    """Test Layer 2 LLM-as-judge."""

    @patch("httpx.Client")
    def test_evaluate_single_criterion(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "score": 5,
                                "reasoning": "Directly and completely answers the prompt.",
                            }
                        )
                    }
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        judge = LocalLLMJudge()
        res = judge.evaluate("What is 2+2?", "2+2 equals 4.", "relevance")

        assert res.score == 5
        assert res.criterion == "relevance"
        assert "Directly" in res.reasoning

    @patch("httpx.Client")
    def test_evaluate_with_consensus(self, mock_client_cls):
        # Return scores 4, 5, 4 across 3 calls
        responses = [
            MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [
                        {"message": {"content": json.dumps({"score": 4, "reasoning": "Good."})}}
                    ]
                },
            ),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [
                        {"message": {"content": json.dumps({"score": 5, "reasoning": "Great."})}}
                    ]
                },
            ),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [
                        {"message": {"content": json.dumps({"score": 4, "reasoning": "Good."})}}
                    ]
                },
            ),
        ]
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = responses
        mock_client_cls.return_value = mock_client

        judge = LocalLLMJudge()
        res = judge.evaluate_with_consensus("Question", "Answer", "accuracy", num_judges=3)

        assert res.score == 4
        assert "Consensus median 4" in res.reasoning


class TestHumanCalibration:
    """Test Layer 3 human eval agreement and drift calibration."""

    def test_cohens_kappa_agreement(self):
        # Substantial agreement
        scores_1 = [5, 4, 3, 4, 5, 2, 3, 4, 5, 4]
        scores_2 = [5, 4, 4, 4, 5, 3, 3, 4, 5, 3]

        res = measure_cohens_kappa(scores_1, scores_2)
        assert res["cohens_kappa"] > 0.4
        assert res["exact_agreement"] >= 0.7
        assert res["interpretation"] in ["moderate", "substantial", "almost perfect"]

    def test_check_judge_drift(self):
        human_scores = [5.0, 4.0, 3.0, 5.0, 4.0]
        # Low drift: close scores
        calibrated_judge = [4.9, 4.1, 3.2, 4.8, 4.0]
        cal_res = check_judge_drift(human_scores, calibrated_judge, drift_threshold=0.5)
        assert cal_res["has_drifted"] is False
        assert cal_res["status"] == "CALIBRATED"

        # High drift: scores diverged
        drifted_judge = [2.0, 1.0, 1.0, 2.0, 1.0]
        drift_res = check_judge_drift(human_scores, drifted_judge, drift_threshold=0.5)
        assert drift_res["has_drifted"] is True
        assert drift_res["status"] == "RECALIBRATE_JUDGE"


class TestStatisticalSignificanceAndRegression:
    """Test paired t-test and regression testing pipeline."""

    def test_is_improvement_significant_real(self):
        before = [3.0, 4.0, 3.0, 4.0, 3.0, 3.0, 4.0, 3.0, 3.0, 4.0]
        after = [5.0, 5.0, 4.0, 5.0, 5.0, 4.0, 5.0, 5.0, 4.0, 5.0]

        res = is_improvement_significant(before, after, alpha=0.05)
        assert res["is_significant"] is True
        assert res["p_value"] < 0.05
        assert res["direction"] == "improvement"
        assert "safe to deploy" in res["recommendation"].lower()

    def test_is_improvement_significant_noise(self):
        before = [4.0, 4.0, 4.0, 4.0, 4.0]
        after = [4.1, 3.9, 4.0, 4.1, 3.9]

        res = is_improvement_significant(before, after, alpha=0.05)
        assert res["is_significant"] is False
        assert res["p_value"] > 0.05
        assert "Not statistically significant" in res["recommendation"]

    def test_regression_pipeline_compare_runs(self):
        pipeline = RegressionPipeline()

        baseline = EvalRun(
            run_id="run_1",
            timestamp="2026-09-14T00:00:00Z",
            model="test_model",
            prompt_version="v1",
            total_examples=10,
            avg_scores={"relevance": 4.5, "accuracy": 4.2},
            pass_rate=0.9,
            failures=[],
        )

        regressed = EvalRun(
            run_id="run_2",
            timestamp="2026-09-14T01:00:00Z",
            model="test_model",
            prompt_version="v2",
            total_examples=10,
            avg_scores={"relevance": 4.1, "accuracy": 3.8},  # accuracy dropped by 0.4
            pass_rate=0.7,
            failures=[{"id": "ex1"}],
        )

        comparison = pipeline.compare_runs(baseline, regressed)
        assert comparison["verdict"] == "REGRESSION"
        assert "accuracy" in comparison["regressions"]
        assert comparison["pass_rate_delta"] == -0.2


class TestSelfEvaluatingOrchestrator:
    """Test unified orchestrator execution."""

    @patch("httpx.Client")
    def test_evaluate_output_deterministic_failure(self, mock_client_cls):
        orchestrator = SelfEvaluatingOrchestrator()
        # Invalid JSON
        result = orchestrator.evaluate_output(
            question="Generate JSON",
            response="Not JSON at all",
            config={"expect_json": True},
        )
        assert result["status"] == "FAIL"
        assert result["layer"] == "deterministic"
        assert len(result["details"]) > 0

    @patch("httpx.Client")
    def test_evaluate_output_llm_judge_pass(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": json.dumps({"score": 5, "reasoning": "Excellent."})}}
            ]
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        orchestrator = SelfEvaluatingOrchestrator()
        result = orchestrator.evaluate_output(
            question="What is recursion?",
            response="Recursion is a process where a function calls itself.",
            criteria=["relevance"],
            config={"check_syntax": False},
        )
        assert result["status"] == "PASS"
        assert result["layer"] == "llm_judge"
        assert result["score"] == 5.0
