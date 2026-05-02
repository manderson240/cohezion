---
paths:
  - "src/cohezion/mcp/**"
  - "apps/mcp-*/**"
  - "config/mcp*"
---

# MCP Server Rules

- MCP servers expose Cohezion capabilities via Model Context Protocol (stdio transport)
- Four servers: `narration_server`, `surreal_server`, `swarm_server`, `usage_server`
- Apps in `apps/mcp-*/` are TypeScript frontends consuming MCP data (Express/React/Three.js)
- MCP config lives in `config/` — keep server definitions there, not scattered
- All MCP tool handlers must validate input with Pydantic before processing
- Cost guardrail applies: MCP servers must not spawn cloud API calls without explicit user action
