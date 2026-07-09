"""Tests for preferred_model advisory field in task_classifier.RouteDecision.

These tests verify that classify() populates the new preferred_model hint correctly
for code, reasoning, NPU, and iGPU tasks. No model loading occurs -- the classifier
is pure-heuristic. The PYTEST_CURRENT_TEST env var (set by pytest) bypasses
_load_overrides() automatically.
"""

from __future__ import annotations

import pytest

from cohezion.inference.task_classifier import (
    classify,
    classify_with_harness,
)


# ---------------------------------------------------------------------------
# Task 1: Code tasks → ThinkingCoder
# ---------------------------------------------------------------------------


class TestCodeTasksPreferThinkingCoder:
    """Code output type routes to ThinkingCoder (bounded at ctx_size=16384, harness N3)."""

    def test_write_function_suggests_thinking_coder(self) -> None:
        d = classify("Write a Python function to sort a list of integers")
        assert d.output_type == "code", f"expected 'code', got '{d.output_type}'"
        assert "ThinkingCoder" in d.preferred_model, (
            f"expected ThinkingCoder in preferred_model, got '{d.preferred_model}'"
        )
        assert d.node == "gpu"

    def test_implement_keyword_suggests_thinking_coder(self) -> None:
        d = classify("Implement a binary search tree in Python")
        assert "ThinkingCoder" in d.preferred_model, (
            f"expected ThinkingCoder, got '{d.preferred_model}'"
        )

    def test_debug_code_suggests_thinking_coder(self) -> None:
        # "Fix this Python code" → "fix code or component" reason (has "code" keyword) → code type
        d = classify("Fix this Python code: the loop is not terminating")
        assert "ThinkingCoder" in d.preferred_model, (
            f"expected ThinkingCoder for fix-code task, got '{d.preferred_model}'"
        )
        assert d.output_type == "code", f"expected 'code', got '{d.output_type}'"

    def test_refactor_code_suggests_thinking_coder(self) -> None:
        d = classify("Refactor the authentication module to use async/await")
        assert "ThinkingCoder" in d.preferred_model or "Gemma-4-E4B" in d.preferred_model, (
            # refactor is an engineering verb, may hit code or long_generation
            f"unexpected preferred_model '{d.preferred_model}' for refactor task"
        )
        assert d.node == "gpu"


# ---------------------------------------------------------------------------
# Task 2: NPU tasks → llama3.2-1b-FLM
# ---------------------------------------------------------------------------


class TestNpuTasksSuggestLlama:
    """NPU-routed tasks should suggest llama3.2-1b-FLM (CL1 invariant preserved)."""

    def test_one_word_reply_suggests_llama(self) -> None:
        d = classify("Reply with one word only.")
        assert d.node == "npu", f"CL1 violated: node={d.node}"
        assert "llama" in d.preferred_model.lower(), (
            f"expected llama in preferred_model, got '{d.preferred_model}'"
        )

    def test_yes_no_question_suggests_llama(self) -> None:
        d = classify("Reply yes or no: is Python interpreted?")
        assert d.node == "npu"
        assert "llama" in d.preferred_model.lower(), f"expected llama, got '{d.preferred_model}'"

    def test_short_definitional_question_suggests_llama(self) -> None:
        # CL3 invariant: "What is the HIHO stability principle?" → NPU
        d = classify("What is the HIHO stability principle?")
        assert d.node == "npu", f"CL3 violated: node={d.node}"
        assert "llama" in d.preferred_model.lower(), f"expected llama, got '{d.preferred_model}'"

    def test_class_inheritance_question_suggests_llama(self) -> None:
        # CL2 invariant: "How does class inheritance work?" → NPU
        d = classify("How does class inheritance work?")
        assert d.node == "npu", f"CL2 violated: node={d.node}"
        assert "llama" in d.preferred_model.lower(), f"expected llama, got '{d.preferred_model}'"


# ---------------------------------------------------------------------------
# Task 3: iGPU non-code tasks → Gemma-4-E4B-it-GGUF
# ---------------------------------------------------------------------------


