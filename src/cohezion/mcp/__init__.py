"""Cohezion MCP servers."""

from __future__ import annotations

import contextlib

from .wiki_mcp import WikiMCP


__all__ = ["WikiMCP"]

# Wiring-sweep 2026-06-22: mcp/ orphan modules — creates import-graph edges.
with contextlib.suppress(Exception):
    from cohezion.mcp.audit import MCPAuditor as MCPAuditor
with contextlib.suppress(Exception):
    from cohezion.mcp.audit import AuditResult as AuditResult
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_session import CompoundMCPSessionManager as CompoundMCPSessionManager
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_session import MCPServerState as MCPServerState
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_unified import UnifiedCompoundManager as UnifiedCompoundManager
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_unified import ServerState as ServerState
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_utils import McpClientResolver as McpClientResolver
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_utils import ok as ok
with contextlib.suppress(Exception):
    from cohezion.mcp.compound_utils import err as err
with contextlib.suppress(Exception):
    from cohezion.mcp.hookify_server import HookifyMCPBridge as HookifyMCPBridge
with contextlib.suppress(Exception):
    from cohezion.mcp.knowledge_server import KnowledgeMCP as KnowledgeMCP
with contextlib.suppress(Exception):
    from cohezion.mcp.manager import MCPManager as MCPManager
with contextlib.suppress(Exception):
    from cohezion.mcp.manager import ServerHealth as ServerHealth
with contextlib.suppress(Exception):
    from cohezion.mcp.registry import MCPRegistry as MCPRegistry
with contextlib.suppress(Exception):
    from cohezion.mcp.research_server import ResearchMinerServer as ResearchMinerServer
with contextlib.suppress(Exception):
    from cohezion.mcp.skills_server import SkillsMCP as SkillsMCP
with contextlib.suppress(Exception):
    from cohezion.mcp.surreal_server import SurrealMCP as SurrealMCP
with contextlib.suppress(Exception):
    from cohezion.mcp.swarm_server import SwarmMCP as SwarmMCP
with contextlib.suppress(Exception):
    from cohezion.mcp.webmcp_bridge import WebMCPBridge as WebMCPBridge
