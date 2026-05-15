"""Unit tests for task_classifier — routing accuracy and gate correctness."""

from __future__ import annotations

import pytest

from cohezion.inference.task_classifier import RouteDecision, classify


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

    def test_code_context_backtick_def(self):
        # Backtick before `def` signals code context → GPU
        d = classify("When I use `def foo():` what does that create?")
        assert d.node == "gpu"

    def test_code_context_prose_def_routes_npu(self):
        # "def" in prose (no backtick/newline/tab) → conceptual question → NPU
        d = classify("What does def __init__(self) do in Python?")
        assert d.node == "npu"  # conceptual question, 1-sentence answer sufficient

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

    def test_what_is_question_routes_npu(self):
        """'What is/does X?' patterns route to NPU as short_answer."""
        d = classify("What is the HIHO stability principle?")
        assert d.node == "npu"
        assert d.output_type == "short_answer"

    def test_describe_question_routes_npu(self):
        """'Describe X?' patterns route to NPU as short_answer."""
        d = classify("Describe the triune orchestrator's hardware tiers.")
        assert d.node == "npu"
        assert d.output_type == "short_answer"

    def test_code_gen_inside_describe_still_routes_gpu(self):
        """'Describe how to write X' — code gen keyword overrides describe."""
        d = classify("Describe how to write a Python class.")
        assert d.node == "gpu"  # GPU pattern (write + class) takes precedence

    def test_short_prompt_default_npu(self):
        # Short prompts default to NPU
        d = classify("What is the purpose of a circuit breaker?")
        assert d.node == "npu"

    def test_medium_prompt_tries_npu(self):
        # 150-400 chars with no GPU signal: try NPU first via length heuristic
        # (Prompt deliberately avoids GPU-trigger verbs like "implement", "write", "explain difference")
        prompt = (
            "In the cohezion inference stack NPU and GPU routing serve different roles. "
            "The tiered orchestrator selects a node based on task complexity and output length. "
            "Shorter categorical outputs prefer the NPU tier for latency reasons. "
        )
        prompt = prompt[:300]
        d = classify(prompt)
        assert d.node == "npu"  # medium prompt with no GPU signal → NPU


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


def test_route_decision_str_format():
    """__str__ includes node, output_type, gate, and confidence."""
    d = RouteDecision(
        node="npu",
        output_type="short_categorical",
        quality_gate_chars=0,
        confidence=1.0,
        reason="test",
    )
    s = str(d)
    assert "NPU" in s
    assert "short_categorical" in s
    assert "gate=0" in s
    assert "conf=1.00" in s


# ── EXP-EXPLAIN-HOW-FIX: infinitive verb forms + 0.80→0.85 boosts ────────────


class TestExplainHowInfinitives:
    """explain-how mechanism pattern now matches infinitive verb forms (work/operate/function)."""

    def test_explain_how_jepa_work(self):
        d = classify("Explain how JEPA world models work")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_explain_how_attention_operate(self):
        d = classify("Explain how attention mechanisms operate")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_explain_how_cache_function(self):
        d = classify("Explain how semantic caches function")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_explain_how_prevents_unchanged(self):
        d = classify("Explain how the circuit breaker prevents cascading failures")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_explain_how_short_stays_npu(self):
        # Trivial "Explain how this works" — only 5 chars between 'how' and 'works' → NPU
        d = classify("Explain how this works")
        assert d.node == "npu"

    def test_explain_how_it_works_stays_npu(self):
        d = classify("Explain how it works")
        assert d.node == "npu"


@pytest.mark.parametrize(
    "prompt",
    [
        "How do we handle database migrations safely?",
        "How can we architect the multi-tier router?",
        "How do you debug a memory leak in Python?",
        "How do you troubleshoot Kafka consumer lag?",
        "How to run the compound engineering pipeline?",
        "How to start the Lemonade NPU server?",
        "Can you configure the Redis cache settings?",
        "Can you implement the retry logic for the client?",
        "Run the benchmark and report the results",
        "Execute the test suite and show the coverage",
        "When implementing the semantic cache layer, consider...",
        "Test the classifier with various edge case inputs",
        "Test the router with various payload configurations",
    ],
)
def test_procedural_gpu_patterns_at_085(prompt):
    """Procedural/contextual GPU patterns boosted from 0.80→0.85."""
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for: {prompt!r}"
    assert d.confidence >= 0.85, f"Expected conf >= 0.85, got {d.confidence} for: {prompt!r}"


# ── EXP-0.82-BATCH-BOOST: bug fixes + 21×0.82→0.85 ──────────────────────────


class TestMakeCodeQualityMultiWord:
    """make-code-quality now allows up to 3 words before quality adjective."""

    def test_two_word_subject(self):
        d = classify("Make the task classifier more readable")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_two_word_subject_maintainable(self):
        d = classify("Make the routing logic more maintainable")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_fp_guard_no_quality_adj(self):
        d = classify("Make it work")
        assert d.node == "npu"


class TestUpdateCodeArtifactExpanded:
    """update-code-artifact now covers suite, classifier, orchestrator, etc."""

    def test_update_test_suite(self):
        d = classify("Update the test suite to use async fixtures")
        assert d.node == "gpu"
        assert d.confidence >= 0.85

    def test_update_classifier(self):
        d = classify("Update the classifier to handle streaming inputs")
        assert d.node == "gpu"
        assert d.confidence >= 0.85


