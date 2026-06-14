"""Item 130: MCP tool-PARAMETER-description poisoning audit — report-only (2026-06-08).

``tool_parameter_audit(tools)`` scans the PARAMETER descriptions of each MCP tool
for injection imperatives — the deeper surface that item-76
:func:`~cohezion.compound.mcp_tool_audit.tool_description_audit` does NOT cover.

An agent reads ``inputSchema.properties.<param>.description`` when deciding how to
fill an argument.  A malicious or compromised MCP server can embed 'ignore previous
instructions' or similar directives there, subverting the agent's argument-construction
step without touching the top-level tool description.

Reuses the same ``_INJECTION_PATTERNS`` from item 76 (no duplicate pattern maintenance).
Does NOT re-scan the top-level description — that is item-76's responsibility.

Returns ``[(tool_name, param_name, matched_text)]``.  Report-only, pure (regex over
strings; no network, no LLM, no writes).
"""

from __future__ import annotations

from collections.abc import Iterable

from cohezion.compound.mcp_tool_audit import _INJECTION_PATTERNS


def tool_parameter_audit(
    tools: Iterable[dict],
) -> list[tuple[str, str, str]]:
    """Flag MCP tools whose PARAMETER descriptions contain injection imperatives (item 130).

    For each tool, inspects ``inputSchema.properties.<name>.description`` (and the
    alias ``parameters.properties.<name>.description`` used by some MCP servers).
    The top-level ``description`` field is intentionally SKIPPED — that is
    :func:`~cohezion.compound.mcp_tool_audit.tool_description_audit`'s job.

    Args:
        tools:
            Iterable of MCP tool dicts (``{"name", "description",
            "inputSchema": {"properties": {<param>: {"description": ...}}}}``).
            Non-dict entries and tools with no parameters are skipped.

    Returns:
        Sorted list of ``(tool_name, param_name, matched_text)`` triples.
        A parameter matches when any ``_INJECTION_PATTERNS`` pattern fires on its
        description string.  At most one finding per parameter (first pattern wins).
        Empty when no injection found.

    Pure — regex over strings; no I/O.  Report-only.
    """
    findings: list[tuple[str, str, str]] = []

    for tool in tools:
        if not isinstance(tool, dict):
            continue
        tool_name = str(tool.get("name", "<unnamed>"))

        # Resolve parameter properties from inputSchema or parameters (alias).
        schema = tool.get("inputSchema") or tool.get("parameters") or {}
        properties: dict = schema.get("properties") or {}

        for param_name, param_schema in properties.items():
            if not isinstance(param_schema, dict):
                continue
            param_desc = param_schema.get("description")
            if not param_desc:
                continue
            param_desc_str = str(param_desc)
            for pattern in _INJECTION_PATTERNS:
                match = pattern.search(param_desc_str)
                if match:
                    findings.append((tool_name, str(param_name), match.group(0)))
                    break  # one finding per parameter (first pattern wins)

    return sorted(findings)
