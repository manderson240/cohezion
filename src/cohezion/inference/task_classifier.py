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
    # Extended: formula, macro, procedure, query, snippet, lambda, decorator, mixin, interface
    (
        re.compile(
            r"\b(write|implement|create|generate|build)\s+(a |an |the )?(?:[\w-]+ ){0,3}(?:function|class|script|module|code|program|formula|macro|procedure|query|snippet|lambda|decorator|mixin|interface|getters?|setters?|validators?|serializers?|deserializers?|accessors?|migrations?|fixtures?|resolvers?|middlewares?|driver|routine|handler|client|library|daemon|firmware|plugin|extension|adapter|wrapper|proxy|stub|mock|task\b|job\b|service\b|worker|processor|listener|observer|consumer|producer|publisher|subscriber|widget|screen|fragment|composable|activity\b|viewmodel|repository\b|dao\b|coroutine|category\b|entity\b|component|[\w]*viewcontroller|[\w]*recyclerview|[\w]*tableview|[\w]*collectionview|shader|loop\b|controller\b|renderer|pass\b|pipeline|algorithm|simulation|generator|visualiz(?:er|ation)|importer|exporter|converter|transformer|dispatcher|scheduler|executor|runner|scanner|parser\b|loader|hook\b|contract\b|token\b|wallet|oracle|integration\b|connector|bridge\b|gateway\b|registry\b|factory\b|builder\b|chain\b|pool\b|lock(?:ing)?\b|replicas?\b|replication\b|cluster\b|shard(?:ing)?\b|partition(?:ing)?\b|trigger\b|view\b|materialized\b|microservices?|crawler|scraper|spider|fetcher|extractor|classifier\b|embedder|tokenizer|normalizer|vectorizer|profiler|tracer|sampler|prober|collector)\b",
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
        0.85,
        "procedural guidance how-do-we",
    ),
    # "How should I structure/design/organize/architect X" — individual architectural guidance
    (
        re.compile(
            r"\bhow should (?:I|we)\s+(?:structure|design|organize|architect|layout|model|approach|handle|set\s+up)\b",
            re.I,
        ),
        0.85,
        "how-should-I-structure architectural guidance",
    ),
    # "How should [subject] be [handled/structured/done]" — passive voice architectural guidance
    (
        re.compile(
            r"\bhow should\s+(?:\w+\s+){0,3}be\s+(?:handled|done|implemented|structured|organized|managed|configured|tested|used|written|designed|built|stored|cached|deployed|monitored|secured|validated|parsed|serialized|authorized|authenticated)\b",
            re.I,
        ),
        0.85,
        "how-should-X-be passive architectural guidance",
    ),
    # "Should I use X or Y" / "Should this query use X" — architectural/tool decision
    (
        re.compile(
            r"\bshould (?:I|we)\s+use\b.{3,}\b(?:or|vs\.?|versus)\b"
            r"|\bshould (?:this|the)\s+(?:\w+\s+){0,2}use\b",
            re.I,
        ),
        0.85,
        "should-I-use A-or-B decision",
    ),
    # "What are THE [edge cases / time complexity / tradeoffs]" — technical analysis
    # Requires "the" to avoid FP on definitional "What are edge cases?" (no "the")
    (
        re.compile(
            r"\bwhat (is|are)\s+the\s+(?:edge\s+cases?|time\s+complexity|space\s+complexity|big.?o|tradeoffs?|trade.offs?|performance\s+implications?|memory\s+implications?|implications?\s+of|limitations?\s+of|constraints?\s+of|downsides?\s+of|risks?\s+of|best\s+(?:architecture|approach|design|solution|option|choice|way))\b",
            re.I,
        ),
        0.85,
        "technical analysis question",
    ),
    # "What is the best [architecture/approach/design] for X" — architectural guidance
    (
        re.compile(
            r"\bwhat(?:'s| is| are)\s+(?:the\s+)?(?:best|recommended|preferred|ideal|proper|right)\s+(?:architecture|approach|design|solution|option|way|method|strategy|pattern)\s+(?:for|to|when)\b",
            re.I,
        ),
        0.85,
        "best architecture/approach question",
    ),
    # "How to configure/implement/handle/manage" — requires substantial follow-up context
    # (≥10 chars after the keyword to exclude "How to configure nginx?" style short queries)
    (
        re.compile(
            r"\bhow (do|can|should|to) (set up|configure|implement|handle|fix|manage)\b.{10,}",
            re.I,
        ),
        0.85,
        "procedural how-to-configure",
    ),
    # Explain [content] in detail / step-by-step — preamble content may separate them
    (
        re.compile(r"\bexplain\b.{5,50}\b(in detail|thoroughly|step.by.step)\b", re.I | re.S),
        0.88,
        "detailed explanation with preamble",
    ),
    # Implement [complex artifact] — logic/pipeline/system/workflow/mechanism
    # Article is optional: "implement complex logic for..." and "implement the X logic..." both match
    (
        re.compile(
            r"\bimplement (?:the |a |an )?\w+.{5,}\b(logic|pipeline|system|workflow|mechanism)\b",
            re.I,
        ),
        0.85,
        "implement complex logic/system",
    ),
    # Implement [multi-word component] (broader than above — catches "impl the semantic cache with...")
    # Excludes "why did we implement" (retrospective decision — NPU)
    (
        re.compile(r"\bimplement (the |a |an )\w+\s+\w+\b.{5,}", re.I),
        0.82,
        "implement multi-word component",
    ),
    # "implement the feature/fix/change/solution" — single-word object (feature, fix, etc.)
    # Also: "implement one/it/them" — anaphoric reference after prior context
    (
        re.compile(
            r"\bimplement\s+(?:(?:the|a|an|this)\s+(?:feature|fix|change|solution|logic|idea|concept|requirement|improvement|enhancement|refactor|optimization|integration|endpoint|service|check|guard|hook)|(?:one|it|them|this|that)\b)",
            re.I,
        ),
        0.85,
        "implement the feature/fix",
    ),
    # "implement sorting/caching/searching/batching/anonymization/etc" — algorithm/operation as direct object
    (
        re.compile(
            r"\bimplement\s+(?:the\s+|a\s+|an\s+)?(?:[\w-]+\s+){0,3}(?:sort(?:ing)?|search(?:ing)?|cach(?:e|ing)|hash(?:ing)?|batch(?:ing)?|rout(?:e|ing)|queu(?:e|ing)|stack(?:ing)?|heap|tree|graph|shard(?:ing)?|auto.shard(?:ing)?|auto.scal(?:e|ing)?|index(?:ing)?|filter(?:ing)?|compres(?:s|sion)|encod(?:e|ing)|anon(?:ymiz(?:e|ation)|ymisation)?|encrypt(?:ion)?|decrypt(?:ion)?|authenticat(?:e|ion)|authoriz(?:e|ation)|paginat(?:e|ion)|throttl(?:e|ing)|algorithm|protocol|webhook|recogni(?:tion|ze)|summariz(?:ation|ing|e)|classif(?:ication|y)|translat(?:ion|e)|detect(?:ion)?|extract(?:ion)?|pars(?:ing|e)|tagg(?:ing)?|segment(?:ation)?|cluster(?:ing)?|embed(?:ding)?|ota\s+(?:update|firmware)|firmware\s+update|isr|interrupt|persistence|notification\s+handling|push\s+notification|sync(?:hronization)?)\b",
            re.I,
        ),
        0.85,
        "implement algorithm/operation",
    ),
    # "implement JWT/OAuth/CSRF/GDPR/etc." — tech acronym/standard without article
    (
        re.compile(
            r"\bimplement\s+(?:jwt|oauth|oauth2|saml|ldap|ssl|tls|grpc|websocket|webhook|oidc|sso|csrf|xss|gdpr|ccpa|rbac|acl|2fa|mfa|otp|token\s+refresh|token\s+rotation|session\s+invalidation|rate\s+limiting|crud|crud\s+(?:endpoints|operations|api)|graphql\s+(?:mutations?|queries|subscriptions)|api\s+versioning|backward\s+compatibility)\b",
            re.I,
        ),
        0.88,
        "implement tech protocol",
    ),
    # "Define the [schema/interface/contract/spec]" — formal definition tasks
    (
        re.compile(
            r"\b(define|specify|declare)\s+(?:the\s+|a\s+|an\s+)?(?:[\w-]+\s+)?(schema|interface|contract|spec|protocol|model|type|enum|struct|protobuf|api\s+spec|openapi)\b",
            re.I,
        ),
        0.85,
        "define schema/interface",
    ),
    # Security analysis verbs — identify, analyze, assess, scan, detect (with security context)
    (
        re.compile(
            r"\b(identify|analyze|assess|scan|detect|investigate)\b.{0,30}\b(vuln(?:erabilit(?:y|ies))?|attack\s+vector|security\s+issue|weakness|exploit|injection|xss|csrf|threat|limitations?|gaps?|biases?|issues?|inconsistenc(?:y|ies)|findings?|root\s+cause|cause|spike|regression|bottleneck|anomaly|incident)\b",
            re.I,
        ),
        0.85,
        "security and analytical task",
    ),
    # "When implementing X" / "While implementing X" — gerund form of implement
    (
        re.compile(r"\b(?:when|while|after|before)\s+implementing\b", re.I),
        0.85,
        "implementing gerund context",
    ),
    # "Deploy/provision/migrate X to/from/on Y" — cloud deployment verbs
    (
        re.compile(
            r"\b(?:deploy|provision|migrate|rollout|release|rollback|revert|redeploy|undeploy|restart)\s+(?:the\s+|a\s+|an\s+|this\s+|last\s+)?\w+",
            re.I,
        ),
        0.85,
        "deploy/provision task",
    ),
    # Cloud/system infrastructure operations — "Set up [service]" / "Implement [cloud ops]"
    (
        re.compile(
            r"\b(?:set\s+up|implement|configure)\s+(?:the\s+|a\s+|an\s+)?(?:[\w-]+\s+)?(?:auto.?scal(?:e|ing)|health\s+checks?|lifecycle|monitoring|alerting|logging|iam\s+role|iam\s+policy|s3\s+bucket|lambda|ec2|cloudwatch|azure\s+ad|gcp|gcr|eks|ecs|fargate|sns|sqs|ssh\s+key|vpn\s+tunnel|vpn|firewall|iptables|cron\s+job|log\s+rotation|systemd|syslog|pagerduty|opsgenie|escalation|on.call|incident|slo|sla|sre)\b",
            re.I,
        ),
        0.85,
        "cloud infrastructure operation",
    ),
    # Test/spec generation — "write a unit test for...", "write tests for..."
    (
        re.compile(
            r"\b(write|create|generate|add)\s+(a |an |the )?(?:[\w-]+\s+)?(unit |integration |regression |end.to.end |smoke |e2e |api |load |performance |acceptance |contract |)test(s?)\b",
            re.I,
        ),
        0.95,
        "test generation",
    ),
    # Document generation with adjective(s) — "draft a technical report", "write a comprehensive detailed proposal"
    # ([\w-]+ )* allows zero or more adjectives (including hyphenated like "non-disclosure") between article and noun
    # Extended nouns: medical (note, diagnosis, assessment), legal (agreement, brief, contract),
    # business (memo, analysis, summary, narrative), security (policy, template, playbook, runbook),
    # content/creative (description, email, post, story, copy, announcement, changelog, letter,
    #   slide, presentation, pitch, newsletter, tweet, thread, caption, bio)
    # academic (review, abstract, hypothesis, findings, conclusion, methodology, literature-review)
    (
        re.compile(
            r"\b(write|create|generate|draft|prepare|compose)\s+(a |an |the )?([\w-]+ )*(essay|report|article|document|proposal|note|diagnosis|assessment|agreement|brief|contract|memo|analysis|summary|narrative|specification|amendment|plan|template|policy|playbook|runbook|guide|handbook|description|email|post|story|stories|copy|announcement|changelog|letter|slide|presentation|pitch|newsletter|thread|caption|bio|blurb|readme|script|storyboard|review|abstract|hypothesis|findings|conclusion|methodology|critique|overview|synopsis|annotation)\b",
            re.I,
        ),
        0.95,
        "document generation with adjective(s)",
    ),
    # Best practices / guidelines / recommendations — requires detailed enumeration
    (
        re.compile(r"\bwhat are (the |some )?(best practices|guidelines|recommendations)\b", re.I),
        0.85,
        "best practices enumeration",
    ),
    # Explain how [mechanism] [does something] — causation explanation
    # .{8,} excludes trivial "Explain how this works" (≤7 chars gap); allows multi-word subjects
    # Matches both third-person singular (works, operates) and infinitive (work, operate)
    (
        re.compile(
            r"\bexplain how\b.{8,}\b(prevents?|enables?|improves?|works?|operates?|handles?|functions?|behaves?)\b",
            re.I | re.S,
        ),
        0.85,
        "explain how mechanism",
    ),
    # How do you [diagnose/fix/solve/debug] — troubleshooting questions
    (
        re.compile(r"\bhow do you (diagnose|debug|fix|solve|troubleshoot|handle)\b", re.I),
        0.85,
        "troubleshooting how-do-you",
    ),
    # "What should I do when/if X" — actionable troubleshooting advice
    # Clause order: action-verb + if/when immediately, then context
    (
        re.compile(
            r"\bwhat should (?:I|we) (do|check|try|investigate|look\s+at)\s+(?:if|when|after|before)\b.{3,}",
            re.I,
        ),
        0.85,
        "what-should-I-do troubleshooting",
    ),
    # Imperative troubleshoot/diagnose — "Troubleshoot slow queries", "Debug the OOM error"
    (
        re.compile(
            r"^(?:troubleshoot|diagnose|debug|investigate)\s+.{5,}",
            re.I,
        ),
        0.85,
        "imperative troubleshoot/debug",
    ),
    # "What happens if/when X" — conditional/failure analysis
    (
        re.compile(r"\bwhat happens\s+(?:if|when|after|before)\b.{5,}", re.I),
        0.85,
        "what-happens-if conditional analysis",
    ),
    # "Explain this regex / SQL / function" — technical artifact explanation
    (
        re.compile(
            r"\bexplain\s+(?:this|the)\s+(?:regex|regexp?|sql|query|function|method|class|code|algorithm|pattern|expression|formula|snippet|line|block|command|statement|loop|condition|assertion|decorator|hook|middleware|schema|migration|config|rule)\b",
            re.I,
        ),
        0.85,
        "explain-this-artifact",
    ),
    # "Should this/the X be async/stateless/cached" — design property decision
    (
        re.compile(
            r"\bshould\s+(?:this|the)\s+(?:\w+\s+){0,3}be\s+(?:async(?:hronous)?|sync(?:hronous)?|cached|lazy|eager|stateful|stateless|idempotent|atomic|transactional|immutable|mutable|concurrent|sequential|blocking|non.blocking|threaded|single.threaded)\b",
            re.I,
        ),
        0.85,
        "should-this-be property decision",
    ),
    # "What should the X be / What is a good/reasonable X" — config/tuning guidance
    (
        re.compile(
            r"\bwhat\s+(?:should\s+(?:the\s+)?(?:\w+\s+){0,3}be\s+(?:set\s+to|configured|set)?|is\s+(?:a\s+)?(?:good|reasonable|appropriate|optimal|recommended|sensible|safe|typical|standard|normal)\b)",
            re.I,
        ),
        0.85,
        "config tuning guidance",
    ),
    # "How many [connections/requests/threads/workers]" — capacity analysis
    (
        re.compile(
            r"\bhow many\s+(?:\w+\s+){0,3}(?:connections?|requests?|threads?|workers?|instances?|retries?|replicas?|shards?|partitions?|nodes?|pods?|tasks?|jobs?|queries?|records?|rows?|entries?)\b",
            re.I,
        ),
        0.85,
        "how-many-capacity analysis",
    ),
    # "How do I [git/dev operation]" — procedural dev operation
    (
        re.compile(
            r"\bhow do (?:I|we)\s+(?:resolve|fix|handle|squash|rebase|merge|cherry.pick|amend|reset|revert|stash|push|pull|deploy|install|upgrade|downgrade|configure|setup|init|clone|fork|tag|release|publish|package|build|run|test|debug|profile|monitor|check|verify|validate|lint|format|generate|scaffold|migrate|rollback|backup|restore)\b",
            re.I,
        ),
        0.85,
        "how-do-I procedural dev op",
    ),
    # "Give me an example / Show me how" — code demonstration request
    (
        re.compile(
            r"\b(?:give\s+me|show\s+me)\s+(?:an?\s+)?(?:example|demo|sample|snippet|usage|use\s+case|how\s+to\s+use|how\s+this\s+works?)\b",
            re.I,
        ),
        0.85,
        "give-me-example demonstration",
    ),
    # "What [type/interface/version/dependencies] should this" — type/dependency guidance
    (
        re.compile(
            r"\bwhat\s+(?:type|interface|class|signature|return\s+type|version|dependency|dependencies|package|library|module)\s+(?:should|does|do)\s+(?:this|I|we)\b",
            re.I,
        ),
        0.85,
        "what-type/dependency-should guidance",
    ),
    # "What is the [memory/latency/cost/performance] of/here" — performance metric question
    (
        re.compile(
            r"\bwhat\s+is\s+(?:the\s+)?(?:memory\s+(?:usage|footprint|cost)|latency|throughput|cpu\s+usage|time\s+complexity|space\s+complexity|cost|overhead|performance|bottleneck)\s+(?:of|for|here|in\s+this)\b",
            re.I,
        ),
        0.85,
        "performance-metric question",
    ),
    # "How expensive/fast/slow is this" — performance evaluation
    (
        re.compile(
            r"\bhow\s+(?:expensive|fast|slow|efficient|inefficient|costly|cheap)\s+is\s+(?:this|the)\b",
            re.I,
        ),
        0.85,
        "how-expensive performance question",
    ),
    # "What exceptions/errors/cases should I handle/catch" — error handling design
    (
        re.compile(
            r"\bwhat\s+(?:exceptions?|errors?|cases?|scenarios?|edge\s+cases?)\s+should\s+(?:I|we)\s+(?:catch|handle|cover|test|consider|account\s+for|be\s+aware\s+of)\b",
            re.I,
        ),
        0.85,
        "what-exceptions-to-handle",
    ),
    # "What are the alternatives to X" / "What is a reasonable X strategy" — design alternatives
    (
        re.compile(
            r"\bwhat\s+(?:are\s+(?:the\s+)?alternatives?\s+to\b|is\s+(?:a\s+)?(?:good|reasonable|appropriate|recommended)\s+\w+\s+(?:strategy|approach|policy|configuration|setting|value|threshold|limit|size|interval|timeout|ttl)\b)",
            re.I,
        ),
        0.85,
        "design alternatives/configuration",
    ),
    # "Is there a [race condition/memory leak/bottleneck/bug]" — diagnostic code question
    (
        re.compile(
            r"\bis there\s+(?:a\s+|an\s+)?(?:potential\s+|possible\s+|any\s+)?(?:race\s+condition|memory\s+leak|bottleneck|deadlock|bug|security\s+(?:issue|vulnerability|flaw)|performance\s+(?:issue|problem)|data\s+race|infinite\s+loop|null\s+pointer|off.by.one|buffer\s+overflow|sql\s+injection)\b",
            re.I,
        ),
        0.85,
        "diagnostic code issue question",
    ),
    # "Is there a better way / approach / alternative" — improvement question
    (
        re.compile(
            r"\bis\s+there\s+(?:a\s+|an\s+)?better\s+(?:way|approach|solution|alternative|method|pattern|design)\b",
            re.I,
        ),
        0.85,
        "is-there-a-better-way",
    ),
    # "Is this [thread-safe/optimized/O(n)/following DRY]" — code review property check
    # Note: O\( without \b — unicode superscripts (²) are \w so \b fails after n
    (
        re.compile(
            r"\bis\s+this\s+(?:\w+\s+){0,3}(?:thread.safe|type.safe|null.safe|idempotent|optimized|efficient|scalable|secure|concurrent.safe|following|following\s+the|O\(|idiomatic|the\s+right|the\s+correct|the\s+best|appropriate\s+here|an?\s+anti.pattern)",
            re.I,
        ),
        0.85,
        "is-this-code-property",
    ),
    # "Does this follow the [principle/pattern]" — code quality principle check
    (
        re.compile(
            r"\b(?:does|is)\s+this\s+(?:follow|following|comply|adhere|conform)\b",
            re.I,
        ),
        0.85,
        "code-principle-check",
    ),
    # "Can this be [parallelized/optimized/cached/...]" — code capability question
    (
        re.compile(
            r"\bcan\s+this\s+be\s+(?:parallelized|optimized|vectorized|cached|memoized|batched|streamed|distributed|shared|reused|simplified|generalized|abstracted|tested|mocked|inlined|refactored)\b",
            re.I,
        ),
        0.85,
        "can-this-be code question",
    ),
    # "Will/Can this scale/handle/work/perform" — scalability analysis
    (
        re.compile(
            r"\b(?:will|can)\s+this\s+(?:scale|handle|work|perform|run|support)\b.{5,}",
            re.I,
        ),
        0.85,
        "scalability analysis question",
    ),
    # "What should I test / Am I missing test cases" — test coverage question
    (
        re.compile(
            r"\b(?:what\s+should\s+(?:I|we)\s+test|am\s+I\s+missing\s+(?:any\s+)?test|what\s+test\s+cases?\s+(?:am\s+I\s+missing|should\s+I\s+add))\b",
            re.I,
        ),
        0.85,
        "test coverage question",
    ),
    # "What is the bottleneck / What do I need" — GPU-appropriate what-is questions
    (
        re.compile(
            r"\bwhat\s+(?:is\s+(?:the\s+)?(?:bottleneck|root\s+cause|issue|problem|bug)\s+(?:here|in\s+this)|do\s+(?:I|we)\s+need\s+(?:to\s+)?\w+|environment\s+variables?|(?:env|config)\s+vars?)\b",
            re.I,
        ),
        0.85,
        "what-is-the-bottleneck/need",
    ),
    # "What is wrong / what could be causing / what caused X to fail / what does this mean" — analysis
    (
        re.compile(
            r"\bwhat (is|are|could be|might be|would be|caused|does\s+this|does\s+the)\s+(?:wrong|causing|the\s+(?:cause|reason|issue|problem|bug|error)|(?:stack\s+trace|error|warning|exception|traceback|output)(?:\s+mean)?|mean\b)"
            r"|\bwhat (caused|triggered|broke|made|led\s+to)\b.{3,40}\b(?:fail(?:ure|ing)?|break|crash|stop|hang|slow\s+down|return|throw|spike|surge|drop|leak|error|timeout|regression|degradation)\b",
            re.I,
        ),
        0.85,
        "root-cause analysis question",
    ),
    # "Explain the difference between X and Y" — comparative explanation
    (
        re.compile(
            r"\bexplain (the )?(difference|distinction|trade-?offs?|pros and cons|advantages|disadvantages)\b",
            re.I,
        ),
        0.88,
        "explain difference/tradeoffs",
    ),
    # "How does X work/produce/prevent" — mechanism explanation (does ≠ imperative do)
    # {2,4} word subject prevents FP on trivial "How does this work?" (1-word subject)
    # Extended: technical process verbs + causation verbs (prevent/enable/improve/allow)
    (
        re.compile(
            r"\bhow does?\s+(?:\w+\s+){2,4}(work|function|operate|behave|handle|produce|generate|compute|calculate|determine|decide|select|route|detect|process|return|prevent|enable|improve|allow|enforce|guarantee|ensure|coordinate|synchronize|learn|train|adapt|converge|update|propagate|scale|balance|distribute|replicate|partition|shard|index|cache|serialize|deserialize)\b",
            re.I,
        ),
        0.85,
        "how does X work",
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
    # "Can you [action verb]" — multi-step task requests
    # Extended with explain/analyze/review/check for indirect GPU questions
    (
        re.compile(
            r"\bcan you (resume|manage|orchestrate|handle|coordinate|configure|implement|create|build|explain|analyze|review|check|diagnose|debug|optimize|refactor)\b",
            re.I,
        ),
        0.85,
        "can-you-action-request",
    ),
    # "How to run / execute / set up [task]" — procedural execution
    (
        re.compile(r"\bhow to (run|execute|start|launch|trigger|perform|conduct)\b", re.I),
        0.85,
        "how-to-run-execute",
    ),
    # "Implement the [adjective(s)]* policy/strategy/approach/pipeline"
    # Uses .{0,40} to skip over hyphenated compound adjectives like "multi-tier"
    (
        re.compile(
            r"\bimplement (the |a |an ).{0,40}\b(policy|strategy|approach|mechanism|framework|workflow)\b",
            re.I,
        ),
        0.85,
        "implement policy/strategy",
    ),
    # "Write a [adj]* test suite" — broader test generation
    (
        re.compile(
            r"\b(write|create|generate|compile|build)\s+(a |an |the )?(?:[\w-]+\s+)*(test suite|test set|test harness|test framework|test battery)\b",
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
    # Extended with structural ops: split/move/remove/delete/decouple/decompose
    # "review" excluded — too ambiguous. Use code-review pattern below.
    (
        re.compile(
            r"\b(refactor|optimize|profile|debug|audit|trace|rewrite|rework|improve|translate|adapt|summarize|critique|formulate|interpret|hypothesize|split|move|remove|delete|decouple|decompose|consolidate|migrate|merge|inline|flatten|hoist)\b.{0,30}\b(the|a|an|this|it|these|those)\b",
            re.I,
        ),
        0.85,
        "engineering task verb",
    ),
    # Code review — "review" only when paired with code-specific nouns
    (
        re.compile(
            r"\breview\b.{0,30}\b(code|implementation|pull\s+request|pr\b|changes|diff|api|module|test|function|class|endpoint|service)\b",
            re.I,
        ),
        0.85,
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
        0.85,
        "comparative evaluation",
    ),
    # "Test the [X] with various [Y] configurations" — test design requiring analysis
    (
        re.compile(
            r"\btest (the |a |an )\w+.{0,30}\b(configurations?|scenarios?|cases?|fixture|input)\b",
            re.I,
        ),
        0.85,
        "test with various configurations",
    ),
    # ML/training task verbs — fine-tune, train, finetune (expanded targets including model names)
    (
        re.compile(
            r"\b(fine-tune|finetune|train|retrain|fine tune)\b.{0,40}\b(model|network|classifier|detector|adapter|checkpoint|weights|embeddings|backbone|encoder|bert|gpt|llama|gemma|mistral|falcon|claude|palm|t5|roberta|deberta|electra|xlnet|bloom)\b",
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
        0.85,
        "system integration task",
    ),
    # Wire X into Y (without "up") — service wiring
    (
        re.compile(
            r"\bwire\s+(?:the\s+)?\w+(?:\s+\w+)?\s+(?:service|module|component|layer|system)\b",
            re.I,
        ),
        0.85,
        "service wiring task",
    ),
    # "Why is/are [X] [doing/returning/failing/scoring]" — specific debugging verbs
    # Also covers noun-form degradation/drop (e.g. "throughput degradation", "hit rate drop")
    # and trend verbs (increasing/decreasing) for performance investigation questions
    # Also: "why am I getting/seeing" first-person error form
    (
        re.compile(
            r"\bwhy (is|are|am|does|did|isn't|aren't|am\s+not|doesn't|didn't)\b.{0,60}\b(returning|fail(ing)?|scoring|not|error|broken|wrong|zero|null|empty|opening|dropping|crashing|slow|leaking|growing|blocking|hanging?|stuck|exhausting|falling|rising|spiking|timing\s+out|degrading|degradation|throwing|breaking|oscillating|converging|diverging|saturating|plateauing|drop(?:\s+below)?|declin(?:e|ing)|decreas(?:e|ing)|increas(?:e|ing)|persisting?|getting|seeing|experiencing|having)\b",
            re.I,
        ),
        0.85,
        "debugging why-question",
    ),
    # Long "why" question (≥42 chars) — complex system behavior investigation
    (
        re.compile(r"\bwhy\s+(?:does|is|are|did|doesn't|isn't|aren't|didn't)\b.{42,}", re.I),
        0.82,
        "long debugging why-question",
    ),
    # "Generate the [adjective*] [config/JSON/YAML/entry/file] for [X]" — config generation
    (
        re.compile(
            r"\bgenerate (the |a |an |this )(?:\w+ )*(config|configuration|settings|json|yaml|entry|file|manifest|schema)\b",
            re.I,
        ),
        0.85,
        "configuration generation",
    ),
    # IaC/infra tool generation — nginx, k8s, terraform, docker, helm config files
    (
        re.compile(
            r"\b(generate|create|produce|write|build)\s+(?:the\s+|a\s+|an\s+)?(?:nginx|kubernetes|k8s|terraform|helm|docker|dockerfile|ansible|puppet|grafana|prometheus|github\s+actions?|ci/cd|gitlab\s+ci|migrations?)\b",
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
            r"\bimplement\b.{0,40}\bin\s+(python|java|c\+\+|cpp|javascript|typescript|go\b|rust|kotlin|swift|scala|ruby|haskell|erlang|elixir|clojure|ocaml|f#|lua|r\b|matlab|dart|zig|nim|crystal|julia|groovy|perl|bash|shell|powershell)(?:\W|$)",
            re.I,
        ),
        0.88,
        "implement in language",
    ),
    # Create/build a [adjective(s)] endpoint/service/server/cache/pipeline/queue
    (
        re.compile(
            r"\b(create|build|add)\s+(?:a\s+)?(?:[\w-]+\s+){0,3}(endpoint|service|server\b|api\b|cache|pipeline|queue|handler|middleware|dashboard|visualization|report|portal|agent|bot|workflow|framework|harness|scaffold|index\b|view\b|trigger\b|constraint|migration|role\b|policy|lifecycle|bucket|cluster|repository|registry)\b",
            re.I,
        ),
        0.85,
        "build service or endpoint",
    ),
    # "Configure [tech/service]" as an imperative — NOT part of "How to configure X?" question
    # Requires configure to be at start of prompt or after sentence-ending punctuation
    (
        re.compile(
            r"(?:^|[.!;]\s+)configure\s+(?:the\s+|a\s+|this\s+)?(?:redis|rabbitmq|kafka|nginx|postgresql|mysql|mongodb|elasticsearch|grafana|prometheus|vault|consul|ssl|tls|https?|ldap|smtp|dns|iptables|sshd?|vpn|openvpn|wireguard|fail2ban|ufw|nfs|samba|waf|rate\s+limit|load\s+balanc|circuit\s+breaker|cdn|adc|dac|uart|spi\b|i2c\b|gpio|pwm|timer|hal|freertos|rtos|mqtt|zigbee|bluetooth|wifi)\b",
            re.I | re.M,
        ),
        0.85,
        "configure tech service",
    ),
    # "Perform [data analysis/EDA/audit/assessment]" — analysis execution verb
    (
        re.compile(
            r"\bperform\s+(?:a\s+|an\s+|the\s+)?(?:[\w-]+\s+){0,3}(?:analysis|audit|assessment|evaluation|benchmarking|profiling|eda|testing|migration|review)\b",
            re.I,
        ),
        0.85,
        "perform analysis task",
    ),
    # "Add X to the [adjective] [function/class/module/code/system]" — code modification
    (
        re.compile(
            r"\badd\s+(?:[\w-]+\s+){0,4}(?:to\s+(?:the\s+|a\s+|this\s+)?(?:[\w-]+\s+){0,2})(function|class|method|module|code|system|service|api|handler|test|endpoint)\b",
            re.I,
        ),
        0.85,
        "add to code artifact",
    ),
    # "Add documentation/logging/monitoring/metrics to X" — observability additions
    (
        re.compile(
            r"\badd\s+(?:[\w/.-]+\s+)*(documentation|logging|monitoring|metrics|tracing|observability|telemetry|swagger|openapi)\s+(?:to|for)\b",
            re.I,
        ),
        0.85,
        "add observability/docs",
    ),
    # "Add X support/feature/type-hints" — direct feature addition without "to [artifact]"
    (
        re.compile(
            r"\badd\s+(?:[\w-]+\s+){0,3}(?:support|feature|functionality|capability|handling|hints?\b|annotations?\b|docstrings?\b|validation|caching|pagination|retry(?:\s+logic)?|timeout|types?\b|generics?|overloads?)\b",
            re.I,
        ),
        0.85,
        "add feature directly",
    ),
    # "Fix the [bug/issue] in X" OR "Fix it/them/this" — code fix commands
    (
        re.compile(
            r"\bfix\s+(?:(?:the\s+)?(?:bug|issue|error|problem|crash|failure|regression)\b.{0,30}\b(?:in|with|at|for)\b|(?:it|them|this|that)\b)",
            re.I,
        ),
        0.85,
        "fix bug in code",
    ),
    # "Set up / Enable / Activate [infra/config]" — imperative config tasks
    (
        re.compile(
            r"\b(?:set\s+up|enable|activate|turn\s+on)\s+(?:a\s+|an\s+|the\s+)?(?:[\w-]+\s+){0,2}(?:rate\s+limit(?:ing)?|connection\s+pool(?:ing)?|load\s+balanc(?:er|ing)?|circuit\s+breaker|cache(?:\s+invalidation)?|health\s+check(?:s|ing)?|retry(?:\s+logic)?|timeout|failover|caching|tracing|monitoring|logging|rate\s+limiting|auth(?:entication|orization)?|ssl|tls|compression|pagination|webhook|event\s+streaming)\b",
            re.I,
        ),
        0.85,
        "imperative enable/setup config",
    ),
    # "Does/Would/Could this [code/impl] [look correct/cause issue/introduce bug]" — code review impact
    (
        re.compile(
            r"\b(?:does|would|could|might)\s+this\s+(?:\w+\s+){0,3}(?:look\s+(?:correct|right|good|ok)|cause\s+(?:a\s+)?(?:performance|memory|security|concurrency)\s+(?:issue|problem|leak|race|bug)|introduce\s+(?:a\s+)?(?:\w+\s+)?(?:bug|regression|issue|vulnerability|race|leak|bottleneck|deadlock|conflict|error))\b",
            re.I,
        ),
        0.85,
        "code review impact question",
    ),
    # "Help me [debug/understand/analyze]" — guided debugging/analysis
    (
        re.compile(
            r"\bhelp\s+me\s+(?:debug|understand|analyze|analyse|investigate|figure\s+out|interpret|diagnose|fix|optimize|review)\b",
            re.I,
        ),
        0.85,
        "help me debug/analyze",
    ),
    # Security vulnerability questions — "Is this vulnerable to X" / "Are there any vulnerabilities"
    (
        re.compile(
            r"\b(?:vulnerable\s+to|vulnerability|xss|csrf|sql\s+injection|injection\s+(?:attack|vulnerability)|security\s+(?:flaw|hole|gap|risk))\b",
            re.I,
        ),
        0.85,
        "security vulnerability question",
    ),
    # Short imperative code operations: scaffold/stub/mock + transformation verbs
    # Extended with code-transformation verbs: port/convert/wrap/extract/rename/benchmark/etc.
    (
        re.compile(
            r"\b(scaffold|stub\s+out?|mock|process|handle|extend|simplify|dockerize|containerize|serialize|paginate|port|convert|wrap|extract|rename|inline|flatten|normalize|canonicalize|benchmark)\s+(?:the\s+|a\s+|an\s+|this\s+)?(?:[\w-]+\s+){0,3}\w+\b",
            re.I,
        ),
        0.85,
        "short imperative code op",
    ),
    # "Make [the/a] X more/less [readable/efficient/testable/...] — code quality improvement
    # {0,3} allows multi-word subjects like "Make the task classifier more readable"
    (
        re.compile(
            r"\bmake\s+(?:the\s+|a\s+|this\s+)?(?:[\w-]+\s+){0,3}(?:more\s+|less\s+)?(?:readable|efficient|testable|maintainable|performant|scalable|clean|modular|robust|reusable|thread.safe|async(?:hronous)?|synchronous|idempotent|stateless|observable|resilient|fault.tolerant|clear(?:er)?|simple(?:r)?|fast(?:er)?|small(?:er)?|concise(?:r)?|Pythonic|idiomatic|elegant|type.safe|functional|declarative|composable)\b",
            re.I,
        ),
        0.85,
        "make-code-quality",
    ),
    # "Update the [artifact] to [action]" — code update task
    # Expanded noun list covers specialist nouns (classifier, orchestrator, suite, etc.)
    (
        re.compile(
            r"\bupdate\s+(?:the\s+)?(?:[\w-]+\s+){0,2}(tests?|suite|function|class|method|module|code|schema|config|service|api|endpoint|classifier|router|orchestrator|pipeline|handler|adapter|registry|scheduler|processor|harness|agent|worker|workflow)\s+to\b",
            re.I,
        ),
        0.85,
        "update code artifact",
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
        0.85,
        "run-and-report task",
    ),
    # "Run [tool] experiment/tracking" — ML experiment management
    (
        re.compile(
            r"\brun\s+(?:the\s+)?\w+\s+(?:experiment|tracking|benchmark|evaluation|ablation)\b",
            re.I,
        ),
        0.85,
        "ml experiment run",
    ),
    # Derive/calculate without explicit "step" — complex mathematical operations
    (
        re.compile(
            r"\b(derive|calculate|compute) (the |a |an )(\w+ )*(matrix|transform|projection|distribution|gradient|kernel|embedding|decomposition|eigendecomposition|eigenvalue|jacobian|hessian|integral|derivative|divergence|entropy|covariance|correlation)\b",
            re.I,
        ),
        0.88,
        "derive/calculate complex math",
    ),
    # "Prove that X" / "Prove X is/holds/satisfies" — mathematical proof
    (
        re.compile(r"\bprove\s+(?:that\b|the\b|\w+\s+is\b|\w+\s+holds\b|\w+\s+satisfies\b)", re.I),
        0.88,
        "mathematical proof",
    ),
    # "Show the derivation/proof/calculation" — derivation tasks
    (
        re.compile(
            r"\bshow\s+(?:the\s+|a\s+)?(?:derivation|proof|calculation|working|steps)\b", re.I
        ),
        0.85,
        "show derivation task",
    ),
    # "Solve [equation/ODE/PDE/system/optimization problem]" — problem solving
    (
        re.compile(
            r"\bsolve\s+(?:the\s+|this\s+)?(?:differential|linear|quadratic|cubic|optimization|eigenvalue|integral|system)\b",
            re.I,
        ),
        0.88,
        "mathematical problem solving",
    ),
    # "Find the optimal/minimum/maximum/critical X [Y] using Z" — optimization
    (
        re.compile(
            r"\bfind\s+(?:the\s+)?(?:optimal|minimum|maximum|critical|saddle|fixed)\s+(?:\w+\s+){1,3}(?:using|with|by|via)\b",
            re.I,
        ),
        0.85,
        "find-optimal task",
    ),
    # "Calculate X for N [units/calls/queries]" — quantitative calculation
    (
        re.compile(
            r"\bcalculate\s+(?:the\s+)?(?:\w+\s+){1,3}(?:for|with|given|across|over)\s+",
            re.I,
        ),
        0.85,
        "calculate-for quantitative task",
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
        0.85,
        "comparative or analytical task",
    ),
    # "Compare X vs Y" / "Compare X versus Y" — direct comparison without "the"
    (
        re.compile(r"\bcompare\s+\w+\s+(?:vs\.?|versus)\b", re.I),
        0.85,
        "direct A-vs-B comparison",
    ),
    # Walk-through / describe full lifecycle
    (
        re.compile(
            r"\b(walk\s+(?:me\s+)?through|describe\s+the\s+(full|complete|entire|detailed))\b", re.I
        ),
        0.85,
        "walk-through or full description",
    ),
    # "Plan how to [migrate/build/redesign]" — architectural planning
    (
        re.compile(r"\bplan\s+how\s+to\b", re.I),
        0.85,
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
        0.85,
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

# Brevity-qualified summarize/critique/interpret: "Summarize X in one paragraph" → short answer (NPU)
# Also: "Briefly summarize/critique/interpret X" → NPU
# Also: "In one sentence, summarize X" (leading brevity qualifier) → NPU
# Without brevity qualifier: "Summarize the contributions of BERT" → GPU
_BREVITY_SUMMARIZE_PATTERN = re.compile(
    r"(?:\bbriefly\s+(?:summarize|critique|interpret|formulate|explain)\b)|"
    r"(?:\bsummariz(?:e|ing)\b.{0,80}\b(?:in\s+(?:one|two|three|a\s+single)\s+(?:sentence|paragraph|bullet|word|line)|in\s+brief)\b)|"
    r"(?:^in\s+(?:one|two|three|a\s+single)\s+(?:sentence|paragraph|word|line)[,.]?\s+(?:summarize|explain|describe|state|tell|give)\b)",
    re.I | re.S,
)


def classify(prompt: str) -> RouteDecision:
    """Classify a prompt and return routing decision. Zero model calls."""
    # Truncate very long prompts — classifier only needs the opening intent phrase
    # Prevents O(n²) backtracking on adversarial 1000+ char inputs
    if len(prompt) > 500:
        prompt = prompt[:500]
    prompt_len = len(prompt)

    # ── Pre-GPU overrides (fire before GPU patterns) ─────────────────────────
    # -1. Explicit categorical instruction — always overrides ANY GPU signals
    # "Reply with one word only" / "True or false only" must win over "implement this:..."
    for cat_pat, cat_conf, cat_reason in _CATEGORICAL_PATTERNS[
        :6
    ]:  # only highest-conf categorical patterns
        if cat_pat.search(prompt):
            node, gate = _TYPE_CONFIG["short_categorical"]
            return RouteDecision(
                node=node,
                output_type="short_categorical",
                quality_gate_chars=gate,
                confidence=cat_conf,
                reason=f"categorical override: {cat_reason}",
            )

    # 0. Brevity-qualified summarize: "Summarize X in one paragraph" → NPU
    # Without brevity qualifier, "summarize" → GPU (see engineering task verb pattern)
    if _BREVITY_SUMMARIZE_PATTERN.search(prompt):
        node, gate = _TYPE_CONFIG["short_answer"]
        return RouteDecision(
            node=node,
            output_type="short_answer",
            quality_gate_chars=gate,
            confidence=0.85,
            reason="brevity-qualified summarize",
        )

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
