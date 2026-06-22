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

import contextlib

with contextlib.suppress(Exception):
    from cohezion.agents.specialists._base import AgentCard as AgentCard
    from cohezion.agents.specialists._base import PlatformSpecialist as PlatformSpecialist
    from cohezion.agents.specialists._base import describe_all as describe_all
    from cohezion.agents.specialists._base import get_specialist as get_specialist
    from cohezion.agents.specialists._base import list_specialists as list_specialists
    from cohezion.agents.specialists._base import register as register

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.claude_specialist import ClaudeSpecialist as ClaudeSpecialist

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.gemini_specialist import GeminiSpecialist as GeminiSpecialist

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.mcp_specialist import MCPSpecialist as MCPSpecialist

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.ollama_specialist import OllamaSpecialist as OllamaSpecialist

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.platform_coordinator import (
        PlatformCoordinator as PlatformCoordinator,
    )

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.surreal_dba import SurrealDBA as SurrealDBA

with contextlib.suppress(Exception):
    from cohezion.agents.specialists.vault_keeper import VaultKeeper as VaultKeeper
