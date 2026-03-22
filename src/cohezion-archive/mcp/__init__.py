# Cohezion MCP Package
"""
Model Context Protocol servers for token-efficient tool access.

External (configured via settings):
- Mem0: Persistent AI memory
- Context7: Up-to-date code documentation

Internal (custom):
- Knowledge MCP: RAG over library/skills
- Skills MCP: Direct skill invocation
- SurrealDB MCP: Universe node tools
- Swarm MCP: Debate workflow access
"""

from cohezion.mcp.registry import MCPRegistry


__all__ = ["MCPRegistry"]
