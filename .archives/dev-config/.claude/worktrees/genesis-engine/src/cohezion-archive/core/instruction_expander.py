"""Instruction expander: maps PRIME skill instructions to executable plan steps.

Parses each instruction line from a :class:`SkillSpec` and classifies it into
one of five operation types (search, generate, analyze, transform, persist)
using keyword matching. The result is an :class:`ExecutablePlan` that can be
fed to :class:`PlanExecutor` for sequential execution.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from cohezion.core.template_engine import SkillSpec


logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """A single executable step within a plan.

    Attributes
    ----------
    operation : str
        One of ``"search"``, ``"generate"``, ``"analyze"``,
        ``"transform"``, ``"persist"``.
    params : dict[str, Any]
        Operation-specific parameters extracted from the instruction.
    description : str
        Original instruction text.
    """

    operation: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ExecutablePlan:
    """An ordered sequence of plan steps derived from a PRIME skill.

    Attributes
    ----------
    skill_name : str
        Name of the source PRIME skill.
    steps : list[PlanStep]
        Ordered steps to execute.
    domain : str
        Domain expertise context from the skill.
    """

    skill_name: str
    steps: list[PlanStep] = field(default_factory=list)
    domain: str = ""


# Maps operation types to their keyword triggers (lowercase).
OPERATION_KEYWORDS: dict[str, list[str]] = {
    "search": [
        "search",
        "find",
        "locate",
        "discover",
        "identify",
        "scan",
        "lookup",
        "query",
        "check",
        "consult",
    ],
    "generate": [
        "generate",
        "create",
        "write",
        "compose",
        "draft",
        "produce",
        "build",
        "implement",
        "seed",
    ],
    "analyze": [
        "analyze",
        "evaluate",
        "assess",
        "examine",
        "review",
        "inspect",
        "verify",
        "validate",
        "test",
    ],
    "transform": [
        "transform",
        "convert",
        "format",
        "extract",
        "parse",
        "map",
        "offload",
        "route",
        "update",
        "increment",
    ],
    "persist": [
        "store",
        "save",
        "persist",
        "record",
        "log",
        "archive",
        "walkthrough",
        "provide",
    ],
}

# Pre-compile word-boundary patterns for each keyword.
_KEYWORD_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    op: [re.compile(rf"\b{kw}\b", re.IGNORECASE) for kw in keywords] for op, keywords in OPERATION_KEYWORDS.items()
}


def _classify_instruction(text: str) -> str:
    """Classify an instruction string into an operation type.

    Parameters
    ----------
    text : str
        The instruction text to classify.

    Returns
    -------
    str
        The best-matching operation type, or ``"generate"`` as default.
    """
    scores: dict[str, int] = dict.fromkeys(OPERATION_KEYWORDS, 0)
    lower = text.lower()

    for op, patterns in _KEYWORD_PATTERNS.items():
        for pat in patterns:
            if pat.search(lower):
                scores[op] += 1

    best_op = max(scores, key=lambda k: scores[k])
    if scores[best_op] == 0:
        return "generate"
    return best_op


def _extract_params(text: str, operation: str) -> dict[str, Any]:
    """Extract operation-specific parameters from instruction text.

    Parameters
    ----------
    text : str
        Instruction text.
    operation : str
        Classified operation type.

    Returns
    -------
    dict[str, Any]
        Extracted parameters.
    """
    params: dict[str, Any] = {}

    # Extract backtick-quoted identifiers as targets
    backtick_refs = re.findall(r"`([^`]+)`", text)
    if backtick_refs:
        params["references"] = backtick_refs

    # Extract bold-quoted terms as key concepts
    bold_refs = re.findall(r"\*\*([^*]+)\*\*", text)
    if bold_refs:
        params["concepts"] = bold_refs

    # Operation-specific extraction
    if operation == "search":
        params["search_type"] = "capability"
    elif operation == "persist":
        params["persist_type"] = "log"

    return params


class InstructionExpander:
    """Expand PRIME skill instructions into an executable plan.

    Each instruction from a :class:`SkillSpec` is classified by keyword
    matching and turned into a :class:`PlanStep`.
    """

    def expand(self, spec: SkillSpec) -> ExecutablePlan:
        """Expand a skill specification into an executable plan.

        Parameters
        ----------
        spec : SkillSpec
            Parsed PRIME skill specification.

        Returns
        -------
        ExecutablePlan
            Plan with ordered steps ready for execution.
        """
        steps: list[PlanStep] = []

        for instruction in spec.instructions:
            operation = _classify_instruction(instruction)
            params = _extract_params(instruction, operation)
            step = PlanStep(
                operation=operation,
                params=params,
                description=instruction,
            )
            steps.append(step)

        plan = ExecutablePlan(
            skill_name=spec.name,
            steps=steps,
            domain=spec.domain_expertise,
        )

        logger.info(
            "Expanded %s: %d instructions -> %d steps",
            spec.name,
            len(spec.instructions),
            len(steps),
        )
        return plan