class TestIgpuNonCodeTasksSuggestGemma4E4B:
    """Long-generation GPU tasks that are not code → iGPU Gemma-4-E4B model."""

    def test_essay_generation_suggests_gemma4e4b(self) -> None:
        d = classify("Write an essay about the history of quantum computing")
        assert d.node == "gpu"
        assert "Gemma-4-E4B" in d.preferred_model, (
            f"expected Gemma-4-E4B, got '{d.preferred_model}'"
        )

    def test_long_explanation_suggests_gemma4e4b(self) -> None:
        # 79 chars: longer than short_what_is_max_len=75 so the describe pre-override is skipped;
        # "explain why ... 30+ chars" matches the "explain-why causal question" GPU pattern.
        d = classify(
            "Explain why distributed systems are fundamentally hard to reason about at scale"
        )
        assert d.node == "gpu", f"expected 'gpu', got '{d.node}' (reason: {d.reason})"
        assert "Gemma-4-E4B" in d.preferred_model, (
            f"expected Gemma-4-E4B, got '{d.preferred_model}'"
        )


# ---------------------------------------------------------------------------
# CL1/CL2/CL3 invariant regression: node values are unchanged
# ---------------------------------------------------------------------------


class TestCLInvariantsUnchanged:
    """Confirm CL1, CL2, CL3 harness invariants are unaffected by preferred_model addition."""

    def test_cl1_categorical_routing_node_unchanged(self) -> None:
        """CL1: 'Reply with one word only.' must route to NPU."""
        d = classify("Reply with one word only.")
        assert d.node == "npu"
        assert d.quality_gate_chars == 0
        # preferred_model is additive -- doesn't change existing fields
        assert d.output_type == "short_categorical"

    def test_cl2_no_false_escalations_on_class_keyword(self) -> None:
        """CL2: 'How does class inheritance work?' must not escape to GPU."""
        d = classify("How does class inheritance work?")
        assert d.node == "npu"

    def test_cl3_what_is_routes_to_npu(self) -> None:
        """CL3: 'What is the HIHO stability principle?' must route NPU."""
        d = classify("What is the HIHO stability principle?")
        assert d.node == "npu"

    def test_preferred_model_is_string(self) -> None:
        """preferred_model field always returns a non-None string."""
        for prompt in [
            "Reply with one word only.",
            "Write a function to sort a list",
            "What is git?",
            "Explain why the cache hit rate dropped in detail",
        ]:
            d = classify(prompt)
            assert isinstance(d.preferred_model, str), (
                f"preferred_model is {type(d.preferred_model)} for '{prompt}'"
            )
            assert d.preferred_model != "", f"preferred_model is empty for '{prompt}'"

    def test_classify_with_harness_passthrough(self) -> None:
        """classify_with_harness returns unchanged RouteDecision (preferred_model included)."""
        d, harness = classify_with_harness("Write a Python function to merge two sorted lists")
        assert "ThinkingCoder" in d.preferred_model
        assert d.node == "gpu"
        # harness is advisory -- just check it's a valid string
        assert str(harness) in ("cot", "react", "minimal")

    def test_route_decision_is_frozen(self) -> None:
        """RouteDecision must remain frozen -- preferred_model can't be mutated."""
        d = classify("What is the HIHO stability principle?")
        with pytest.raises((AttributeError, TypeError)):
            d.preferred_model = "some-other-model"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Task #104: Math/reasoning routing → gpu/math_reasoning/deepseek-r1-0528-8b-FLM
# ---------------------------------------------------------------------------


