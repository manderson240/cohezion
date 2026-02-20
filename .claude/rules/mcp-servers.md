# MCP Servers

Custom MCP servers configured for this vault.

## cloud-vault-mcp

**Source:** `~/.claude/mcp.json`
**Type:** HTTP server
**URL:** http://127.0.0.1:8360
**Purpose:** Programmatic access to the Cohezion vault

**Available Tool Categories:**
- **VaultOps:** Query papers, decisions, lessons, concepts
- **CompoundOps:** Semantic linking, cross-validation
- **ObsidianOps:** Create wiki-links, update frontmatter
- **Teleport:** Cloud↔local file sync
- **SheetsBridge:** Batch update Google Sheets
- **SurrealDB:** Query agent context graph

**When to Use:**
- Searching vault programmatically
- Creating vault notes automatically
- Batch updating sheets
- Querying agent decisions

**Authentication:** Bearer token configured in mcp.json

## ollama

**Source:** `~/.claude/mcp.json`
**Type:** stdio
**Purpose:** Semantic search and embeddings via Ollama

**Available Tools:**
- `embed` - Generate embeddings for semantic search
- `query` - Vector search across vault
- `batch` - Bulk operations
- `select_model` - Choose Ollama model
- `status` - Check Ollama health

**Configuration:**
- **Ollama URL:** http://localhost:11434
- **Timeout:** 30 seconds
- **Python:** `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python`

**When to Use:**
- Semantic search + embeddings
- Vector search across vault content
- Model selection for embeddings

**Note:** Requires Ollama service running on port 11434
