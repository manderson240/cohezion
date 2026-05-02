---
paths:
  - ".mcp.json"
  - "cloud-vault-mcp/"
---

# User MCP Servers

Custom MCP servers configured for Cohezion compound engineering.

## cohezion-vault

**Source:** `.mcp.json` (HTTP server at `http://localhost:8360/mcp`)
**Purpose:** Programmatic vault access for compound engineering knowledge management
**Status:** ✅ All tools working

### Core Operations (Vault CRUD)

| Tool | Status | Description |
|------|--------|-------------|
| `vault_read` | ✅ | Read note content from vault |
| `vault_write` | ✅ | Create or overwrite a note |
| `vault_edit` | ✅ | Surgical edits (find_replace, append, prepend, insert_at_heading) |
| `vault_delete` | ✅ | Delete a note |
| `vault_list` | ✅ | List vault contents (directory or recursive) |

### Search & Navigation

| Tool | Status | Description |
|------|--------|-------------|
| `vault_search` | ✅ | Full-text search (all/folder/tags scope) |
| `vault_backlinks` | ✅ | Find notes linking TO target |
| `vault_forward_links` | ✅ | Find notes target links TO |
| `vault_tags` | ✅ | List all tags or tags for specific note |

### Compound Engineering Operations

| Tool | Status | Description |
|------|--------|-------------|
| `vault_log_decision` | ✅ | Log architectural decision with context/rationale |
| `vault_log_experiment` | ✅ | Log experiment with hypothesis/method/result/learnings |
| `vault_extract_pattern` | ✅ | Extract reusable pattern from source with code example |
| `vault_find_relevant_context` | ✅ | Semantic search for relevant decisions/patterns |

### Template System

| Tool | Status | Description |
|------|--------|-------------|
| `vault_create_from_template` | ✅ | Create note from template with variable substitution |

**Available templates:** decisions, experiments, patterns, papers, daily, projects

### Usage Patterns

**Log learnings:**
```python
# After solving a problem
mcp__cohezion-vault__vault_log_decision(
    project="cohezion",
    title="Short decision title",
    context="What led to this",
    decision="What was decided",
    rationale="Why this option"
)
```

**Search for context:**
```python
# Before solving a similar problem
mcp__cohezion-vault__vault_find_relevant_context(
    query="error handling patterns for MCP servers"
)
```

**Extract patterns:**
```python
# After discovering reusable code
mcp__cohezion-vault__vault_extract_pattern(
    source_path="src/cohezion/compound/executor.py",
    pattern_name="Circuit Breaker Pattern",
    description="When to use circuit breakers",
    code_example="```python\n# example\n```",
    domain="reliability"
)
```

### Vault Location

- **Directory:** `~/vaults/cohezion-vault/`
- **Structure:** decisions/, experiments/, patterns/, concepts/, daily/, sessions/, projects/
- **Templates:** In `templates/` subdirectory

### Token Efficiency

Using vault for knowledge management provides 10K+ token savings per session:
- Load only relevant context via search (vs loading all 1177 lines of old MEMORY.md)
- MEMORY.md is now auto-compiled weekly from vault (95 lines vs 1177 lines)
- Single source of truth survives across sessions
