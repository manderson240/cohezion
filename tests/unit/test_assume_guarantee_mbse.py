"""Unit tests for Assume-Guarantee Model-Based Systems Engineering (MBSE).
========================================================================
Tests contract evaluation, refinement checking, composition, and counterexample generation.
"""

import pytest
from cohezion.compound.assume_guarantee_mbse import (
    AssumeGuaranteeContract,
    ContractCompositionEngine,
    ContractPredicate,
)


class TestAssumeGuaranteeMBSE:
    def test_contract_predicate_evaluation(self):
        pred = ContractPredicate(
            name="memory_below_32gb",
            description="RAM usage must not exceed 32GB",
            predicate=lambda s: s.get("memory_gb", 0) <= 32,
        )
        assert pred.evaluate({"memory_gb": 16}) is True
        assert pred.evaluate({"memory_gb": 40}) is False
        assert pred.evaluate({}) is True

    def test_contract_step_evaluation_guarantee_upheld(self):
        c = AssumeGuaranteeContract(
            name="npu_inference_contract",
            assumptions=[
                ContractPredicate("valid_prompt", "Prompt is non-empty", lambda s: len(s.get("prompt", "")) > 0)
            ],
            guarantees=[
                ContractPredicate("bounded_latency", "Latency < 200ms", lambda s: s.get("latency_ms", 999) < 200),
                ContractPredicate("zero_uma_leak", "Zero UMA allocation", lambda s: s.get("uma_allocated_mb", 0) == 0),
            ],
        )

        pre = {"prompt": "Solve ARC puzzle"}
        post = {"latency_ms": 45, "uma_allocated_mb": 0}
        satisfied, msg = c.evaluate_step(pre, post)
        assert satisfied is True
        assert "Contract satisfied" in msg

    def test_contract_step_evaluation_guarantee_violated(self):
        c = AssumeGuaranteeContract(
            name="npu_inference_contract",
            assumptions=[
                ContractPredicate("valid_prompt", "Prompt is non-empty", lambda s: len(s.get("prompt", "")) > 0)
            ],
            guarantees=[
                ContractPredicate("zero_uma_leak", "Zero UMA allocation", lambda s: s.get("uma_allocated_mb", 0) == 0),
            ],
        )

        pre = {"prompt": "Solve ARC puzzle"}
        post = {"uma_allocated_mb": 1024}  # Leaked into UMA!
        satisfied, msg = c.evaluate_step(pre, post)
        assert satisfied is False
        assert "Contract violation" in msg
        assert "zero_uma_leak" in msg

    def test_contract_vacuous_satisfaction_on_broken_assumption(self):
        c = AssumeGuaranteeContract(
            name="npu_inference_contract",
            assumptions=[
                ContractPredicate("valid_prompt", "Prompt is non-empty", lambda s: len(s.get("prompt", "")) > 0)
            ],
            guarantees=[
                ContractPredicate("zero_uma_leak", "Zero UMA allocation", lambda s: s.get("uma_allocated_mb", 0) == 0),
            ],
        )

        pre = {"prompt": ""}  # Assumption violated
        post = {"uma_allocated_mb": 9999}
        satisfied, msg = c.evaluate_step(pre, post)
        assert satisfied is True
        assert "Vacuously satisfied" in msg

    def test_contract_refinement(self):
        spec = AssumeGuaranteeContract(
            name="abstract_router_spec",
            guarantees=[
                ContractPredicate("valid_status", "Status is success", lambda s: s.get("status") == "success"),
            ],
        )

        impl = AssumeGuaranteeContract(
            name="concrete_router_impl",
            guarantees=[
                ContractPredicate("valid_status", "Status is success", lambda s: s.get("status") == "success"),
                ContractPredicate("fast_latency", "Latency < 50ms", lambda s: s.get("latency_ms", 999) < 50),
            ],
        )

        refines, err = impl.refines(spec)
        assert refines is True
        assert err is None

        # Reversed should fail (spec does not guarantee fast_latency)
        refines_rev, err_rev = spec.refines(impl)
        assert refines_rev is False
        assert "fast_latency" in err_rev

    def test_contract_composition_and_compatibility(self):
        c1 = AssumeGuaranteeContract(
            name="extractor_agent",
            guarantees=[
                ContractPredicate("has_embeddings", "Provides 2048D embeddings", lambda s: "embedding" in s),
            ],
        )

        c2 = AssumeGuaranteeContract(
            name="poincare_goal_agent",
            assumptions=[
                ContractPredicate("has_embeddings", "Requires 2048D embeddings", lambda s: "embedding" in s),
            ],
            guarantees=[
                ContractPredicate("has_lyapunov", "Computes Lyapunov distance", lambda s: "lyapunov_potential" in s),
            ],
        )

        state_valid = {"embedding": [0.1] * 2048}
        compatible, issues = ContractCompositionEngine.check_compatibility(c1, c2, state_valid)
        assert compatible is True
        assert len(issues) == 0

        composite = ContractCompositionEngine.compose(c1, c2, "extractor_poincare_pipeline")
        assert len(composite.guarantees) == 2
        assert "extractor_agent" in composite.metadata["composition"]
