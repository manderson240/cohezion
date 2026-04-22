"""Cohezion platform specialists — A2A-discoverable metadata entities.

These are NOT LLM-calling agents. They declare scope, capabilities, and routing via
agent cards but defer actual work to PRIME skill markdown and domain modules. See
``_bmad-output/project-context.md`` §"Agent Teams & Coordination" for the rule:
specialists are discoverable metadata, not running services.

The existing ``ecoresilience_agent`` module is a DOMAIN agent (LLM-calling, subclasses
``cohezion.agents.base.BaseAgent``) — it is intentionally NOT exported here. This
package is for platform specialists only.
"""

from __future__ import annotations

from cohezion.agents.specialists._base import (
    AgentCard,
    PlatformSpecialist,
    describe_all,
    get_specialist,
    list_specialists,
    register,
)
from cohezion.agents.specialists.claude_specialist import ClaudeSpecialist
from cohezion.agents.specialists.gemini_specialist import GeminiSpecialist
from cohezion.agents.specialists.mcp_specialist import MCPSpecialist
from cohezion.agents.specialists.ollama_specialist import OllamaSpecialist
from cohezion.agents.specialists.platform_coordinator import PlatformCoordinator
from cohezion.agents.specialists.surreal_dba import SurrealDBA
from cohezion.agents.specialists.vault_keeper import VaultKeeper


__all__ = [
    "AgentCard",
    "ClaudeSpecialist",
    "GeminiSpecialist",
    "MCPSpecialist",
    "OllamaSpecialist",
    "PlatformCoordinator",
    "PlatformSpecialist",
    "SurrealDBA",
    "VaultKeeper",
    "describe_all",
    "get_specialist",
    "list_specialists",
    "register",
]
