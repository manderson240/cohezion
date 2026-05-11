"""Unit tests for task_classifier — routing accuracy and gate correctness."""

from __future__ import annotations

import pytest

from cohezion.inference.task_classifier import classify


# ── GPU routing (highest-cost to mis-route) ──────────────────────────────────


class TestGpuPatterns:
    def test_code_generation_write_function(self):
        d = classify("Write a Python function that sorts a list by key.")
        assert d.node == "gpu"
        assert d.output_type == "code"
        assert d.quality_gate_chars == 0

    def test_code_generation_implement_class(self):
        d = classify("Implement a class for managing database connections.")
        assert d.node == "gpu"
        assert d.output_type == "code"

    def test_code_context_backtick(self):
        d = classify("Fix the bug in this code:\n```python\ndef foo(): pass\n```")
        assert d.node == "gpu"

    def test_code_context_def_keyword(self):
        d = classify("What does def __init__(self) do in Python?")
        assert d.node == "gpu"

    def test_essay_generation(self):
        d = classify("Write an essay explaining the HIHO stability principle in detail.")
        assert d.node == "gpu"
        assert d.output_type == "long_generation"

    def test_detailed_explanation(self):
        d = classify("Explain step-by-step how transformers handle attention.")
        assert d.node == "gpu"

    def test_math_multi_step(self):
        d = classify("Prove that sqrt(2) is irrational, showing each step.")
        assert d.node == "gpu"

    def test_design_task(self):
        d = classify("Design a caching architecture for a distributed system.")
        assert d.node == "gpu"

    def test_long_prompt_routes_gpu(self):
        prompt = "A" * 500
        d = classify(prompt)
        assert d.node == "gpu"


# ── NPU routing — categorical (gate must be 0 to prevent false escalation) ───


class TestCategoricalPatterns:
    def test_explicit_one_word_instruction(self):
        d = classify("Reply with one word: is this code correct?")
        assert d.node == "npu"
        assert d.output_type == "short_categorical"
        assert d.quality_gate_chars == 0, "gate=0 required: 'CORRECT'/'INCORRECT' are 1 word each"

    def test_one_word_answer(self):
        d = classify("One word answer: is Python interpreted?")
        assert d.node == "npu"
        assert d.quality_gate_chars == 0

    def test_reply_yes_no(self):
        d = classify("Reply with yes or no: is the server running?")
        assert d.node == "npu"
        assert d.quality_gate_chars == 0

    def test_true_false_only(self):
        d = classify("True or false only: Python is compiled.")
        assert d.node == "npu"
        assert d.quality_gate_chars == 0

    def test_sentiment_categories(self):
        d = classify(
            "Sentiment: 'Everything works perfectly.' Reply POSITIVE, NEGATIVE, or NEUTRAL."
        )
        assert d.node == "npu"
        assert d.quality_gate_chars == 0

    def test_multiple_choice_abcd(self):
        d = classify(
            "Best cache tier for exact matches: A) L1-hash  B) L2-cosine  C) L3-vault  D) None. "
            "Reply with one letter."
        )
        assert d.node == "npu"
        assert d.quality_gate_chars == 0

    def test_classify_task(self):
        d = classify("Classify this as spam or not spam: 'You've won a million dollars!'")
        assert d.node == "npu"
        assert d.quality_gate_chars == 0


# ── NPU routing — short answer (gate=10) ─────────────────────────────────────


class TestShortAnswerPatterns:
    def test_in_one_sentence(self):
        d = classify("In one sentence, what does the HIHO stability principle optimize for?")
        assert d.node == "npu"
        assert d.output_type == "short_answer"
        assert d.quality_gate_chars == 10

    def test_briefly_explain(self):
        d = classify("Briefly explain what FLUME encoding does.")
        assert d.node == "npu"
        assert d.output_type == "short_answer"

    def test_name_the_entity(self):
        d = classify("Name the primary orchestration layer in cohezion.")
        assert d.node == "npu"

    def test_short_prompt_default_npu(self):
        # Short prompts default to NPU
        d = classify("What is the purpose of a circuit breaker?")
        assert d.node == "npu"

    def test_medium_prompt_tries_npu(self):
        # 150-400 chars: try NPU first
        prompt = (
            "Explain the difference between NPU and GPU routing in the cohezion inference stack and when each is preferred for different task types in the tiered orchestrator. "
            * 2
        )
        prompt = prompt[:300]
        d = classify(prompt)
        assert d.node == "npu"  # medium prompt → try NPU


# ── Gate correctness invariants ───────────────────────────────────────────────


class TestGateInvariants:
    def test_categorical_gate_always_zero(self):
        """CL2: gate=0 prevents false escalation on correct 1-word answers."""
        categoricals = [
            "Reply with one word: yes or no.",
            "Answer with one letter: A, B, C, or D.",
            "True or false only: water boils at 100°C.",
            "POSITIVE, NEGATIVE, or NEUTRAL?",
        ]
        for prompt in categoricals:
            d = classify(prompt)
            assert d.quality_gate_chars == 0, (
                f"gate must be 0 for categorical '{prompt[:40]}' — "
                f"correct 1-word answers would fail gate={d.quality_gate_chars}"
            )

    def test_code_gate_always_zero(self):
        """Code tasks: no min_chars gate — let the model produce as little as needed."""
        d = classify("Write a Python script to print hello world.")
        assert d.quality_gate_chars == 0

    def test_short_answer_gate_positive(self):
        """Short-answer tasks have a positive gate to detect empty/truncated responses."""
        d = classify("In one sentence, describe the purpose of the compound loop.")
        assert d.quality_gate_chars > 0

    def test_route_decision_is_frozen(self):
        """RouteDecision must be immutable (frozen dataclass)."""
        d = classify("What is Python?")
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            d.node = "cpu"  # type: ignore[misc]


# ── Confidence bounds ─────────────────────────────────────────────────────────


class TestConfidence:
    def test_explicit_instruction_high_confidence(self):
        d = classify("Reply with exactly one word.")
        assert d.confidence >= 0.95

    def test_length_fallback_lower_confidence(self):
        d = classify("What is a compiler?")
        assert d.confidence <= 0.75

    def test_gpu_code_high_confidence(self):
        d = classify("Write a Python function to reverse a string.")
        assert d.confidence >= 0.95


# ── CL1: Harness invariant regression suite ──────────────────────────────────


@pytest.mark.parametrize(
    "prompt,expected_node,expected_type",
    [
        ("Reply with one word only.", "npu", "short_categorical"),
        ("Classify this text as spam or not.", "npu", "short_categorical"),
        ("In one sentence, summarize the main idea.", "npu", "short_answer"),
        ("Write a Python function to merge two dicts.", "gpu", "code"),
        ("Prove that P != NP showing each step.", "gpu", "long_generation"),
        ("Is this statement true or false only: 2+2=4", "npu", "short_categorical"),
        ("Name the capital of France.", "npu", "short_answer"),
        ("Write an essay on the history of computing.", "gpu", "long_generation"),
    ],
)
def test_harness_invariant_routing(prompt, expected_node, expected_type):
    d = classify(prompt)
    assert d.node == expected_node, f"Expected {expected_node} for: {prompt!r}"
    assert d.output_type == expected_type, f"Expected {expected_type} for: {prompt!r}"
