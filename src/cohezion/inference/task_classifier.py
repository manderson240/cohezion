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
    # Also matches inline code-fix requests with Python-like syntax after colon
    (
        re.compile(
            r"```|(?:^|[\n\t`])[ \t]*(?:def |class |import )|#include|func |fn |"
            r"\bfix\s+it\s*:.*\bfor\b|\bfix\s+this\s*:.*\bfor\b",
            re.S | re.I,
        ),
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
    # Procedural guidance — "how do/can/should we [do something]"
    # "we" = team-level architectural question; excludes "I/you" + simple run/check verbs
    (
        re.compile(r"\bhow (do|can|should|might|would) we\b", re.I),
        0.80,
        "procedural guidance how-do-we",
    ),
    # "How to configure/implement/handle/manage" — requires substantial follow-up context
    # (≥10 chars after the keyword to exclude "How to configure nginx?" style short queries)
    (
        re.compile(
            r"\bhow (do|can|should|to) (set up|configure|implement|handle|fix|manage)\b.{10,}",
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
    # Excludes "why did we implement" (retrospective decision — NPU)
    (
        re.compile(r"\bimplement (the |a |an )\w+\s+\w+\b.{5,}", re.I),
        0.78,
        "implement multi-word component",
    ),
    # "implement sorting/caching/searching/batching/etc" — algorithm/operation as direct object
    (
        re.compile(
            r"\bimplement\s+(?:the\s+|a\s+|an\s+)?(?:\w+\s+)?(?:sort(?:ing)?|search(?:ing)?|cach(?:e|ing)|hash(?:ing)?|batch(?:ing)?|rout(?:e|ing)|queu(?:e|ing)|stack(?:ing)?|heap|tree|graph|index(?:ing)?|filter(?:ing)?|compres(?:s|sion)|encod(?:e|ing)|algorithm|protocol)\b",
            re.I,
        ),
        0.85,
        "implement algorithm/operation",
    ),
    # "implement JWT/OAuth/SAML/etc." — tech acronym without article (common in mixed-signal prompts)
    (
        re.compile(
            r"\bimplement\s+(?:jwt|oauth|oauth2|saml|ldap|ssl|tls|grpc|websocket|webhook|oidc|sso)\b",
            re.I,
        ),
        0.88,
        "implement tech protocol",
    ),
    # "When implementing X" / "While implementing X" — gerund form of implement
    (
        re.compile(r"\b(?:when|while|after|before)\s+implementing\b", re.I),
        0.80,
        "implementing gerund context",
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
    # Cap at {2,4} to prevent O(n²) backtracking on adversarial repeated-word inputs
    (
        re.compile(
            r"\b(write|implement|create|generate|build)\s+(a |an |the )?(\w+ ){2,4}(function|class|script|module|code|program|component|system)\b",
            re.I,
        ),
        0.95,
        "code generation multi-adjective",
    ),
    # Engineering task verbs — refactor, debug, profile, optimize, audit, trace
    # "review" excluded — too ambiguous ("review before meeting" FP). Use code-review pattern below.
    (
        re.compile(
            r"\b(refactor|optimize|profile|debug|audit|trace|rewrite|rework)\b.{0,30}\b(the|a|an|this|it)\b",
            re.I,
        ),
        0.82,
        "engineering task verb",
    ),
    # Code review — "review" only when paired with code-specific nouns
    (
        re.compile(
            r"\breview\b.{0,30}\b(code|implementation|pull\s+request|pr\b|changes|diff|api|module|test|function|class|endpoint|service)\b",
            re.I,
        ),
        0.82,
        "code review task",
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
    # ML/training task verbs — fine-tune, train, finetune (expanded targets)
    (
        re.compile(
            r"\b(fine-tune|finetune|train|retrain|fine tune)\b.{0,40}\b(model|network|classifier|detector|adapter|checkpoint|weights|embeddings|backbone|encoder)\b",
            re.I,
        ),
        0.88,
        "ml training task",
    ),
    # System integration verbs — integrate, wire, connect, hook up, set up X integration
    (
        re.compile(
            r"\b(integrate|wire up|connect|hook up|set up)\b.{0,40}\b(with|into|to|integration|monitoring|tracking|observability)\b",
            re.I,
        ),
        0.82,
        "system integration task",
    ),
    # Wire X into Y (without "up") — service wiring
    (
        re.compile(
            r"\bwire\s+(?:the\s+)?\w+(?:\s+\w+)?\s+(?:service|module|component|layer|system)\b",
            re.I,
        ),
        0.82,
        "service wiring task",
    ),
    # "Why is/are [X] [doing/returning/failing/scoring]" — specific debugging verbs
    (
        re.compile(
            r"\bwhy (is|are|does|did|isn't|aren't|doesn't|didn't)\b.{0,60}\b(returning|fail(ing)?|scoring|not|error|broken|wrong|zero|null|empty|opening|dropping|crashing|slow|leaking|growing|blocking|hanging?|stuck|exhausting|falling|rising|spiking|timing\s+out|degrading|throwing|breaking)\b",
            re.I,
        ),
        0.82,
        "debugging why-question",
    ),
    # Long "why" question (≥45 chars) — complex system behavior investigation
    (
        re.compile(r"\bwhy\s+(?:does|is|are|did|doesn't|isn't|aren't|didn't)\b.{42,}", re.I),
        0.78,
        "long debugging why-question",
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
    # IaC/infra tool generation — nginx, k8s, terraform, docker, helm config files
    (
        re.compile(
            r"\b(generate|create|produce|write|build)\s+(?:a\s+)?(?:nginx|kubernetes|k8s|terraform|helm|docker|ansible|puppet|grafana|prometheus)\b",
            re.I,
        ),
        0.88,
        "iac config generation",
    ),
    # SQL query generation — "Generate a SQL query", "Write the SQL for"
    (
        re.compile(r"\b(generate|write|create)\s+(?:a\s+|the\s+)?sql\b", re.I),
        0.88,
        "sql query generation",
    ),
    # "Implement X in [language]" — language-specific algorithm/feature
    (
        re.compile(
            r"\bimplement\b.{0,40}\bin\s+(python|java|c\+\+|cpp|javascript|typescript|go|rust|kotlin|swift|scala|ruby)(?:\W|$)",
            re.I,
        ),
        0.88,
        "implement in language",
    ),
    # Create/build a [adjective(s)] endpoint/service/cache/pipeline/queue
    (
        re.compile(
            r"\b(create|build|add)\s+(?:a\s+)?(?:[\w-]+\s+){0,3}(endpoint|service|api\b|cache|pipeline|queue|handler|middleware)\b",
            re.I,
        ),
        0.82,
        "build service or endpoint",
    ),
    # "Create a K8s/Terraform deployment manifest/spec" — infra manifest
    (
        re.compile(
            r"\b(create|write|produce|generate)\s+(?:a\s+)?(?:\w+\s+)?(manifest|deployment\s+spec|helm\s+chart|infra\s+config)\b",
            re.I,
        ),
        0.85,
        "infra manifest generation",
    ),
    # "Run the [X] and [report/show/list/output]" or "Execute the [X] and report"
    (
        re.compile(
            r"\b(run|execute)\s+(the |a |an )(\w+ ){0,3}(and|then) (report|show|list|output|print|display|log)\b",
            re.I,
        ),
        0.80,
        "run-and-report task",
    ),
    # "Run [tool] experiment/tracking" — ML experiment management
    (
        re.compile(
            r"\brun\s+(?:the\s+)?\w+\s+(?:experiment|tracking|benchmark|evaluation|ablation)\b",
            re.I,
        ),
        0.82,
        "ml experiment run",
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
            r"\b(write|implement|create|generate|build) (the |a |an )[\w-]+.{0,40}\b(function|class|method|module|component|system|autoencoder|encoder|decoder|network|pipeline|layer|schema|model|entity|workflow|blueprint)\b",
            re.I,
        ),
        0.88,
        "code generation hyphenated adjective",
    ),
    # Comparative analysis — "Compare the X vs Y", "Analyze the X metrics", "Evaluate the trade-offs"
    (
        re.compile(r"\b(compare|analyze|evaluate|assess)\s+the\b", re.I),
        0.82,
        "comparative or analytical task",
    ),
    # "Compare X vs Y" / "Compare X versus Y" — direct comparison without "the"
    (
        re.compile(r"\bcompare\s+\w+\s+(?:vs\.?|versus)\b", re.I),
        0.82,
        "direct A-vs-B comparison",
    ),
    # Walk-through / describe full lifecycle
    (
        re.compile(
            r"\b(walk\s+(?:me\s+)?through|describe\s+the\s+(full|complete|entire|detailed))\b", re.I
        ),
        0.82,
        "walk-through or full description",
    ),
    # "Plan how to [migrate/build/redesign]" — architectural planning
    (
        re.compile(r"\bplan\s+how\s+to\b", re.I),
        0.82,
        "architectural planning task",
    ),
    # Draft/write document types — README, ADR, post-mortem, report, proposal
    (
        re.compile(
            r"\b(draft|write)\s+(?:a\s+|an\s+|the\s+)?(?:\w+\s+)?(readme|adr|architecture\s+decision|post.mortem|incident\s+report|design\s+document|proposal|specification)\b",
            re.I,
        ),
        0.88,
        "draft document task",
    ),
    # "Create an end-to-end test" or "build an end-to-end X"
    (
        re.compile(r"\b(?:create|write|build|add)\s+an?\s+end.to.end\s+test\b", re.I),
        0.85,
        "end-to-end test creation",
    ),
    # "Recommended approaches/practices/strategies for X" — GPU analysis tasks
    (
        re.compile(
            r"\b(?:recommended|best)\s+(?:approaches|strategies|patterns|ways|practices)\s+(?:for|to)\b",
            re.I,
        ),
        0.82,
        "recommended approaches analysis",
    ),
]


_RETROSPECTIVE_PATTERN = re.compile(
    r"\bwhy\s+did\s+(?:we|you|they|the\s+team)\s+(?:choose|decide|select|use|go\s+with|adopt|implement|pick)\b",
    re.I,
)

_NEGATION_PATTERN = re.compile(
    r"\b(?:not\s+asking\s+(?:you\s+)?to\s+write|without\s+writing\s+(?:any\s+)?code|don'?t\s+write\s+(?:any\s+)?code|no\s+code\b)",
    re.I,
)


def classify(prompt: str) -> RouteDecision:
    """Classify a prompt and return routing decision. Zero model calls."""
    # Truncate very long prompts — classifier only needs the opening intent phrase
    # Prevents O(n²) backtracking on adversarial 1000+ char inputs
    if len(prompt) > 500:
        prompt = prompt[:500]
    prompt_len = len(prompt)

    # ── Pre-GPU overrides (fire before GPU patterns) ─────────────────────────
    # 1. Negation: "not asking you to write code, just tell me X" → NPU
    if _NEGATION_PATTERN.search(prompt):
        node, gate = _TYPE_CONFIG["short_answer"]
        return RouteDecision(
            node=node,
            output_type="short_answer",
            quality_gate_chars=gate,
            confidence=0.75,
            reason="code generation explicitly negated",
        )

    # 2. Retrospective decision questions stay NPU ───────────────────────────
    # "Why did we choose to implement X?" asks for decision history, not code.
    # Must fire before GPU patterns to prevent "implement" keyword false-routes.
    if _RETROSPECTIVE_PATTERN.search(prompt):
        node, gate = _TYPE_CONFIG["short_answer"]
        return RouteDecision(
            node=node,
            output_type="short_answer",
            quality_gate_chars=gate,
            confidence=0.72,
            reason="retrospective decision question",
        )

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