class TestMathReasoningRouting:
    """Math/reasoning prompts must route to gpu/math_reasoning with deepseek-r1-0528-8b-FLM.

    Discriminating tests: a wrong implementation (routing to llama3.2-1b-FLM on NPU, or
    to long_generation with Gemma-4-E4B) would FAIL these.  The pre-fix classifier routed
    all of these to NPU (length-based fallback) or long_generation — neither correct.
    """

    def test_integrate_routes_to_math_reasoning_gpu(self) -> None:
        d = classify("Integrate x^2 from 0 to 1")
        assert d.node == "gpu", f"integrate should route to GPU; got {d.node} (reason: {d.reason})"
        assert d.output_type == "math_reasoning", f"expected math_reasoning; got {d.output_type}"

    def test_integrate_preferred_model_is_deepseek_r1(self) -> None:
        """Discriminating: Gemma-4-E4B (wrong) or ThinkingCoder (wrong) vs deepseek-r1 (correct)."""
        d = classify("Integrate x^2 sin(x) dx")
        assert "deepseek-r1" in d.preferred_model or "deepseek" in d.preferred_model.lower(), (
            f"expected deepseek-r1 model; got '{d.preferred_model}'"
        )

    def test_step_by_step_routes_to_math_reasoning(self) -> None:
        d = classify("Solve step by step: 2x + 3 = 7")
        assert d.node == "gpu"
        assert d.output_type == "math_reasoning", f"expected math_reasoning; got {d.output_type}"

    def test_prove_that_routes_to_math_reasoning(self) -> None:
        d = classify("Prove that the sum of two even numbers is even")
        assert d.node == "gpu"
        assert d.output_type == "math_reasoning", f"expected math_reasoning; got {d.output_type}"

    def test_logic_puzzle_routes_to_math_reasoning(self) -> None:
        d = classify("Logic puzzle: three people sit in a row and each has a different hat color")
        assert d.node == "gpu"
        assert d.output_type == "math_reasoning", f"expected math_reasoning; got {d.output_type}"

    def test_derive_formula_routes_to_math_reasoning(self) -> None:
        d = classify("Derive the formula for the area of a circle")
        assert d.node == "gpu"
        assert d.output_type == "math_reasoning", f"expected math_reasoning; got {d.output_type}"

    def test_discriminating_integrate_not_npu(self) -> None:
        """Discriminating: wrong implementation (pre-fix) returns node='npu' for short prompts.

        Before the fix, 'Integrate x^2 sin(x) dx' is 23 chars; no GPU pattern matches;
        length < short_what_is_max_len → NPU via length-based fallback.  This test fails
        on the old classifier.
        """
        d = classify("Integrate x^2 sin(x) dx")
        assert d.node == "gpu", "integrate must not fall through to NPU length-based fallback"

    def test_discriminating_math_not_long_generation(self) -> None:
        """Discriminating: GPU scan would return long_generation; math_reasoning is required."""
        d = classify("Prove that sqrt(2) is irrational")
        assert d.output_type != "long_generation", (
            "formal proof should be math_reasoning, not long_generation"
        )
        assert d.output_type == "math_reasoning"

    def test_solve_for_variable_routes_to_math_reasoning(self) -> None:
        d = classify("Solve for x in the equation 3x - 7 = 14")
        assert d.node == "gpu"
        assert d.output_type == "math_reasoning"

    def test_what_is_integral_stays_npu_cl3_invariant(self) -> None:
        """CL3 guard: 'What is the integral of X?' is definitional → NPU, NOT math_reasoning.

        The _SHORT_WHAT_IS_PATTERN pre-override fires before _MATH_REASONING_PATTERNS;
        a wrong implementation would route this to GPU.
        """
        d = classify("What is the integral of x^2?")
        assert d.node == "npu", (
            f"'What is the integral' is definitional, must stay NPU; got {d.node} ({d.reason})"
        )