@pytest.mark.parametrize(
    "prompt",
    [
        "What are the best practices for distributed systems design?",
        "Refactor the cost-aware router to use async patterns",
        "Review the compound executor implementation",
        "Compare the triune orchestrator vs flat routing approach",
        "Perform a security audit of the auth service",
        "Add logging to the classifier for debugging",
        "Scaffold a new microservice with FastAPI",
        "Run the inference benchmark and report results",
        "Calculate the average latency for 1000 concurrent requests",
        "Walk me through the complete compound engineering loop",
        "Plan how to migrate the SurrealDB schema",
    ],
)
def test_batch_0_82_boost_to_085(prompt):
    """21 GPU patterns boosted from 0.82→0.85 with no regressions."""
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for: {prompt!r}"
    assert d.confidence >= 0.85, f"Expected conf >= 0.85, got {d.confidence} for: {prompt!r}"


# ── EXP-0.78-PATTERNS: noun-form why-verbs + implement-multi-word boost ───────


@pytest.mark.parametrize(
    "prompt",
    [
        # noun-form degradation/drop/increase now hit specific why-question at 0.85
        "Why does the compound loop experience throughput degradation after 50 concurrent sessions?",
        "Why did the semantic cache hit rate drop below 80% on production yesterday?",
        "Why does the JEPA world model produce increasing surprise scores over time?",
    ],
)
def test_why_noun_form_verbs_at_085(prompt):
    """Why-question pattern extended with noun-form degradation/drop/increase terms."""
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for: {prompt!r}"
    assert d.confidence >= 0.85, f"Expected conf >= 0.85, got {d.confidence} for: {prompt!r}"


@pytest.mark.parametrize(
    "prompt",
    [
        "Implement the semantic cache with TTL eviction",
        "Implement a retry policy with exponential backoff",
        "Implement an async message queue using Redis",
    ],
)
def test_implement_multi_word_at_082(prompt):
    """implement multi-word component boosted from 0.78→0.82."""
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for: {prompt!r}"
    assert d.confidence >= 0.82, f"Expected conf >= 0.82, got {d.confidence} for: {prompt!r}"


def test_retrospective_why_still_npu():
    """Retrospective why-did-we pattern still overrides GPU patterns."""
    d = classify("Why did we choose to implement this?")
    assert d.node == "npu"


# ── EXP-HOW-DOES-EXTENDED: {2,4} subject + produce/prevent/enable verbs ──────


@pytest.mark.parametrize(
    "prompt",
    [
        "How does the JEPA encoder produce embeddings?",
        "How does the circuit breaker prevent cascading failures?",
        "How does the rate limiter enforce quotas?",
        "How does the consensus algorithm ensure consistency?",
        "How does the cache determine when to evict?",
        "How does the router decide which tier to use?",
        "How does the classifier compute confidence scores?",
    ],
)
def test_how_does_extended_verbs_at_085(prompt):
    """how-does-X-work extended with technical process and causation verbs."""
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for: {prompt!r}"
    assert d.confidence >= 0.85, f"Expected conf >= 0.85, got {d.confidence} for: {prompt!r}"


def test_how_does_this_stays_npu():
    """Trivial 'How does this work?' (1-word subject) stays NPU via length fallback."""
    d = classify("How does this work?")
    assert d.node == "npu"


# ── EXP-GAPS-SWEEP: ML verbs, server noun, language list, what-should ────────


@pytest.mark.parametrize(
    "prompt",
    [
        "How does a neural network learn?",
        "How does the model adapt to new data?",
        "How does the optimizer converge?",
    ],
)
def test_how_does_ml_verbs(prompt):
    """how-does-X-work extended with ML training verbs (learn/adapt/converge)."""
    d = classify(prompt)
    assert d.node == "gpu"
    assert d.confidence >= 0.85


@pytest.mark.parametrize(
    "prompt",
    [
        "Build a Go HTTP server with middleware",
        "Create a gRPC server with streaming",
    ],
)
def test_build_server_gpu(prompt):
    """'server' added to build-service-or-endpoint noun list."""
    d = classify(prompt)
    assert d.node == "gpu"
    assert d.confidence >= 0.85


@pytest.mark.parametrize(
    "prompt",
    [
        "Implement a REST client in Go",
        "Implement a parser in Haskell",
        "Implement a web crawler in Rust",
    ],
)
def test_implement_in_expanded_languages(prompt):
    """implement-in-language expanded with Haskell, Erlang, Elixir, Go, etc."""
    d = classify(prompt)
    assert d.node == "gpu"
    assert d.confidence >= 0.85


@pytest.mark.parametrize(
    "prompt",
    [
        "What should I do when the GPU memory is exhausted?",
        "What should I check if the tests are failing?",
        "What should we do if the cache becomes stale?",
        "What should I investigate when latency spikes?",
    ],
)
def test_what_should_i_do_troubleshooting(prompt):
    """New what-should-I-do-if/when troubleshooting pattern at 0.85."""
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for: {prompt!r}"
    assert d.confidence >= 0.85


def test_what_should_i_do_no_context_stays_npu():
    """Bare 'What should I do?' with no when/if context stays NPU."""
    d = classify("What should I do?")
    assert d.node == "npu"
