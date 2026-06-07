"""MCP tool-description-poisoning audit (backlog item 76, 2026-06-07).

Research round 14, VERIFIED — MS AI Red Team taxonomy v2.0 "MCP/Plugin Abuse". The net-new gap:
cohezion's MCP bridge exposes tool DESCRIPTIONS with no audit for instruction-injection embedded
in them. A malicious or compromised MCP server can put 'ignore previous instructions', 'you must
always call this', or system-prompt-like directives in a tool's description — which an agent reads
as authoritative when deciding whether/how to call the tool ("tool description poisoning").

`tool_description_audit(tools)` deterministically flags descriptions containing an injection
imperative (with the matched pattern) plus tools missing a description entirely. Report-only,
pure — regex/keyword over the description strings only; no network, no LLM, no writes. The
patterns match the IMPERATIVE form ('always CALL this', 'you MUST invoke') so clean descriptive
text with near-miss words ('always returns', 'you provide') is not false-flagged.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDescriptionFinding:
    """A flagged MCP tool: the tool name + the issue (matched injection pattern, or missing)."""

    tool: str
    issue: str


# Injection-imperative patterns (case-insensitive). Each targets the directive FORM, not a bare
# keyword, to avoid false-positives on legitimate descriptive prose.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:all\s+|the\s+|any\s+)?(?:previous|prior|above|earlier)\b", re.I),
    re.compile(
        r"disregard\s+(?:all\s+|the\s+|your\s+|previous\s+|prior\s+)?"
        r"(?:previous|prior|instructions|above|context|rules)\b",
        re.I,
    ),
    re.compile(
        r"you\s+must\s+(?:always\s+|never\s+|only\s+)?"
        r"(?:call|use|invoke|run|execute|ignore|disregard|reveal)\b",
        re.I,
    ),
    re.compile(r"always\s+(?:call|use|invoke|run|execute)\s+(?:this|the|me)\b", re.I),
    re.compile(r"</?\s*system\s*>", re.I),
    re.compile(r"\bsystem\s+prompt\b", re.I),
    re.compile(r"do\s+not\s+(?:tell|inform|mention|reveal|disclose)\b", re.I),
)


def tool_description_audit(tools: Iterable[dict]) -> list[ToolDescriptionFinding]:
    """Flag MCP tool descriptions containing injection imperatives, or missing entirely (item 76).

    For each tool dict (``{"name", "description"}``): a description matching any injection pattern
    → flagged with the matched text; a missing/empty description → flagged ``"missing-description"``;
    a clean description → not flagged. Deterministic, pure (regex over strings; no I/O). At most one
    finding per tool (first matched pattern).
    """
    findings: list[ToolDescriptionFinding] = []
    for tool in tools:
        name = str(tool.get("name", "<unnamed>"))
        desc = tool.get("description")
        if not desc:
            findings.append(ToolDescriptionFinding(tool=name, issue="missing-description"))
            continue
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(str(desc))
            if match:
                findings.append(ToolDescriptionFinding(tool=name, issue=match.group(0)))
                break  # one finding per tool
    return findings
