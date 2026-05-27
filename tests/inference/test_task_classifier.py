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

    def test_definitional_question_confidence(self):
        # "What is X?" routes NPU via 1-2-term definitional pattern (0.78) — not length fallback
        d = classify("What is a compiler?")
        assert d.node == "npu"
        assert (
            0.70 <= d.confidence < 0.90
        )  # higher than length fallback (0.60), lower than explicit (0.95)

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


# ---------------------------------------------------------------------------
# Real-world routing: external research and URL patterns (exp_MMMM findings)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "Do additional research on huggingface and arxiv to identify tip of the spear developments",
        "research new papers on LENR physics",
        "research huggingface for better embedding models",
        "now research https://www.stealthskater.com/Intro.htm",
    ],
)
def test_external_research_routes_to_gpu(prompt):
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for research task: {prompt!r}"
    assert d.output_type == "long_generation"


@pytest.mark.parametrize(
    "prompt",
    [
        "Integrate https://github.com/DVampire/Autogenesis",
        "can we try https://huggingface.co/Ring-2.6-1T with lemonade server",
        "test https://github.com/some/repo integration",
    ],
)
def test_url_action_routes_to_gpu(prompt):
    d = classify(prompt)
    assert d.node == "gpu", f"Expected gpu for URL action: {prompt!r}"


def test_real_world_routing_accuracy_19_prompts():
    """Regression: 19 real human prompts from session history must route correctly."""
    cases = [
        (
            "How do we recover the other local claude code sessions that were killed to prevent OOM",
            "gpu",
        ),
        ("Can you resume and manage those sessions with headless claude code sessions?", "gpu"),
        ("Yes, give them different PRs each", "npu"),
        (
            "Do additional research on huggingface and arxiv to identify tip of the spear developments",
            "gpu",
        ),
        ("Integrate https://github.com/DVampire/Autogenesis", "gpu"),
        ("how can we extend this to improve FLUME?", "gpu"),
        ("now research https://www.stealthskater.com/Intro.htm", "gpu"),
        ("can we try https://huggingface.co/Ring-2.6-1T with lemonade server", "gpu"),
        ("Create a merge request to main", "gpu"),
        ("check the CI pipeline", "gpu"),
        ("Why is /ultraplan broken?", "gpu"),
        ("investigate that 96MB file", "gpu"),
        ("write tests for another paper", "gpu"),
        ("refactor skill_registry.json", "gpu"),
        ("How do we enable autocompact?", "gpu"),
        ("Be careful with destructive operations.", "npu"),
        ("Are we using all gemma 4 models?", "npu"),
        ("Let's stay low and slow for now.", "npu"),
        ("shoud be in .env don't print it", "npu"),
    ]
    misses = [(p, e, classify(p).node) for p, e in cases if classify(p).node != e]
    assert not misses, f"Routing misses: {misses}"


# ── Round 8 patterns (2026-05-27) ────────────────────────────────────────────


class TestWhichResourcePreOverride:
    """exp_YYYY2: 'Which port/model/version does X use?' → NPU before GPU scan.

    'port' is in the extended engineering verb list (can trigger GPU), but
    'Which port does the NPU tier use?' is a factual lookup, not an engineering task.
    The pre-override fires on ^which + resource-noun + does/is (≤75 chars).
    """

    def test_which_port_routes_npu(self):
        d = classify("Which port does the NPU tier use?")
        assert d.node == "npu"
        assert "which-resource" in d.reason

    def test_which_model_routes_npu(self):
        d = classify("Which model does the iGPU tier run?")
        assert d.node == "npu"

    def test_which_default_routes_npu(self):
        d = classify("Which default does CLAUDE_CODE_STOP_HOOK_BLOCK_CAP use?")
        assert d.node == "npu"

    def test_which_library_recommendation_routes_gpu(self):
        # 'Which library should I use?' is a recommendation, not a factual lookup
        d = classify("Which library should I use for structured logging?")
        assert d.node == "gpu"

    def test_which_approach_recommendation_routes_gpu(self):
        d = classify("Which approach should I use for the new caching strategy?")
        assert d.node == "gpu"


class TestRouteTaskPrefixPreOverride:
    """exp_ZZZZ2: 'Route/Classify this task: X' → NPU (meta-routing instruction).

    Without the override, GPU patterns fire on technical nouns in the content after
    the colon (e.g., 'port', 'implement', 'batch processing pipeline').
    """

    def test_route_this_task_routes_npu(self):
        d = classify("Route this task: short factual question about a port number")
        assert d.node == "npu"
        assert "route-task-prefix" in d.reason

    def test_route_this_request_routes_npu(self):
        d = classify("Route this request: is this a code generation task?")
        assert d.node == "npu"

    def test_classify_this_prompt_routes_npu(self):
        d = classify("Classify this prompt: is it code or text?")
        assert d.node == "npu"

    def test_route_task_with_gpu_content_still_npu(self):
        # Content after colon has GPU verbs, but prefix overrides
        d = classify(
            "Route this task: implement a new batch processing pipeline for the compound loop"
        )
        assert d.node == "npu"


