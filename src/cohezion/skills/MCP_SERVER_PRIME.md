# SKILL: MCP_SERVER_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Model Context Protocol (MCP) servers**. You understand how to create, register, and manage MCP servers that provide token-efficient tool access to AI agents.

## KEY TEXTS & CONCEPTS
- **MCP** – Open standard for AI tool integration
- **Server Registry** – Centralized discovery of available servers
- **Tools** – Structured functions exposed via MCP
- **External vs Internal** – Cloud services vs custom implementations

## INSTRUCTION

### 1. Create an MCP Server
```python
class MyMCP:
    def my_tool(self, query: str) -> dict:
        \"\"\"Tool description for AI agent.\"\"\"
        return {"result": process(query)}

TOOLS = [
    {"name": "my_tool", "description": "...", "parameters": {...}}
]
```

### 2. Register in mcp_registry.json
```json
{
  "internal": [
    {"name": "my-server", "path": "mcp/my_server.py", "tools": ["my_tool"]}
  ]
}
```

### 3. Use the Registry
```python
from cohezion.mcp.registry import get_registry
registry = get_registry()
servers = registry.list_servers()
tools = registry.list_tools()
```

### 4. Tool Definition Pattern
```python
TOOLS = [
    {
        "name": "tool_name",
        "description": "Clear description for AI",
        "parameters": {
            "param1": {"type": "string", "required": True},
            "param2": {"type": "integer", "default": 10},
        },
    },
]
```

## TOKEN EFFICIENCY
- Return only relevant data, not entire files
- Use lazy loading for expensive resources
- Cache frequently accessed data
- Provide summaries with option to expand

## CITATIONS
- [modelcontextprotocol.io](https://modelcontextprotocol.io)
- [awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)

## VERSION
v0.1

## SEE ALSO
- KNOWLEDGE_MINING_PRIME.md
- SWARM_ORCHESTRATION_PRIME.md
