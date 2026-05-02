"""Configuration file templates for Phase 4.

Template-driven regeneration of CLAUDE.md and GEMINI.md
from canonical vault content.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


CLAUDE_MD_TEMPLATE = """# Cohezion - Claude Code Orchestration

COHEZION is a systemic AI orchestration ecosystem governed by
**Quadrature Nexus Orchestration** and **Hermetic Compound Engineering**
("As Above, So Below"). We implement **FLUME** combined with
**JEPA-aligned World Models** for 12D universe simulation,
autonomous research, and value precipitation via **UCP/MCP**.

## Constitutional Framework

All actions are governed by two documents:
- **Core Constitution**: `.agent/CONSTITUTION.md` - January 2026 Claude Edition
- **Project Charter**: `.agent/COHEZION_CHARTER.md` - SPIN theory, FLUME evolution, HIHO, observable AI

## Quick Reference

- **Language**: Python 3.13+ | **Package Manager**: `uv`
- **Formatter**: `ruff format` (88-char) | **Linter**: `ruff check`
- **Database**: SurrealDB (ws://localhost:8000/rpc)
- **Local Models**: Ollama (deepseek-r1:70b, qwen3-coder:30b, phi3:mini)

## Latest Decisions (from vault)

{latest_decisions}

## Key Operational Protocols

{operational_protocols}

## For Detailed Information

→ See ~/vaults/cohezion-vault/ for 150+ docs (decisions, patterns, experiments)
→ Read .agent/ for constitutional framework
→ Check knowledge_graph/ for mission journal and learnings
"""

GEMINI_MD_TEMPLATE = """# GEMINI - Cohezion Orchestration Layer

This document serves as the primary orchestration hub for AI agents in the Cohezion project.

## 1. Core Project Identity

**COHEZION** is a systemic AI orchestration ecosystem governed by
**Quadrature Nexus Orchestration** and **Hermetic Compound Engineering**
("As Above, So Below"). We implement **FLUME** methodology combined
with **JEPA-aligned World Models**.

## 2. Constitutional Framework

All agent actions are governed by:
- **Core Constitution**: `.agent/CONSTITUTION.md` (behavioral pillars, hard constraints)
- **Project Charter**: `.agent/COHEZION_CHARTER.md` (SPIN theory, FLUME, HIHO)

## 3. Dynamic Knowledge Hub

Historical and specialized information:
- **Historical Context**: Knowledge graph / MISSION_JOURNAL.md
- **Extracted Wisdom**: KEY_LEARNINGS.md
- **Technical Standards**: .agent/CODING_STANDARDS.md

## 4. Operational Guardrails

{operational_guardrails}

## 5. Repository Layout

- **Source**: `src/cohezion/` - Core package
- **Research**: `research/` - Challenges and experiments
- **Knowledge**: `knowledge_graph/` - Persistent memory
- **Skills**: `src/cohezion/skills/` - 124+ PRIME definitions

## 6. Configuration Management

This file is kept lean (<200 lines) via automated synchronization.
→ See vault/ for detailed decisions and patterns.
"""


class TemplateType(Enum):
    """Available configuration templates."""

    CLAUDE_MD = "claude_md"
    GEMINI_MD = "gemini_md"


@dataclass
class TemplateContext:
    """Context variables for template rendering."""

    latest_decisions: list[str]
    operational_protocols: list[str]
    operational_guardrails: list[str]
    recent_patterns: list[str]
    sync_timestamp: str


class ConfigTemplateEngine:
    """Renders configuration files from templates and vault content."""

    @staticmethod
    def render_claude_md(context: TemplateContext) -> str:
        """Render CLAUDE.md from template and context."""
        # Format decisions section
        decisions_text = "### Latest Decisions\n\n"
        if context.latest_decisions:
            for decision in context.latest_decisions[:5]:  # Top 5
                decisions_text += f"- {decision}\n"
        else:
            decisions_text += "See vault/decisions/ for complete decision log.\n"

        # Format protocols section
        protocols_text = "### Core Protocols\n\n"
        if context.operational_protocols:
            for protocol in context.operational_protocols[:5]:  # Top 5
                protocols_text += f"- {protocol}\n"
        else:
            protocols_text += "Refer to .agent/ for detailed protocols.\n"

        # Render template
        content = CLAUDE_MD_TEMPLATE.format(
            latest_decisions=decisions_text,
            operational_protocols=protocols_text,
        )

        return content

    @staticmethod
    def render_gemini_md(context: TemplateContext) -> str:
        """Render GEMINI.md from template and context."""
        # Format guardrails section
        guardrails_text = ""
        if context.operational_guardrails:
            for guardrail in context.operational_guardrails[:5]:
                guardrails_text += f"- {guardrail}\n"
        else:
            guardrails_text += "- Resource Monitor: Enforce 4 concurrent model calls\n"

        # Render template
        content = GEMINI_MD_TEMPLATE.format(
            operational_guardrails=guardrails_text,
        )

        return content

    @staticmethod
    def get_template(template_type: TemplateType) -> str:
        """Get raw template string."""
        if template_type == TemplateType.CLAUDE_MD:
            return CLAUDE_MD_TEMPLATE
        else:
            return GEMINI_MD_TEMPLATE
