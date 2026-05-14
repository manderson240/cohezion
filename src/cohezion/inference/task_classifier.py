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
    (re.compile(r"\breply (?:with )?(yes|no) or (no|yes)\b", re.I), 1.0, "yes/no question"),
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
    # Definitional 1-2 word questions — "What is X?", "What is X Y?" → high-conf NPU
    # Caps at 2 words (compound terms like "buffer overflow", "quantum entanglement")
    # 3+ word what-is questions may require complex explanation → keep at 0.70
    (
        re.compile(r"\bwhat (is|are)\s+(?:a\s+|an\s+|the\s+)?(?:[\w-]+\s+)?[\w-]+\s*\?$", re.I),
        0.78,
        "1-2-term definitional question",
    ),
    (
        re.compile(r"\bwhat does [\w-]+\s+(?:stand for|mean|represent)\b", re.I),
        0.78,
        "acronym or term expansion question",
    ),
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
            r"\b(write|implement|create|generate|build)\s+(a |an |the )?(?:[\w-]+ ){0,3}(?:function|class|script|module|code|program|formula|macro|procedure|query|snippet|lambda|decorator|mixin|interface|getters?|setters?|validators?|serializers?|deserializers?|accessors?|migrations?|fixtures?|resolvers?|middlewares?|driver|routine|handler|client|library|daemon|firmware|plugin|extension|adapter|wrapper|proxy|stub|mock|task\b|job\b|service\b|worker|processor|listener|observer|consumer|producer|publisher|subscriber|widget|screen|fragment|composable|activity\b|viewmodel|repository\b|dao\b|coroutine|category\b|entity\b|component|[\w]*viewcontroller|[\w]*recyclerview|[\w]*tableview|[\w]*collectionview|shader|loop\b|controller\b|renderer|pass\b|pipeline|algorithm|simulation|generator|visualiz(?:er|ation)|importer|exporter|converter|transformer|dispatcher|scheduler|executor|runner|scanner|parser\b|loader|hook\b|contract\b|token\b|wallet|oracle|integration\b|connector|bridge\b|gateway\b|registry\b|factory\b|builder\b|chain\b|circuit\b|calculator\b|analyzer|analyser|simulator\b|model\b|harness\b|profiler|embedder|clusterer|classifier\b|detector\b|extractor|tokenizer|vectorizer|optimizer\b|sampler|trainer|evaluator|scorer|node\b|planner|reasoner)\b",
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
        re.compile(r"\bexplain\b.{5,80}\b(in detail|thoroughly|step.by.step)\b", re.I | re.S),
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
    # "implement the feature/fix/change/solution" — single-word object (feature, fix, etc.)
    # Also: "implement one/it/them" — anaphoric reference after prior context
    (
        re.compile(
            r"\bimplement\s+(?:(?:the|a|an|this)\s+(?:feature|fix|change|solution|logic|idea|concept|requirement|improvement|enhancement|refactor|optimization|integration|endpoint|service|check|guard|hook)|(?:one|it|them|this|that)\b)",
            re.I,
        ),
        0.82,
        "implement the feature/fix",
    ),
    # "implement sorting/caching/searching/alignment/etc" — algorithm/operation as direct object
    (
        re.compile(
            r"\bimplement\s+(?:the\s+|a\s+|an\s+)?(?:[\w-]+\s+){0,3}(?:sort(?:ing)?|search(?:ing)?|cach(?:e|ing)|hash(?:ing)?|batch(?:ing)?|rout(?:e|ing)|queu(?:e|ing)|stack(?:ing)?|heap|tree|graph|shard(?:ing)?|auto.shard(?:ing)?|auto.scal(?:e|ing)?|index(?:ing)?|filter(?:ing)?|compres(?:s|sion)|encod(?:e|ing)|anon(?:ymiz(?:e|ation)|ymisation)?|encrypt(?:ion)?|decrypt(?:ion)?|authenticat(?:e|ion)|authoriz(?:e|ation)|paginat(?:e|ion)|throttl(?:e|ing)|algorithm|protocol|webhook|recogni(?:tion|ze)|summariz(?:ation|ing|e)|classif(?:ication|y)|translat(?:ion|e)|detect(?:ion)?|extract(?:ion)?|pars(?:ing|e)|tagg(?:ing)?|segment(?:ation)?|cluster(?:ing)?|embed(?:ding)?|ota\s+(?:update|firmware)|firmware\s+update|isr|interrupt|persistence|notification\s+handling|push\s+notification|sync(?:hronization)?|align(?:ment)?|assembly|sequenc(?:e|ing)|annot(?:ation|ate)|genotyp(?:e|ing)|variant\s+call(?:ing)?|teleportation|error\s+correction|handshake|consensus|replication|kinematics|dynamics\b|trajectory\s+(?:plan|track|optim)|path\s+planning|pid\s+(?:controller|loop|control)|localization|slam\b|odometry|navigation)\b",
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
        0.80,
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
    # "review" excluded — too ambiguous ("review before meeting" FP). Use code-review pattern below.
    (
        re.compile(
            r"\b(refactor|optimize|profile|debug|audit|trace|rewrite|rework|improve|translate|adapt|summarize|critique|formulate|interpret|hypothesize)\b.{0,30}\b(the|a|an|this|it|these|those)\b",
            re.I,
        ),
        0.82,
        "engineering task verb",
    ),
    # Code/document review — "review" when paired with code artifacts or legal/compliance documents
    (
        re.compile(
            r"\breview\b.{0,30}\b(code|implementation|pull\s+request|pr\b|changes|diff|api|module|test|function|class|endpoint|service|agreement|contract|license|policy|terms|compliance|patent|ip\b|clause|provisions?)\b",
            re.I,
        ),
        0.82,
        "code or legal document review",
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
    # "Implement/Create/Build/Write X in [language/framework]" — language-specific code task
    (
        re.compile(
            r"\b(?:implement|create|build|write)\b.{0,55}\bin\s+(python|java|c\+\+|cpp|javascript|typescript|go|rust|kotlin|swift|scala|ruby|qiskit|pennylane|cirq|braket|pyquil|pytorch|tensorflow|jax)(?:\W|$)",
            re.I,
        ),
        0.88,
        "implement in language",
    ),
    # "X using/with [framework]" — framework-keyed code generation
    (
        re.compile(
            r"\b(?:using|with)\s+(qiskit|pennylane|cirq|braket|pyquil|pytorch|tensorflow|jax|scikit.learn|sklearn|biopython|bioconductor|deseq2|edger|samtools|gatk|bowtie|hisat|star\b|blast\b|llamaindex|langchain|opentelemetry|great.expectations|apache\s+beam|apache\s+flink|debezium|argocd|fluxcd|helm\b|argo\s+rollout|vault\s+(?:secret|sidecar))\b",
            re.I,
        ),
        0.90,
        "using quantum/ML/bio/devops framework",
    ),
    # Create/build a [adjective(s)] endpoint/service/cache/pipeline/queue
    (
        re.compile(
            r"\b(create|build|add)\s+(?:a\s+)?(?:[\w-]+\s+){0,3}(endpoint|service|api\b|cache|pipeline|queue|handler|middleware|dashboard|visualization|report|portal|agent|bot|workflow|framework|harness|scaffold|index\b|view\b|trigger\b|constraint|migration|role\b|policy|lifecycle|bucket|cluster|repository|registry)\b",
            re.I,
        ),
        0.82,
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
        0.82,
        "perform analysis task",
    ),
    # "Add X to the [adjective] [function/class/module/code/system]" — code modification
    (
        re.compile(
            r"\badd\s+(?:[\w-]+\s+){0,4}(?:to\s+(?:the\s+|a\s+|this\s+)?(?:[\w-]+\s+){0,2})(function|class|method|module|code|system|service|api|handler|test|endpoint)\b",
            re.I,
        ),
        0.82,
        "add to code artifact",
    ),
    # "Add documentation/logging/monitoring/metrics to X" — observability additions
    (
        re.compile(
            r"\badd\s+(?:[\w/.-]+\s+)*(documentation|logging|monitoring|metrics|tracing|observability|telemetry|swagger|openapi)\s+(?:to|for)\b",
            re.I,
        ),
        0.82,
        "add observability/docs",
    ),
    # "Fix the [adj] [bug/issue] in/where X" OR "Fix it/them/this" — code fix commands
    # .{0,40} prefix allows adjectives ("routing regression", "critical bug")
    (
        re.compile(
            r"\bfix\s+(?:.{0,40}\b(?:bug|issue|error|problem|crash|failure|regression)\b.{0,60}\b(?:in|with|at|for|where)\b|(?:it|them|this|that)\b)",
            re.I,
        ),
        0.85,
        "fix bug in code",
    ),
    # Short imperative code operations: scaffold/stub/mock/process/handle/extend/simplify/dockerize
    (
        re.compile(
            r"\b(scaffold|stub\s+out?|mock|process|handle|extend|simplify|dockerize|containerize|serialize|paginate)\s+(?:the\s+|a\s+|an\s+|this\s+)?(?:[\w-]+\s+){0,3}\w+\b",
            re.I,
        ),
        0.82,
        "short imperative code op",
    ),
    # "Make [the/a] X more/less [readable/efficient/testable/...] — code quality improvement
    (
        re.compile(
            r"\bmake\s+(?:the\s+|a\s+|this\s+)?(?:[\w-]+\s+)?(?:more\s+|less\s+)?(?:readable|efficient|testable|maintainable|performant|scalable|clean|modular|robust|reusable|thread.safe|async(?:hronous)?|synchronous|idempotent|stateless|observable|resilient|fault.tolerant|clear(?:er)?|simple(?:r)?|fast(?:er)?|small(?:er)?|concise(?:r)?)\b",
            re.I,
        ),
        0.82,
        "make-code-quality",
    ),
    # "Update the [tests/function/class/code/module] to [action]" — code update task
    (
        re.compile(
            r"\bupdate\s+(?:the\s+)?(?:[\w-]+\s+){0,2}(tests?|function|class|method|module|code|schema|config|service|api|endpoint)\s+to\b",
            re.I,
        ),
        0.82,
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
            r"\b(derive|calculate|compute) (the |a |an )(\w+ )*(matrix|transform|projection|distribution|gradient|kernel|embedding|decomposition|eigendecomposition|eigenvalue|jacobian|hessian|integral|derivative|divergence|entropy|covariance|correlation|stabilizer|hamiltonian|eigenstate|wavefunction|density\s+matrix|fidelity|expectation|variance|risk\s+metric|volatility|drawdown|portfolio\s+return|content|usage\s+bias|alignment\s+score|similarity\s+score)\b",
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
            r"\bcalculate\s+(?:the\s+)?(?:[\w()]+\s+){1,8}(?:for|with|given|across|over)\s+",
            re.I,
        ),
        0.82,
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
    # Financial analysis — domain-specific complex nouns requiring multi-step GPU work
    # "VaR / DCF / Black-Scholes / backtesting / Sharpe / Monte Carlo / options pricing"
    (
        re.compile(
            r"\b(?:value\s+at\s+risk|var\s+(?:at|for|of)|discounted\s+cash\s+flow|dcf\s+(?:model|analysis|report)|black.scholes|monte\s+carlo\s+(?:sim|model|analysis)|portfolio\s+optim|sharpe\s+ratio|drawdown\s+anal|backtesting?\s+(?:framework|strategy|for)|momentum\s+(?:trading|strategy)|options?\s+pricing|implied\s+volatility|yield\s+curve|credit\s+default\s+swap|asset\s+allocation\s+model)\b",
            re.I,
        ),
        0.88,
        "financial analysis domain",
    ),
    # Bioinformatics — domain-specific pipelines and tools requiring GPU depth
    # Smith-Waterman / RNA-seq / FASTQ / BLAST / phylogenetic / GATK / primer design
    (
        re.compile(
            r"\b(?:smith.waterman|needleman.wunsch|rna.seq|fastq\s+(?:parser|process|filter|qual)|vcf\s+(?:parser|process|extract|annot)|blast.like|gene\s+regulatory|phylogenetic\s+anal|pcr\s+primer|primer\s+(?:pair|design)|sequence\s+alignment|genome\s+assembl|variant\s+(?:call|annot|filter)|differential\s+expression|de.novo\s+assembl|codon\s+usage|gc\s+content\s+(?:and|calc)|motif\s+(?:find|search|scan))\b",
            re.I,
        ),
        0.88,
        "bioinformatics domain",
    ),
    # Quantum computing — domain-specific algorithms/protocols requiring GPU depth
    # Grover / Shor / VQE / quantum error correction / decoherence / entanglement
    (
        re.compile(
            r"\b(?:grover.s\s+(?:algorithm|search)|shor.s\s+algorithm|quantum\s+(?:fourier\s+transform|error\s+correction|circuit|teleportation|key\s+distribution|anneal|walk|gate\s+synthesis|noise\s+model|decoherence|advantage)|bell\s+state|bloch\s+sphere|qubit\s+(?:circuit|gate|error|fidelity|measurement\s+outcome)|variational\s+quantum|steane\s+code|toffoli|hadamard\s+(?:gate|transform)|qasm|qiskit|pennylane\s+(?:impl|code))\b",
            re.I,
        ),
        0.90,
        "quantum computing domain",
    ),
    # NLP/ML engineering domain — transformers, RAG, embeddings, LLM pipelines
    (
        re.compile(
            r"\b(?:attention\s+mechanism|self.attention\s+layer|multi.head\s+(?:attention|self.attention)|positional\s+encoding|word2vec\s+(?:skip.gram|cbow|training)|rag\s+(?:pipeline|vector|retrieval|database|embed)|retrieval.augmented|document\s+chunk(?:ing)?|llamaindex|langchain|beam\s+search\s+decod|bpe\s+(?:algorithm|tokeniz)|subword\s+(?:segment|tokeniz)|data\s+augment\s+(?:pipeline|nlp)|text\s+classifier\s+(?:fine|bert|transformer)|ner\s+(?:dataset|fine|train))\b",
            re.I,
        ),
        0.90,
        "nlp ml engineering domain",
    ),
    # DevOps/platform engineering domain — GitOps, ArgoCD, OpenTelemetry, cost allocation
    (
        re.compile(
            r"\b(?:gitops\s+workflow|argocd|fluxcd|argo\s+rollout|blue.green\s+deploy|canary\s+deploy|distributed\s+trac(?:ing)?|opentelemetry|open\s+telemetry|cost\s+alloc(?:ation)?\s+tagg(?:ing)?|cost\s+tagg(?:ing)?\s+strategy|vault\s+secret\s+(?:inject|sidecar)|kubernetes\s+hpa|eks\s+(?:cluster|provision|terraform)|terraform\s+module|helm\s+chart|github\s+actions\s+(?:ci|pipeline|workflow)|gitops\s+(?:workflow|argo|flux))\b",
            re.I,
        ),
        0.90,
        "devops platform engineering domain",
    ),
    # Legal/compliance domain — contracts, GDPR, IP, license review
    (
        re.compile(
            r"\b(?:non.disclosure\s+agreement|nda\s+(?:draft|clause|review)|gdpr\s+(?:compli|articl|policy|consent|data\s+subject)|ccpa\s+(?:compli|request)|software\s+license\s+(?:agreement|review|audit)|ip\s+rights?|intellectual\s+property\s+(?:clause|rights?|policy)|license\s+(?:compatibility|compli|audit|review)|terms\s+of\s+service|privacy\s+policy|data\s+process\s+agreement|consent\s+management|rbac\s+(?:gdpr|permission|access)|legal\s+(?:risk|memo|brief)|patentability|open.source\s+license)\b",
            re.I,
        ),
        0.88,
        "legal compliance domain",
    ),
    # Scientific research domain — experimental design, clinical trials, paper writing
    (
        re.compile(
            r"\b(?:experimental\s+(?:protocol|design|methodology|plan)|research\s+hypothesis|null\s+hypothesis|clinical\s+trial\s+(?:design|protocol|phase|plan)|systematic\s+review|meta.analysis|statistical\s+power\s+(?:anal|calc)|sample\s+size\s+calc|randomized\s+controlled\s+trial|rct\s+(?:design|protocol)|methods\s+section|crispr\s+(?:gene|edit|effic)|cortisol\s+response|literature\s+review|research\s+paper|bootstrap\s+resamp|confidence\s+interval\s+(?:calc|bootstrap)|statistical\s+analysis\s+plan|phase\s+(?:i{1,3}|iii?|iv)\s+(?:trial|study|clinical))\b",
            re.I,
        ),
        0.88,
        "scientific research domain",
    ),
    # Data engineering domain — Airflow/Spark/dbt/Kafka/Flink/ETL/CDC pipelines
    # Note: bare nouns (data lakehouse, ETL) are NOT included — need action-verb context
    (
        re.compile(
            r"\b(?:airflow\s+(?:dag|pipeline|task|operator|hook)|dbt\s+(?:model|transform|test|project)|spark\s+(?:stream|job|pipeline|etl|session)|kafka\s+(?:consumer|producer|stream|topic|lag)|flink\s+(?:job|stream|window|operator)|debezium\s+(?:cdc|pipeline)|change\s+data\s+capture|cdc\s+pipeline|delta\s+lake\s+(?:table|schema|pipeline|migration)|apache\s+iceberg\s+(?:table|migration|catalog)|data\s+lakehouse\s+(?:architect|design|implement|migrat)|great\s+expectations\s+(?:check|suite|pipeline|for)|feature\s+store\s+(?:ingestion|pipeline)|feast\s+(?:registry|feature)|etl\s+(?:pipeline|dag|job|process)|data\s+quality\s+check|tumbling\s+window|snowflake\s+(?:schema|sql|model)|star.schema\s+(?:data|warehouse)|data\s+warehouse\s+(?:schema|model)|streaming\s+pipeline|clickstream\s+process)\b",
            re.I,
        ),
        0.90,
        "data engineering domain",
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
# Also: "...? One sentence." terminal brevity qualifier overrides domain GPU signals
# Without brevity qualifier: "Summarize the contributions of BERT" → GPU
_BREVITY_SUMMARIZE_PATTERN = re.compile(
    r"(?:\bbriefly\s+(?:summarize|critique|interpret|formulate|explain)\b)|"
    r"(?:\bsummariz(?:e|ing)\b.{0,80}\b(?:in\s+(?:one|two|three|a\s+single)\s+(?:sentence|paragraph|bullet|word|line)|in\s+brief)\b)|"
    r"(?:[\.\?!]\s+(?:one|a\s+single)\s+sentence\.?\s*$)|"
    r"(?:\bin\s+(?:one|two|three|a\s+single)\s+sentence[,:])",
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
    _CODE_REASON_KEYWORDS = frozenset(
        {"code", "implement", "test", "sql", "iac", "infra", "domain", "framework", "language"}
    )
    for pattern, confidence, reason in _GPU_PATTERNS:
        if pattern.search(prompt):
            is_code = any(kw in reason for kw in _CODE_REASON_KEYWORDS)
            node, gate = _TYPE_CONFIG["code"] if is_code else _TYPE_CONFIG["long_generation"]
            otype = "code" if is_code else "long_generation"
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
