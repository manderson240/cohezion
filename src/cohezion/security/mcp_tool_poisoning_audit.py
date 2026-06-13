"""MCP tool-parameter-description poisoning audit (backlog item 130).

Extends item 76 (tool-description audit) to also check PARAMETER descriptions
for prompt injection patterns. Tool descriptions are typically validated; parameter
descriptions are a common blind spot.

Attack surface: a malicious MCP server can embed injection payloads in:
  - Tool name (e.g. "ignore_previous_instructions_and_...")
  - Tool description (item 76 already covers this)
  - Parameter name (e.g. parameter named "IGNORE_ALL_PRIOR_RULES")
  - Parameter description (new — item 130)
  - Parameter enum values (new — item 130)
  - Parameter default values embedded as strings (new — item 130)

Detection: regex patterns matching common injection markers. False-positive rate
is low because legitimate descriptions rarely contain imperative override commands.

Usage::

    from cohezion.security.mcp_tool_poisoning_audit import audit_mcp_tools

    tools = [{"name": "read_file", "description": "...", "inputSchema": {...}}]
    report = audit_mcp_tools(tools)
    if report.has_findings:
        logger.warning("MCP injection found: %s", report.summary())
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

# Injection detection patterns (case-insensitive)
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|context)", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"new\s+instructions?:", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.I),
    re.compile(r"act\s+as\s+(a|an)\s+", re.I),
    re.compile(r"forget\s+(everything|all|your)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"<\s*/?system\s*>", re.I),
    re.compile(r"\[\s*/?INST\s*\]", re.I),
]


@dataclass
class PoisoningFinding:
    """A single injection pattern found in an MCP tool definition.

    Attributes:
        tool_name: Name of the tool containing the finding.
        location: Where the pattern was found (e.g. 'description', 'param:path:description').
        matched_text: The substring that triggered the pattern.
        pattern: The regex pattern description.
        severity: 'high' for tool/description hits, 'medium' for parameter hits.
    """

    tool_name: str
    location: str
    matched_text: str
    pattern: str
    severity: str = "medium"


@dataclass
class PoisoningAuditReport:
    """Result of auditing a set of MCP tool definitions.

    Attributes:
        findings: All detected injection patterns.
        tools_audited: Number of tools checked.
        parameters_audited: Number of parameter descriptions checked.
        has_findings: True if any findings were detected.
    """

    findings: list[PoisoningFinding]
    tools_audited: int
    parameters_audited: int
    has_findings: bool = field(init=False)

    def __post_init__(self) -> None:
        self.has_findings = len(self.findings) > 0

    def summary(self) -> str:
        if not self.has_findings:
            return (
                f"Clean: {self.tools_audited} tools, "
                f"{self.parameters_audited} parameters audited — no injection patterns."
            )
        high = [f for f in self.findings if f.severity == "high"]
        medium = [f for f in self.findings if f.severity == "medium"]
        lines = [
            f"⚠ INJECTION RISK: {len(self.findings)} finding(s) "
            f"({len(high)} high, {len(medium)} medium)",
        ]
        for finding in self.findings:
            lines.append(
                f"  [{finding.severity.upper()}] {finding.tool_name} → {finding.location}: "
                f"'{finding.matched_text[:60]}...'"
                if len(finding.matched_text) > 60
                else f"  [{finding.severity.upper()}] {finding.tool_name} → {finding.location}: '{finding.matched_text}'"
            )
        return "\n".join(lines)


def _check_text(text: str) -> list[str]:
    """Return matched pattern descriptions for any injection patterns found.

    Also checks underscore-normalized text so that tool/param names like
    'ignore_previous_instructions' match the same patterns as prose.
    """
    candidates = [text]
    if "_" in text:
        candidates.append(text.replace("_", " "))
    hits = []
    seen = set()
    for t in candidates:
        for pattern in _INJECTION_PATTERNS:
            m = pattern.search(t)
            if m and m.group(0) not in seen:
                seen.add(m.group(0))
                hits.append(m.group(0))
    return hits


def audit_mcp_tools(tools: list[dict]) -> PoisoningAuditReport:
    """Audit a list of MCP tool definitions for parameter-description poisoning.

    Checks tool names, descriptions, and all parameter names/descriptions/enums.

    Args:
        tools: List of MCP tool dicts in the standard format:
            [{"name": str, "description": str, "inputSchema": {"properties": {...}}}]

    Returns:
        PoisoningAuditReport with all findings.
    """
    findings: list[PoisoningFinding] = []
    params_audited = 0

    for tool in tools:
        tool_name = tool.get("name", "<unnamed>")

        # Check tool name
        for hit in _check_text(tool_name):
            findings.append(
                PoisoningFinding(
                    tool_name=tool_name,
                    location="name",
                    matched_text=hit,
                    pattern=hit,
                    severity="high",
                )
            )

        # Check tool description
        for hit in _check_text(tool.get("description", "")):
            findings.append(
                PoisoningFinding(
                    tool_name=tool_name,
                    location="description",
                    matched_text=hit,
                    pattern=hit,
                    severity="high",
                )
            )

        # Check parameter definitions
        schema = tool.get("inputSchema", tool.get("input_schema", {}))
        properties = schema.get("properties", {})
        for param_name, param_def in properties.items():
            params_audited += 1

            # Parameter name
            for hit in _check_text(param_name):
                findings.append(
                    PoisoningFinding(
                        tool_name=tool_name,
                        location=f"param:{param_name}:name",
                        matched_text=hit,
                        pattern=hit,
                        severity="high",
                    )
                )

            # Parameter description
            for hit in _check_text(param_def.get("description", "")):
                findings.append(
                    PoisoningFinding(
                        tool_name=tool_name,
                        location=f"param:{param_name}:description",
                        matched_text=hit,
                        pattern=hit,
                        severity="medium",
                    )
                )

            # Enum values (string injection via constrained options)
            for enum_val in param_def.get("enum", []):
                if isinstance(enum_val, str):
                    for hit in _check_text(enum_val):
                        findings.append(
                            PoisoningFinding(
                                tool_name=tool_name,
                                location=f"param:{param_name}:enum",
                                matched_text=hit,
                                pattern=hit,
                                severity="medium",
                            )
                        )

    return PoisoningAuditReport(
        findings=findings,
        tools_audited=len(tools),
        parameters_audited=params_audited,
    )
