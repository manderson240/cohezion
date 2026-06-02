"""Unit tests for Swarm Optimization & Verification Engine components.

Verifies prefill-based routing, step-entropy pruning, and decoupled dual-loop cycles.
"""

from __future__ import annotations

from typing import Any

import pytest

from cohezion.compound.dual_loop_optimizer import DualLoopOptimizer
from cohezion.compound.harness_benefit import HarnessBenefitTracker
from cohezion.inference.activation_router import PrefillActivationRouter
from cohezion.inference.entropy_compressor import StepEntropyCompressor
from cohezion.inference.task_classifier import RouteDecision


# ---------------------------------------------------------------------------
# Tests for PrefillActivationRouter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrefillActivationRouter:
    """Tests for prefill-based activation routing logic."""

    def test_estimate_tokens(self) -> None:
        router = PrefillActivationRouter(char_to_token_ratio=4.0)
        assert router.estimate_tokens("a" * 40) == 10
        assert router.estimate_tokens("") == 0

    def test_npu_limit_override(self) -> None:
        # Prompt length triggers estimated tokens = 1200 (> npu_token_limit=1000)
        router = PrefillActivationRouter(
            npu_token_limit=1000,
            gpu_token_limit=4000,
            char_to_token_ratio=4.0,
        )
        prompt = "a" * 4800
        decision = router.route_decision(prompt)
        assert decision.node == "gpu"
        assert "exceeds NPU limit" in decision.reason

    def test_gpu_limit_override(self) -> None:
        # Prompt length triggers estimated tokens = 5000 (> gpu_token_limit=4000)
        router = PrefillActivationRouter(
            npu_token_limit=1000,
            gpu_token_limit=4000,
            char_to_token_ratio=4.0,
        )
        prompt = "a" * 20000
        decision = router.route_decision(prompt)
        assert decision.node == "gpu"
        assert "exceeds GPU limit" in decision.reason

    def test_respect_base_classifier(self) -> None:
        def base_classifier(p: str) -> RouteDecision:
            return RouteDecision(
                node="npu",
                output_type="short_categorical",
                quality_gate_chars=0,
                confidence=0.95,
                reason="base_class",
            )

        router = PrefillActivationRouter(
            base_classifier=base_classifier,
            npu_token_limit=1000,
            gpu_token_limit=4000,
        )
        # Estimated tokens: 400 / 4 = 100 (< npu_token_limit)
        decision = router.route_decision("a" * 400)
        assert decision.node == "npu"
        assert "Respected base classifier" in decision.reason


# ---------------------------------------------------------------------------
# Tests for StepEntropyCompressor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStepEntropyCompressor:
    """Tests for Step Entropy-based CoT reasoning pruning."""

    def setup_method(self) -> None:
        self.compressor = StepEntropyCompressor(entropy_threshold=2.0)

    def test_calculate_word_entropy(self) -> None:
        # High entropy: all words unique
        high_ent = self.compressor.calculate_word_entropy("the quantum fluctuation of lenr fields")
        # Low entropy: repetitive words
        low_ent = self.compressor.calculate_word_entropy("test test test test test")
        assert high_ent > low_ent
        assert self.compressor.calculate_word_entropy("") == 0.0

    def test_compress_thought_pruning(self) -> None:
        thought_text = (
            "<thought>\n"
            "Analyzing rule checklist to verify all parameters match the baseline metrics.\n"
            "Checking step A. Checking step A. Checking step A.\n"
            "Wait, I found an error in rule formulation.\n"
            "</thought>"
        )
        compressed = self.compressor.compress_thought(thought_text)

        # "Checking step A..." is highly repetitive and should be pruned (unless anchor)
        assert "Checking step A. Checking step A." not in compressed
        # Structural tags are preserved
        assert "<thought>" in compressed
        assert "</thought>" in compressed
        # High-entropy / anchor lines are preserved
        assert "Analyzing rule checklist" in compressed
        assert "Wait, I found an error in rule formulation" in compressed


# ---------------------------------------------------------------------------
# Tests for DualLoopOptimizer
# ---------------------------------------------------------------------------


class DummySynthesizer:
    async def synthesize_verifier(self, env_desc: str, dummy_env: Any) -> str:
        return "def verify_action(state, action):\n    return action > 5\n"


@pytest.mark.unit
class TestDualLoopOptimizer:
    """Tests for decoupled dual-loop optimization sequences."""

    def setup_method(self) -> None:
        self.synth = DummySynthesizer()
        self.tracker = HarnessBenefitTracker()
        self.optimizer = DualLoopOptimizer(
            harness_synthesizer=self.synth, benefit_tracker=self.tracker
        )

    @pytest.mark.asyncio
    async def test_evaluate_adherence_delta(self) -> None:
        def policy_fn(state: int) -> int:
            return state + 1  # raw policy returns state + 1

        def harness_fn(state: int, action: int) -> bool:
            return action > 5

        # Dataset of states and expected actions/targets
        dataset = [
            {
                "state": 3,
                "target": 4,
                "fallback_action": 10,
            },  # raw action=4, harnessed action=10 (valid)
            {"state": 6, "target": 7, "fallback_action": 7},  # raw action=7 (valid)
        ]

        def metric_fn(action: int, target: int) -> float:
            return 1.0 if action == target else 0.0

        # Raw score (without harness)
        raw_score = await self.optimizer.evaluate_adherence_delta(
            policy_fn=policy_fn, harness_fn=None, dataset=dataset, metric_fn=metric_fn
        )
        # Harnessed score
        harnessed_score = await self.optimizer.evaluate_adherence_delta(
            policy_fn=policy_fn, harness_fn=harness_fn, dataset=dataset, metric_fn=metric_fn
        )

        assert raw_score == 1.0  # both targets matched exactly (4 and 7)
        assert harnessed_score == 0.5  # state 3 action=10 != target 4

    @pytest.mark.asyncio
    async def test_optimize_cycle(self) -> None:
        dataset = [
            {"state": 6, "target": 7},
        ]

        def policy_fn(state: int) -> int:
            return state + 1

        def metric_fn(action: int, target: int) -> float:
            return 1.0 if action == target else 0.0

        def dummy_env(code: str) -> tuple[bool, str]:
            return True, "pass"

        res = await self.optimizer.optimize_cycle(
            skill_name="test-prime",
            environment_desc="State must be positive",
            policy_fn=policy_fn,
            raw_score=1.0,
            dataset=dataset,
            metric_fn=metric_fn,
            dummy_env=dummy_env,
        )

        assert res["success"] is True
        assert "verify_action" in res["verifier_code"]
        assert res["adherence_delta"] == 0.0  # harnessed matches raw

        record = self.tracker.get_record("test-prime")
        assert record is not None
        assert record.pre_refinement_score == 1.0
        assert record.post_refinement_score == 1.0
        assert record.was_invoked is True
