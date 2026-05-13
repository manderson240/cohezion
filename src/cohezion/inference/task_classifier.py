"""
Task classifier for compound inference routing.

Classifies prompts into output types and assigns the optimal hardware tier
(NPU vs GPU) with an appropriate quality gate threshold.

Design: pure-heuristic, zero latency (< 0.1ms), no model calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Output type → (preferred node, quality gate chars)
# quality_gate_chars=0 means "trust any non-empty response"
_TYPE_CONFIG: dict[str, tuple[Literal["npu", "gpu"], int]] = {
    "short_categorical": ("npu", 0),  # single word / letter / label
    "short_answer": ("npu", 10),  # 1-3 sentences, direct answer
    "medium_generation": ("gpu", 0),  # multi-sentence, some structure
    "long_generation": ("gpu", 0),  # essay, detailed explanation
    "code": ("gpu", 0),  # code output
    "math_reasoning": ("gpu", 0),  # multi-step calculation
}


@dataclass(frozen=True)
class RouteDecision:
    node: Literal["npu", "gpu"]
    output_type: str
    quality_gate_chars: int
    confidence: float  # 0.0 – 1.0
    reason: str

    def __str__(self) -> str:
        return f"{self.node.upper()}({self.output_type}, gate={self.quality_gate_chars}, conf={self.confidence:.2f})"


# Compiled patterns — ordered highest-confidence first
_CATEGORICAL_PATTERNS = [
    # Explicit format instructions
    (
        re.compile(r"\breply with (exactly |only )?one word\b", re.I),
        1.0,
        "explicit one-word instruction",
    ),
    (re.compile(r"\bone word (only|answer|reply)\b", re.I), 1.0, "explicit one-word instruction"),
    (
        re.compile(r"\breply with (exactly |only )?one letter\b", re.I),
        1.0,
        "explicit one-letter instruction",
    ),
    (re.compile(r"\banswer with (a |one )?letter\b", re.I), 1.0, "explicit letter answer"),
    (re.compile(r"\breply with (yes|no) or (no|yes)\b", re.I), 1.0, "yes/no question"),
    (re.compile(r"\b(true|false) only\b", re.I), 0.95, "true/false only"),
    # Categorical options in prompt
    (
        re.compile(r"(?:POSITIVE|NEGATIVE|NEUTRAL).*(?:POSITIVE|NEGATIVE|NEUTRAL)", re.I),
        0.90,
        "sentiment categories",
    ),
    (
        re.compile(r"(?:\bA\)|\bB\)|\bC\)|\bD\)).*(?:\bA\)|\bB\)|\bC\)|\bD\))", re.S),
        0.90,
        "multiple choice A/B/C/D",
    ),
    (re.compile(r"\bclassify (this|as|the)\b", re.I), 0.85, "classify task"),
    (re.compile(r"\b(is this|which is) (a |an |the )?\w+\?", re.I), 0.80, "is-this classification"),
]

_SHORT_ANSWER_PATTERNS = [
    (re.compile(r"\bin one sentence\b", re.I), 0.95, "one sentence requested"),
    (
        re.compile(r"\bbriefly (explain|describe|summarize|state)\b", re.I),
        0.90,
        "brief explanation",
    ),
    (re.compile(r"\bsummariz(e|ing)\b.*\bone sentence\b", re.I), 0.90, "one-sentence summary"),
    (
        re.compile(r"\bwhat (is|are) the (name|result|output|answer)\b", re.I),
        0.80,
        "direct what-is question",
    ),
    (re.compile(r"\bname (the|a|one)\b", re.I), 0.75, "name-the entity"),
    # Compound loop explanation patterns — high frequency, NPU-suitable
    (
        re.compile(r"\bwhat (is|are|does|do)\b.{0,60}\?$", re.I | re.S),
        0.70,
        "direct what-is/does question",
    ),
    (
        re.compile(r"\b(describe|explain)\b.{0,80}\?$", re.I | re.S),
        0.65,
        "describe or explain request",
    ),
]

_GPU_PATTERNS = [
    # Code generation — allow adjectives between article and noun ("a Python function", "a simple script")
    (
        re.compile(
            r"\b(write|implement|create|generate|build)\s+(a |an |the )?(\w+ )?(function|class|script|module|code|program)\b",
            re.I,
        ),
        1.0,
        "code generation",
    ),
    # Code context: keyword must appear after backtick/newline/tab (actual code, not prose)
    # Prevents "What does class inheritance mean?" from routing to GPU
    (
        re.compile(r"```|(?:^|[\n\t`])[ \t]*(?:def |class |import )|#include|func |fn ", re.S),
        0.95,
        "code context",
    ),
    # Long generation
    (
        re.compile(
            r"\b(write|create|generate|draft)\s+(a |an |the )?(essay|report|article|document|proposal)\b",
            re.I,
        ),
        0.95,
        "document generation",
    ),
    (
        re.compile(r"\bexplain (in detail|thoroughly|step.by.step)\b", re.I),
        0.90,
        "detailed explanation",
    ),
    (re.compile(r"\b(design|architect|plan)\s+(a |an |the )\b", re.I), 0.85, "design task"),
    # Math/reasoning chains
    (
        re.compile(r"\b(prove|derive|calculate|compute)\s+\w+.*\bstep\b", re.I),
        0.90,
        "multi-step math",
    ),
    (re.compile(r"\bsolve.*show.*(work|steps)\b", re.I), 0.85, "show-work problem"),
    # Procedural guidance — "how do/can/should we/I [do something]"
    # Catches multi-step guidance questions that need full reasoning (not single-word answers)
    (
        re.compile(r"\bhow (do|can|should|might|would) (we|I|you)\b", re.I),
        0.80,
        "procedural guidance how-do-we",
    ),
    # "How to configure/implement/handle/manage" — setup and integration questions
    (
        re.compile(
            r"\bhow (do|can|should|to) (set up|configure|implement|handle|fix|manage)\b",
            re.I,
        ),
        0.82,
        "procedural how-to-configure",
    ),
    # Explain [content] in detail / step-by-step — preamble content may separate them
    (
        re.compile(r"\bexplain\b.{5,50}\b(in detail|thoroughly|step.by.step)\b", re.I | re.S),
        0.88,
        "detailed explanation with preamble",
    ),
    # Implement [complex artifact] — logic/pipeline/system/workflow/mechanism
    (
        re.compile(
            r"\bimplement (the |a |an )\w+.{5,}\b(logic|pipeline|system|workflow|mechanism)\b",
            re.I,
        ),
        0.80,
        "implement complex logic/system",
    ),
    # Implement [multi-word component] (broader than above — catches "impl the semantic cache with...")
    (
        re.compile(r"\bimplement (the |a |an )\w+\s+\w+\b.{5,}", re.I),
        0.78,
        "implement multi-word component",
    ),
    # Test/spec generation — "write a unit test for...", "write tests for..."
    (
        re.compile(
            r"\b(write|create|generate)\s+(a |an |the )?(unit |integration |regression |)test(s?)\b",
            re.I,
        ),
        0.95,
        "test generation",
    ),
    # Document generation with adjective(s) — "draft a technical report", "write a comprehensive detailed proposal"
    # (\w+ )* allows zero or more adjectives between article and document noun
    (
        re.compile(
            r"\b(write|create|generate|draft)\s+(a |an |the )?(\w+ )*(essay|report|article|document|proposal)\b",
            re.I,
        ),
        0.95,
        "document generation with adjective(s)",
    ),
    # Best practices / guidelines / recommendations — requires detailed enumeration
    (
        re.compile(r"\bwhat are (the |some )?(best practices|guidelines|recommendations)\b", re.I),
        0.82,
        "best practices enumeration",
    ),
    # Explain how [mechanism] [does something] — causation explanation
    (
        re.compile(
            r"\bexplain how\b.{5,}\b(prevents|enables|improves|works|operates|handles)\b",
            re.I | re.S,
        ),
        0.80,
        "explain how mechanism",
    ),
    # How do you [diagnose/fix/solve/debug] — troubleshooting questions
    (
        re.compile(r"\bhow do you (diagnose|debug|fix|solve|troubleshoot|handle)\b", re.I),
        0.80,
        "troubleshooting how-do-you",
    ),
    # Document generation extended — analysis, guide, benchmark, comparison, overview
    (
        re.compile(
            r"\b(write|create|generate|draft)\s+(a |an |the )?(\w+ )*(analysis|guide|benchmark|comparison|overview|tutorial|walkthrough)\b",
            re.I,
        ),
        0.92,
        "document generation extended nouns",
    ),
    # "Can you [action verb] those/these/the [noun]" — multi-step task requests
    (
        re.compile(
            r"\bcan you (resume|manage|orchestrate|handle|coordinate|configure|implement|create|build)\b",
            re.I,
        ),
        0.80,
        "can-you-action-request",
    ),
    # "How to run / execute / set up [task]" — procedural execution
    (
        re.compile(r"\bhow to (run|execute|start|launch|trigger|perform|conduct)\b", re.I),
        0.80,
        "how-to-run-execute",
    ),
    # "Implement the [adjective(s)]* policy/strategy/approach/pipeline"
    # Uses .{0,40} to skip over hyphenated compound adjectives like "multi-tier"
    (
        re.compile(
            r"\bimplement (the |a |an ).{0,40}\b(policy|strategy|approach|mechanism|framework|workflow)\b",
            re.I,
        ),
        0.82,
        "implement policy/strategy",
    ),
    # "Write a [adj]* test suite" — broader test generation
    (
        re.compile(
            r"\b(write|create|generate)\s+(a |an |the )?(\w+ )*(test suite|test set|test harness)\b",
            re.I,
        ),
        0.92,
        "test suite generation",
    ),
    # Multi-adjective code generation — "Create the X Y Z module/component"
    (
        re.compile(
            r"\b(write|implement|create|generate|build)\s+(a |an |the )?(\w+ ){2,}(function|class|script|module|code|program|component|system)\b",
            re.I,
        ),
        0.95,
        "code generation multi-adjective",
    ),
    # Engineering task verbs — refactor, debug, profile, optimize, audit, review
    # These require detailed analysis of code/systems → GPU
    (
        re.compile(
            r"\b(refactor|optimize|profile|debug|audit|review|trace)\b.{0,30}\b(the|a|an|this)\b",
            re.I,
        ),
        0.82,
        "engineering task verb",
    ),
    # "Document the [X] with examples/API/guide" — structured documentation
    (
        re.compile(r"\bdocument (the |a |an |this )\w+.{0,40}\b(api|examples|guide|usage)\b", re.I),
        0.85,
        "documentation with structured content",
    ),
    # "Compare [X] and [Y] response quality / performance" — requires parallel evaluation
    (
        re.compile(
            r"\bcompare\b.{0,40}\b(and|vs|versus)\b.{0,40}\b(quality|performance|latency|accuracy|response)\b",
            re.I,
        ),
        0.82,
        "comparative evaluation",
    ),
    # "Test the [X] with various [Y] configurations" — test design requiring analysis
    (
        re.compile(
            r"\btest (the |a |an )\w+.{0,30}\b(configurations?|scenarios?|cases?|fixture|input)\b",
            re.I,
        ),
        0.80,
        "test with various configurations",
    ),
    # ML/training task verbs — fine-tune, train, finetune
    (
        re.compile(
            r"\b(fine-tune|finetune|train|retrain|fine tune)\b.{0,30}\b(model|network|classifier|detector)\b",
            re.I,
        ),
        0.88,
        "ml training task",
    ),
    # System integration verbs — integrate, wire, connect, hook up
    (
        re.compile(r"\b(integrate|wire up|connect|hook up)\b.{0,30}\b(with|into|to)\b", re.I),
        0.82,
        "system integration task",
    ),
    # "Why is/are [X] [doing/returning/failing/scoring]" — debugging question
    (
        re.compile(
            r"\bwhy (is|are|does|did|isn't|aren't|doesn't|didn't)\b.{0,50}\b(returning|failing|scoring|not|error|broken|wrong|zero|null|empty)\b",
            re.I,
        ),
        0.82,
        "debugging why-question",
    ),
    # "Generate the [config/JSON/YAML/entry/file] for [X]" — config generation
    (
        re.compile(
            r"\bgenerate (the |a |an |this )(config|configuration|settings|json|yaml|entry|file|manifest|schema)\b",
            re.I,
        ),
        0.85,
        "configuration generation",
    ),
    # "Run the [X] and [report/show/list/output]" — execution + reporting
    (
        re.compile(
            r"\brun (the |a |an )(\w+ ){0,3}(and|then) (report|show|list|output|print|display|log)\b",
            re.I,
        ),
        0.80,
        "run-and-report task",
    ),
    # Derive/calculate without explicit "step" — complex mathematical operations
    (
        re.compile(
            r"\b(derive|calculate|compute) (the |a |an )(\w+ )*(matrix|transform|projection|distribution|gradient|kernel|embedding)\b",
            re.I,
        ),
        0.88,
        "derive/calculate complex math",
    ),
    # Code generation with hyphenated adjective (e.g. "Implement the JEPA-based reward function")
    (
        re.compile(
            r"\b(write|implement|create|generate|build) (the |a |an )[\w-]+.{0,40}\b(function|class|method|module|component|system)\b",
            re.I,
        ),
        0.88,
        "code generation hyphenated adjective",
    ),
]


def classify(prompt: str) -> RouteDecision:
    """Classify a prompt and return routing decision. Zero model calls."""
    prompt_len = len(prompt)

    # ── Check GPU patterns first (highest cost to mis-route) ────────────────
    for pattern, confidence, reason in _GPU_PATTERNS:
        if pattern.search(prompt):
            node, gate = (
                _TYPE_CONFIG["code"] if "code" in reason else _TYPE_CONFIG["long_generation"]
            )
            otype = "code" if "code" in reason else "long_generation"
            return RouteDecision(
                node=node,
                output_type=otype,
                quality_gate_chars=gate,
                confidence=confidence,
                reason=reason,
            )

    # ── Check categorical patterns ───────────────────────────────────────────
    for pattern, confidence, reason in _CATEGORICAL_PATTERNS:
        if pattern.search(prompt):
            node, gate = _TYPE_CONFIG["short_categorical"]
            return RouteDecision(
                node=node,
                output_type="short_categorical",
                quality_gate_chars=gate,
                confidence=confidence,
                reason=reason,
            )

    # ── Check short-answer patterns ──────────────────────────────────────────
    for pattern, confidence, reason in _SHORT_ANSWER_PATTERNS:
        if pattern.search(prompt):
            node, gate = _TYPE_CONFIG["short_answer"]
            return RouteDecision(
                node=node,
                output_type="short_answer",
                quality_gate_chars=gate,
                confidence=confidence,
                reason=reason,
            )

    # ── Length-based fallback ────────────────────────────────────────────────
    if prompt_len <= 150:
        return RouteDecision(
            node="npu",
            output_type="short_answer",
            quality_gate_chars=10,
            confidence=0.60,
            reason=f"short prompt ({prompt_len} chars), defaulting to NPU",
        )
    elif prompt_len <= 400:
        return RouteDecision(
            node="npu",
            output_type="medium_generation",
            quality_gate_chars=20,
            confidence=0.55,
            reason=f"medium prompt ({prompt_len} chars), trying NPU first",
        )
    else:
        return RouteDecision(
            node="gpu",
            output_type="long_generation",
            quality_gate_chars=0,
            confidence=0.60,
            reason=f"long prompt ({prompt_len} chars), routing to GPU",
        )
