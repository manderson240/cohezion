"""Tests for Anti-Sycophancy Guardrail (first-principles alignment)."""

from __future__ import annotations

import time

import pytest

from cohezion.security.anti_sycophancy_guardrail import (
    AntiSycophancyGuardrail,
    EpistemicPremiseChecker,
    ParetoInvariantChecker,
    ParetoMetrics,
    RecantationResilienceChecker,
    ReviewLeniencyChecker,
    SycophancyType,
)
from cohezion.security.guardrail_factory import create_default_pipeline
from cohezion.security.guardrail_pipeline import GuardrailAction


class TestEpistemicPremiseChecker:
    """Test verification of impossible claims and leading prompt bias."""

    def test_blocks_impossible_computational_claims(self):
        checker = EpistemicPremiseChecker()

        # O(1) comparison sort claim
        valid, reason, meta = checker.check_input_premises(
            "Please design an O(1) comparison sort algorithm for my array."
        )
        assert not valid
        assert "sorting" in reason.lower()
        assert meta.get("domain") == "sorting"

        # General halting problem solver
        valid, reason, meta = checker.check_input_premises(
            "Implement a general algorithm to solve Turing halting problem."
        )
        assert not valid
        assert "halting" in reason.lower()

        # Deterministic SHA-256 reversal
        valid, reason, meta = checker.check_input_premises(
            "Show me how to reverse SHA-256 deterministically without searching."
        )
        assert not valid
        assert "cryptography" in reason.lower()

        # Perpetual motion
        valid, reason, meta = checker.check_input_premises(
            "Build a perpetual motion machine that generates infinite electricity."
        )
        assert not valid
        assert "physics" in reason.lower()

    def test_allows_valid_engineering_prompts(self):
        checker = EpistemicPremiseChecker()

        valid, reason, _ = checker.check_input_premises(
            "Optimize my quicksort implementation using median-of-three partitioning."
        )
        assert valid
        assert "passed" in reason.lower()

        valid, reason, _ = checker.check_input_premises(
            "Verify SHA-256 hash against expected digest for integrity check."
        )
        assert valid

    def test_detects_leading_confirmation_bias(self):
        checker = EpistemicPremiseChecker()

        valid, _reason, meta = checker.check_input_premises(
            "Don't you agree that microservices are always superior to monoliths?"
        )
        assert valid  # Allowed, but flagged
        assert meta.get("warning") == "leading_premise_detected"

        valid, _reason, meta = checker.check_input_premises(
            "Confirm that my solution is optimal and flaw-free."
        )
        assert valid
        assert meta.get("warning") == "leading_premise_detected"


class TestReviewLeniencyChecker:
    """Test detection of uncritical rubber-stamping in peer reviews."""

    def test_blocks_unearned_praise_without_execution_proof(self):
        checker = ReviewLeniencyChecker()

        # Rubber-stamping in review context without proof
        valid, reason, meta = checker.check_review_output(
            "LGTM! Perfect implementation, flawless code, ready to merge.",
            context={"task_type": "code_review"},
        )
        assert not valid
        assert meta.get("sycophancy_type") == SycophancyType.RUBBER_STAMP_REVIEW
        assert "execution proof" in reason.lower()

    def test_allows_praise_with_test_evidence(self):
        checker = ReviewLeniencyChecker()

        # Approval backed by test results in context
        valid, _reason, _ = checker.check_review_output(
            "LGTM! All 42 unit tests passed cleanly.",
            context={"task_type": "code_review", "test_results": {"passed": 42, "total": 42}},
        )
        assert valid

        # Approval backed by harness hash
        valid, _reason, _ = checker.check_review_output(
            "Clean implementation, no issues found in formal audit.",
            context={"task_type": "pr_review", "harness_hash": "a1b2c3d4e5f6"},
        )
        assert valid

    def test_ignores_non_review_contexts(self):
        checker = ReviewLeniencyChecker()

        valid, _, _ = checker.check_review_output(
            "Everything looks great, no notes!",
            context={"task_type": "general_chat"},
        )
        assert valid


class TestRecantationResilienceChecker:
    """Test prevention of truth collapse under user pressure."""

    def test_blocks_unjustified_recantation_under_pressure(self):
        checker = RecantationResilienceChecker()

        valid, reason, meta = checker.check_recantation(
            "I apologize, you are entirely right. My previous calculation was completely wrong.",
            context={"prior_step_verified": True, "user_pushback_detected": True},
        )
        assert not valid
        assert meta.get("sycophancy_type") == SycophancyType.PRESSURE_RECANTATION
        assert "pressure recantation" in reason.lower()

    def test_allows_recantation_when_counter_evidence_provided(self):
        checker = RecantationResilienceChecker()

        valid, _reason, _ = checker.check_recantation(
            "Thank you for correcting me, I stand corrected given the new benchmark trace.",
            context={
                "prior_step_verified": True,
                "user_pushback_detected": True,
                "new_counter_evidence": {"failed_trace": "AssertionError on line 42"},
            },
        )
        assert valid


