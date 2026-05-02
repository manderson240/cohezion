"""Static vocabulary data for VibeParser — stopwords, operation vocab, complexity signals.

Kept separate to avoid inflating parser.py past the 300-line limit.
"""

from __future__ import annotations

from cohezion.vibe.types import OperationType


# English stopwords to strip from keyword candidates
_SW = "a an the and or but in on at to for of with by from as is it its be"
_SW += " are was were been have has had do does did will would could should"
_SW += " may might shall can not no nor so yet both either neither each every"
_SW += " all any few more most other some such than that their then there"
_SW += " these they this those through under until up very when where which"
_SW += " while who whom why how i we you he she me us him her my our your his"
_SW += " what just also into about only get make use using"
STOPWORDS: frozenset[str] = frozenset(_SW.split())

# Maps vocabulary tokens to OperationType votes
OPERATION_VOCAB: dict[str, OperationType] = {
    # RESEARCH
    "research": OperationType.RESEARCH,
    "study": OperationType.RESEARCH,
    "investigate": OperationType.RESEARCH,
    "explore": OperationType.RESEARCH,
    "survey": OperationType.RESEARCH,
    "review": OperationType.RESEARCH,
    "find": OperationType.RESEARCH,
    "discover": OperationType.RESEARCH,
    "gather": OperationType.RESEARCH,
    "search": OperationType.RESEARCH,
    "look": OperationType.RESEARCH,
    "papers": OperationType.RESEARCH,
    "literature": OperationType.RESEARCH,
    # IMPLEMENT
    "implement": OperationType.IMPLEMENT,
    "build": OperationType.IMPLEMENT,
    "create": OperationType.IMPLEMENT,
    "develop": OperationType.IMPLEMENT,
    "write": OperationType.IMPLEMENT,
    "code": OperationType.IMPLEMENT,
    "program": OperationType.IMPLEMENT,
    "add": OperationType.IMPLEMENT,
    "fix": OperationType.IMPLEMENT,
    "deploy": OperationType.IMPLEMENT,
    "install": OperationType.IMPLEMENT,
    "setup": OperationType.IMPLEMENT,
    # ANALYZE
    "analyze": OperationType.ANALYZE,
    "analyse": OperationType.ANALYZE,
    "evaluate": OperationType.ANALYZE,
    "assess": OperationType.ANALYZE,
    "measure": OperationType.ANALYZE,
    "compare": OperationType.ANALYZE,
    "inspect": OperationType.ANALYZE,
    "examine": OperationType.ANALYZE,
    "diagnose": OperationType.ANALYZE,
    "profile": OperationType.ANALYZE,
    "monitor": OperationType.ANALYZE,
    # TRANSFORM
    "transform": OperationType.TRANSFORM,
    "convert": OperationType.TRANSFORM,
    "translate": OperationType.TRANSFORM,
    "parse": OperationType.TRANSFORM,
    "format": OperationType.TRANSFORM,
    "migrate": OperationType.TRANSFORM,
    "extract": OperationType.TRANSFORM,
    "process": OperationType.TRANSFORM,
    "map": OperationType.TRANSFORM,
    "aggregate": OperationType.TRANSFORM,
    # VALIDATE
    "validate": OperationType.VALIDATE,
    "verify": OperationType.VALIDATE,
    "check": OperationType.VALIDATE,
    "test": OperationType.VALIDATE,
    "confirm": OperationType.VALIDATE,
    "ensure": OperationType.VALIDATE,
    "assert": OperationType.VALIDATE,
    "audit": OperationType.VALIDATE,
    # ORCHESTRATE
    "orchestrate": OperationType.ORCHESTRATE,
    "coordinate": OperationType.ORCHESTRATE,
    "manage": OperationType.ORCHESTRATE,
    "run": OperationType.ORCHESTRATE,
    "execute": OperationType.ORCHESTRATE,
    "schedule": OperationType.ORCHESTRATE,
    "pipeline": OperationType.ORCHESTRATE,
    "workflow": OperationType.ORCHESTRATE,
    "automate": OperationType.ORCHESTRATE,
}

# Phrases that boost complexity estimate
COMPLEXITY_BOOSTERS: list[str] = [
    "and then",
    "then",
    "after",
    "before",
    "finally",
    "also",
    "additionally",
    "multiple",
    "several",
    "many",
    "complex",
    "advanced",
    "full",
    "complete",
    "end-to-end",
    "end to end",
    "production",
    "deploy",
]

# Phrases that reduce complexity estimate
COMPLEXITY_REDUCERS: list[str] = [
    "simple",
    "quick",
    "just",
    "only",
    "single",
    "small",
    "basic",
    "minimal",
]