class TestBrevitySummarizeDigitForms:
    """exp_DDDDD3: 'Summarize in N sentences' → NPU (brevity-qualified).

    The pattern previously only matched 'one/two/three/a single'; digit forms like
    '2 sentences' or '3 bullets' now also route to NPU.
    """

    def test_summarize_in_one_sentence_npu(self):
        d = classify("Summarize the compound loop in one sentence")
        assert d.node == "npu"

    def test_summarize_in_2_sentences_npu(self):
        d = classify("Summarize the compound loop in 2 sentences")
        assert d.node == "npu"

    def test_summarize_in_3_sentences_npu(self):
        d = classify("Summarize the HIHO stability principle in 3 sentences")
        assert d.node == "npu"

    def test_briefly_summarize_routes_npu(self):
        d = classify("Briefly summarize the HIHO stability principle")
        assert d.node == "npu"

    def test_summarize_without_brevity_routes_gpu(self):
        # No brevity qualifier → GPU (complex architectural summary)
        d = classify(
            "Summarize the entire compound engineering loop architecture with diagrams and code examples"
        )
        assert d.node == "gpu"


class TestBacktickVerbEngineeringPreOverride:
    """exp_EEEEE3: Backtick-prefixed engineering verb → GPU (imperative command form).

    Users wrap engineering command verbs in backticks to signal intent explicitly.
    The override fires before the extended engineering verb object-allowlist check,
    which fails when the object is a system name not in the allowlist.
    """

    def test_backtick_port_with_unrecognized_object_routes_gpu(self):
        d = classify("`port` the triune_orchestrator to support async batch processing")
        assert d.node == "gpu"
        assert "backtick" in d.reason

    def test_backtick_port_with_compound_path_routes_gpu(self):
        d = classify("`port` the routing logic to the new AsyncFleet API")
        assert d.node == "gpu"

    def test_backtick_migrate_routes_gpu(self):
        d = classify("`migrate` the triune_orchestrator to async")
        assert d.node == "gpu"

    def test_backtick_refactor_still_routes_gpu(self):
        # refactor already worked via engineering-task-verb; backtick override also fires
        d = classify("`refactor` the executor.py module to use async patterns")
        assert d.node == "gpu"

    def test_no_backtick_port_with_unrecognized_object_routes_npu(self):
        # Without backticks, 'port the triune_orchestrator' falls to length-default NPU
        # Quality gate handles escalation if response is insufficient
        d = classify("Port the triune_orchestrator to support async batch processing")
        assert d.node == "npu"

    def test_backtick_true_false_not_triggered(self):
        # Non-engineering backtick tokens should not fire the override
        d = classify("`true` or `false`: the FlumeVAE uses 256D latent space")
        assert d.node == "npu"


class TestReleaseNotesFalsePositiveFix:
    """exp_FFFFF3: 'release notes' noun phrase must not trigger deploy/provision GPU pattern.

    The deploy/provision GPU pattern matched 'release' as a verb, catching documentation
    references like 'List cached release notes files'. Fixed with negative lookahead
    release(?!\\s+notes?\\b) — deployment actions still route GPU.
    """

    def test_list_release_notes_routes_npu(self):
        d = classify("List cached release notes files")
        assert d.node == "npu"

    def test_read_release_notes_cache_routes_npu(self):
        d = classify("Read the most recent release notes cache")
        assert d.node == "npu"

    def test_fetch_release_notes_routes_npu(self):
        d = classify("Fetch release notes for v2.1.137 through v2.1.152")
        assert d.node == "npu"

    def test_release_to_production_still_gpu(self):
        # Actual deployment action — must still route GPU
        d = classify("Release the new API version to production")
        assert d.node == "gpu"
        assert "deploy" in d.reason

    def test_release_version_to_appstore_still_gpu(self):
        d = classify("Release version 2.0 to the AppStore")
        assert d.node == "gpu"

    def test_review_release_notes_and_update_config_still_gpu(self):
        # 'Review /release-notes and update' — compound task, must stay GPU
        d = classify("Review /release-notes and update our configuration accordingly")
        assert d.node == "gpu"


class TestRunAndReportHyphenatedFix:
    """exp_ZZZZ2: run-and-report GPU pattern must match hyphenated tokens.

    The original pattern used (\\w+ ){0,3} which excludes hyphens. 'dry-run' contains
    a hyphen so 'Run the compound cycle dry-run and report' did not match. Fixed by
    changing to (?:[\\w-]+ ){0,4} to allow hyphenated words.
    """

    def test_run_dry_run_and_report_routes_gpu(self):
        d = classify("Run the compound cycle dry-run and report which phases pass")
        assert d.node == "gpu"
        assert "run-and-report" in d.reason

    def test_execute_pre_commit_and_report_routes_gpu(self):
        d = classify("Execute the pre-commit hook and report any errors")
        assert d.node == "gpu"

    def test_run_benchmark_and_report_routes_gpu(self):
        d = classify("Run a benchmark and report the scores")
        assert d.node == "gpu"


class TestBacktickNormalizationNonEngineeringPath:
    """exp_DDDDD3: Backtick-quoted verbs normalized before GPU scan.

    `re.sub(r'`(\\w+)`', r'\\1', prompt)` strips backticks before the GPU pattern scan
    so that extended engineering verb patterns can match verbs like `validate`, `parse`.
    Verbs not in the _BACKTICK_VERB_ENGINEERING_PATTERN but in GPU patterns still work.
    """

    def test_backtick_validate_routes_gpu_via_extended_verb(self):
        d = classify("`validate` the pipeline schemas before deployment")
        assert d.node == "gpu"

    def test_backtick_parse_routes_gpu_via_extended_verb(self):
        d = classify("`parse` the JSON schemas for the API validation layer")
        assert d.node == "gpu"