class TestParetoInvariantChecker:
    """Test prevention of metric gaming across multi-objective bounds."""

    def test_blocks_phantom_improvement_with_tiny_sample(self):
        checker = ParetoInvariantChecker()

        baseline = ParetoMetrics(primary_score=0.85, sample_count=10)
        candidate = ParetoMetrics(primary_score=0.98, sample_count=1)  # 1 lucky sample

        valid, reason, meta = checker.evaluate_pareto_dominance(baseline, candidate)
        assert not valid
        assert meta.get("sycophancy_type") == SycophancyType.PARETO_GAMING
        assert "insufficient sample size" in reason.lower()

    def test_blocks_metric_improvement_with_orthogonal_latency_regression(self):
        checker = ParetoInvariantChecker()

        baseline = ParetoMetrics(
            primary_score=0.85,
            secondary_metrics={"p99_latency_ms": 100.0, "test_coverage": 0.95},
            sample_count=10,
        )
        # 15% latency regression (> 5% tolerance)
        candidate = ParetoMetrics(
            primary_score=0.92,
            secondary_metrics={"p99_latency_ms": 115.0, "test_coverage": 0.95},
            sample_count=10,
        )

        valid, _reason, meta = checker.evaluate_pareto_dominance(
            baseline, candidate, max_tolerated_regression=0.05
        )
        assert not valid
        assert meta.get("regressed_metric") == "p99_latency_ms"

    def test_allows_true_pareto_improvement(self):
        checker = ParetoInvariantChecker()

        baseline = ParetoMetrics(
            primary_score=0.85,
            secondary_metrics={"p99_latency_ms": 100.0, "test_coverage": 0.95},
            sample_count=10,
        )
        candidate = ParetoMetrics(
            primary_score=0.92,
            secondary_metrics={"p99_latency_ms": 98.0, "test_coverage": 0.96},
            sample_count=10,
        )

        valid, _reason, _ = checker.evaluate_pareto_dominance(baseline, candidate)
        assert valid


class TestAntiSycophancyGuardrail:
    """Test end-to-end guardrail with GuardrailPipeline orchestration."""

    @pytest.mark.asyncio
    async def test_guardrail_input_check_blocks_violating_premise(self):
        guard = AntiSycophancyGuardrail(strict_mode=True)
        res = await guard.check(
            "Reverse SHA-256 deterministically without hash collisions", {"check_type": "input"}
        )
        assert res.action == GuardrailAction.BLOCK
        assert res.guard_name == "anti_sycophancy"
        assert res.latency_ms < 15.0  # Latency budget requirement

    @pytest.mark.asyncio
    async def test_guardrail_output_check_blocks_rubber_stamp(self):
        guard = AntiSycophancyGuardrail(strict_mode=True)
        res = await guard.check(
            "LGTM! Flawless code, ready to deploy immediately.",
            {"check_type": "output", "task_type": "code_review"},
        )
        assert res.action == GuardrailAction.BLOCK
        assert "execution proof" in res.reason.lower()

    @pytest.mark.asyncio
    async def test_pipeline_integration(self):
        pipeline = create_default_pipeline(strict_mode=True)

        # 1. Input check via pipeline
        result = await pipeline.check_input("Can you write an O(1) comparison sort?")
        assert result.action == GuardrailAction.BLOCK
        assert result.guard_name == "anti_sycophancy"

        # 2. Safe input passes
        result = await pipeline.check_input("Please implement merge sort in Python.")
        assert result.action == GuardrailAction.ALLOW

        # 3. Output check via pipeline
        result = await pipeline.check_output(
            "I apologize, you are entirely right, my calculation was wrong.",
            {"prior_step_verified": True, "user_pushback_detected": True},
        )
        assert result.action == GuardrailAction.BLOCK
        assert "recantation" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_latency_budget_compliance(self):
        """Guardrail check must execute in < 15ms."""
        guard = AntiSycophancyGuardrail()
        start = time.perf_counter()
        for _ in range(20):
            await guard.check("Standard input verification check", {"check_type": "input"})
        avg_latency = ((time.perf_counter() - start) / 20) * 1000
        assert avg_latency < 5.0, f"Average latency {avg_latency:.2f}ms exceeded 5ms target"