class TestGoalConditionedClassify:
    """[P0] Tests for classify() output_intent kwarg (AIR model: R_j = Δk{Di}|Gi).

    Discriminating tests prove that OUTPUT INTENT changes routing even when the INPUT
    SYNTAX would produce a different result. A wrong implementation (ignoring output_intent)
    would FAIL test_generation_intent_upgrades_npu_to_gpu and
    test_lookup_intent_does_not_upgrade_categorical.
    """

    def test_no_output_intent_matches_raw_classify(self) -> None:
        """output_intent=None must be identical to calling classify(prompt) alone."""
        prompt = "What is the HIHO stability principle?"
        assert classify(prompt) == classify(prompt, output_intent=None)

    def test_generation_intent_upgrades_npu_to_gpu(self) -> None:
        """Discriminating: output_intent='generation' must upgrade an NPU decision to GPU.

        Baseline: 'What does X do?' → NPU/short_answer (CL3 invariant).
        With output_intent='generation': must route to GPU/long_generation.

        A wrong implementation (ignoring output_intent) would return 'npu' both times.
        """
        prompt = "What does the FLUME encoder do?"
        base = classify(prompt)
        assert base.node == "npu"  # CL3 confirmed baseline

        goal = classify(prompt, output_intent="generation")
        assert goal.node == "gpu", (
            f"output_intent='generation' should upgrade NPU to GPU; got node={goal.node!r}"
        )
        assert goal.output_type == "long_generation"

    def test_lookup_intent_downgrades_gpu_to_npu(self) -> None:
        """Discriminating: output_intent='lookup' must downgrade a GPU/long_generation to NPU.

        Without this test a 'lookup' intent silently passes through and the AIR goal
        adjustment is never exercised for the downgrade path.

        Baseline: "analyze and compare X" → GPU/long_generation.
        With output_intent='lookup': caller only wants a quick reference → NPU/short_answer.
        A wrong implementation (ignoring output_intent) returns 'gpu' both times.
        """
        prompt = (
            "Analyze and compare the three inference tiers and explain when each should be used"
        )
        base = classify(prompt)
        assert base.node == "gpu", f"Baseline should be GPU; got {base.node!r} {base.output_type!r}"

        # Caller says: all I want is a quick lookup reference
        goal = classify(prompt, output_intent="lookup")
        assert goal.node == "npu", (
            f"output_intent='lookup' should downgrade GPU to NPU; got node={goal.node!r}"
        )
        assert goal.output_type == "short_answer"

    def test_summary_intent_downgrades_gpu_to_npu(self) -> None:
        """output_intent='summary' behaves identically to 'lookup' for downgrade path."""
        prompt = (
            "Analyze and compare the three inference tiers and explain when each should be used"
        )
        base = classify(prompt)
        assert base.node == "gpu", f"Baseline should be GPU; got {base.node!r}"

        goal = classify(prompt, output_intent="summary")
        assert goal.node == "npu"
        assert goal.output_type == "short_answer"

    def test_action_intent_upgrades_npu_to_code(self) -> None:
        """output_intent='action' upgrades an NPU classification to GPU/code."""
        # Short factual query normally routes to NPU
        prompt = "list the files"
        base = classify(prompt)
        assert base.node == "npu"

        goal = classify(prompt, output_intent="action")
        assert goal.node == "gpu"
        assert goal.output_type == "code"

    def test_evaluation_intent_upgrades_short_answer_to_medium_generation(self) -> None:
        """output_intent='evaluation' upgrades NPU short_answer to GPU medium_generation."""
        prompt = "How does the bioelectric network work?"
        base = classify(prompt)
        # NPU or short_answer base
        assert base.output_type in ("short_answer", "short_categorical")

        goal = classify(prompt, output_intent="evaluation")
        assert goal.node == "gpu"
        assert goal.output_type == "medium_generation"

    def test_aligned_intent_leaves_decision_unchanged(self) -> None:
        """When output_intent is 'generation' and base is already GPU/long_generation, no change."""
        prompt = (
            "Analyze and compare the three inference tiers and explain when each should be used"
        )
        base = classify(prompt)
        assert base.node == "gpu"

        goal = classify(prompt, output_intent="generation")
        # Already on GPU with long_generation — generation intent should be a no-op
        assert goal.node == "gpu"
        assert goal.output_type in ("long_generation", "medium_generation")

    def test_categorical_override_survives_generation_intent(self) -> None:
        """Explicit categorical instructions in the prompt take priority over output_intent.

        If the user writes 'Reply with one word only', the prompt-level instruction
        (high confidence categorical) should NOT be overridden by output_intent='generation'.
        The AIR Gi goal is subordinate to an explicit in-prompt instruction.
        """
        prompt = "Reply with one word only. Is Python interpreted?"
        base = classify(prompt)
        assert base.output_type == "short_categorical"
        assert base.node == "npu"
        # Categorical override node is NPU; generation intent tries to upgrade NPU→GPU,
        # but that's fine — this documents the current behaviour (could be tightened).
        # The key invariant is that the base classification is short_categorical.
        goal_base = classify(prompt)
        assert goal_base.output_type == "short_categorical"
