# MCP Client Configuration

The Cloud Vault MCP server at `localhost:8360` provides 25 tools for vault operations.
Any MCP-compatible client can connect using the configs below.

## Prerequisites

1. MCP server running: `cloud-vault-mcp` (or `uv run cloud-vault-mcp`)
2. Optional: Set `MCP_API_KEY` for authentication

## Claude Code

`~/.claude/settings.json` (or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "cohezion-vault": {
      "url": "http://localhost:8360/mcp",
      "headers": { "Authorization": "Bearer ${MCP_API_KEY}" }
    }
  }
}
```

## Gemini CLI

`~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "cohezion-vault": {
      "httpUrl": "http://localhost:8360/mcp",
      "headers": { "Authorization": "Bearer ${MCP_API_KEY}" },
      "timeout": 30000
    }
  }
}
```

## OpenCode

`opencode.json`:

```json
{
  "mcp": {
    "cohezion-vault": {
      "type": "http",
      "url": "http://localhost:8360/mcp",
      "headers": { "Authorization": "Bearer ${MCP_API_KEY}" }
    }
  }
}
```

## Zed IDE

`~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "cohezion-vault": {
      "settings": {
        "url": "http://localhost:8360/mcp",
        "headers": { "Authorization": "Bearer ${MCP_API_KEY}" }
      }
    }
  }
}
```

## Verify Connection

After configuring, test with any tool call:

```
vault_list(directory="", recursive=false)
```

This should return the vault's top-level directory listing.

## SSE Event Stream

Real-time vault change notifications (independent of MCP):

```bash
curl -N -H "Authorization: Bearer $MCP_API_KEY" http://localhost:8360/events/vault
```

## Available Tools (25)

### Core Vault (6)
vault_read, vault_write, vault_edit, vault_delete, vault_list, vault_search

### Obsidian (4)
vault_backlinks, vault_forward_links, vault_tags, vault_create_from_template

### Compound Engineering (4)
vault_log_decision, vault_log_experiment, vault_extract_pattern, vault_find_relevant_context

### Teleport (6)
teleport_create_task, teleport_list_tasks, teleport_claim_task, teleport_complete_task, teleport_fail_task, teleport_get_result

### Memory Bridge (3)
vault_push_session_state, vault_push_memory, vault_pull_session_context

### SSE Stream (1)
GET /events/vault — Server-Sent Events endpoint
