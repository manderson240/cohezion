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
_TYPE_CONFIG: dict[str, tuple[str, int]] = {
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
    (re.compile(r"```|def |class |import |#include|func |fn ", re.S), 0.95, "code context"),
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
