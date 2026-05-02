---
title: MCP Infrastructure Architecture
date: 2026-02-10
status: active
tags: [architecture, infrastructure, mcp, concepts]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 48
  synapse_out: 17
---

## System Overview

The MCP (Model Context Protocol) infrastructure provides a bridge between Claude Code IDE and local services (Ollama, SurrealDB, Sheets, Vault). Two MCP servers work together:

1. **Cloud Vault MCP** - HTTP server exposing 30+ tools for vault/graph/research operations
2. **Ollama MCP** - Stdio-based server providing local inference with smart model selection

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code IDE                          │
│            (User runs AI agents/tasks)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP Protocol
                       │ (Claude Code ↔ MCP Servers)
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────────┐    ┌─────────────────────────┐
│ Cloud Vault MCP      │    │   Ollama MCP Server     │
│ (HTTP Port 8360)     │    │   (Stdio, no port)      │
├──────────────────────┤    ├─────────────────────────┤
│ 30 Tools:            │    │ 5 Tools:                │
│  - vault_* (10)      │    │  - ollama_query         │
│  - compound_* (4)    │    │  - ollama_embed         │
│  - sheets_* (5)      │    │  - ollama_batch         │
│  - surrealdb_* (5)   │    │  - ollama_status        │
│  - teleport_* (6)    │    │  - ollama_select_model  │
│  - memory_* (3)      │    │                         │
│  - health_* (1)      │    │ Calls HTTP to Ollama    │
└──────┬───────────────┘    └──────┬──────────────────┘
       │                            │
       │ HTTP Calls                 │ HTTP Calls
       │                            │
       ├────────────┬───────────────┼────────────┬──────────────┐
       │            │               │            │              │
       ▼            ▼               ▼            ▼              ▼
  ┌────────┐  ┌──────────────┐ ┌────────┐ ┌──────────────┐ ┌────────┐
  │ Vault  │  │  SurrealDB   │ │Sheets  │ │ Ollama       │ │Memory  │
  │(Files) │  │  (Graph DB)  │ │ API    │ │ Service      │ │(Notes) │
  └────────┘  └──────────────┘ └────────┘ │(Port 11434)  │ └────────┘
                                          │28+ Models   │
                                          └──────────────┘
```

## Data Flow: Query Processing

### Step 1: User Query
User types in Claude Code IDE: "What papers reference machine learning?"

### Step 2: Claude Routes to MCP Tool
```
Claude Code detects MCP protocol prefix
Routes to available MCP servers (Cloud Vault, Ollama)
Selects best tool: surrealdb_query (in Cloud Vault MCP)
```

### Step 3: Cloud Vault MCP Tool Execution
```
Tool: surrealdb_query({
  "query": "SELECT * FROM papers WHERE tags CONTAINS 'machine-learning'"
})

Execution in Cloud Vault MCP:
  1. Parse query
  2. Connect to SurrealDB (http://localhost:8000)
  3. Execute query
  4. Format results as JSON
  5. Return to Claude
```

### Step 4: If Ollama Inference Needed
User asks: "Summarize this paper in one sentence"

```
Claude routes to: ollama_query (in Ollama MCP)
Ollama MCP:
  1. Select model based on task/length: "qwen2.5-coder:14b"
  2. Call Ollama service: curl localhost:11434/api/generate
  3. Ollama runs inference on GPU/CPU
  4. Return response to Claude
```

### Step 5: Response Returned
Results flow back: Ollama → Ollama MCP → Claude Code → User

## Architecture Components

### 1. Cloud Vault MCP Server

**Location:** `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/`

**Role:** Expose vault, database, and research tools as MCP protocol

**Key Components:**
```
cloud-vault-mcp/
├── src/
│   └── mcp_server/
│       ├── server.py              # Main MCP server
│       ├── vault_operations.py    # Vault access tools
│       ├── compound_operations.py # Multi-step tasks
│       ├── sheets_bridge.py       # Google Sheets integration
│       ├── surrealdb_sync.py      # Graph database sync
│       ├── health.py              # Health checks
│       └── ollama_client.py       # Calls to Ollama MCP
├── benchmarks/
│   └── benchmark_runner.py        # Performance testing
└── tests/
    └── *.py                       # Unit + integration tests
```

**Tools Provided:**
- **vault_** (10): read_file, write_file, search_vault, list_directory, get_metadata, update_metadata, create_note, delete_note, move_note, watch_file
- **compound_** (4): research_topic, enrich_paper, cross_reference_concepts, analyze_gap
- **sheets_** (5): get_all_rows, read_range, update_row, batch_update, update_vault_note_column
- **surrealdb_** (5): query, import_papers, import_concepts, create_index, get_schema
- **teleport_** (6): submit_task, get_result, list_tasks, update_status, archive_result, cleanup
- **memory_** (3): store, retrieve, list_memories
- **health_** (1): /health endpoint

**Configuration (27+ variables):**
```bash
# Core paths
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
MCP_HOST=0.0.0.0
MCP_PORT=8360

# Service URLs
OLLAMA_ENABLED=true
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT=30

SURREALDB_ENABLED=true
SURREALDB_URL=http://localhost:8000

SHEETS_ENABLED=true
GOOGLE_CLOUD_PROJECT=cohezion-477604

# Monitoring
HEALTH_CHECK_TIMEOUT=5
LOG_LEVEL=INFO
```

### 2. Ollama MCP Server

**Location:** `/home/mike-anderson/dev/cohezion/ollama-mcp/`

**Role:** Smart model selection and inference via Ollama service

**Key Components:**
```
ollama-mcp/
├── src/
│   └── mcp_server/
│       ├── server.py           # MCP protocol handler
│       ├── ollama_client.py    # HTTP to Ollama service
│       ├── model_selector.py   # Intelligent model picking
│       ├── context_manager.py  # Token budget tracking
│       └── error_handler.py    # Graceful degradation
├── benchmarks/
│   └── benchmark_runner.py     # Performance testing
└── tests/
    └── *.py                    # Unit + integration tests
```

**Model Selection Logic:**
```python
def select_model(task_type, content_length):
    """
    Select model based on:
    1. Task type (query, embed, code, reasoning)
    2. Content length (short, medium, long context)
    3. Model availability
    """
    if task_type == "embed":
        return "nomic-embed-text:latest"

    if content_length > 100_000:  # Long context (256K)
        return "phi4-256k:latest"
    elif content_length > 10_000:  # Medium (14B)
        return "qwen2.5-coder:14b"
    else:  # Short queries (8B)
        return "qwen3:8b"
```

**Available Models (28):**
- **Fast (8B):** qwen3:8b, deepseek-r1:7b
- **Balanced (14B):** qwen2.5-coder:14b, phi4:latest
- **Long Context (256K):** phi4-256k:latest
- **Embeddings:** nomic-embed-text:latest
- **Other:** 23 additional models (llama, mistral, neural-chat, etc.)

**Configuration:**
```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT=30
CONTEXT_MAX_TOKENS=8192
CACHE_ENABLED=true
```

### 3. Ollama Service (Local Inference)

**Location:** `/usr/local/bin/ollama` or similar

**Role:** Run language models locally on GPU/CPU

**How It Works:**
1. Ollama runs as background service (port 11434)
2. Accepts HTTP requests with prompt
3. Runs inference on available GPU (NVIDIA/AMD) or CPU
4. Returns generated text

**Key Endpoints:**
```bash
# List available models
GET /api/tags

# Run inference
POST /api/generate
{
  "model": "qwen3:8b",
  "prompt": "What is ML?",
  "stream": false
}

# Show model info
POST /api/show
{"name": "qwen3:8b"}

# Generate embeddings
POST /api/embed
{"model": "nomic-embed-text:latest", "input": "machine learning"}
```

### 4. SurrealDB (Graph Database)

**Location:** `http://localhost:8000`

**Role:** Store and query 12-dimensional paper/concept graph

**Schema:**
```surql
-- Paper nodes
TABLE papers {
  title: string,
  abstract: string,
  authors: array,
  published: datetime,
  tags: array,
  file_path: string,
  -- Relationships
  concepts: array
}

-- Concept nodes
TABLE concepts {
  name: string,
  definition: string,
  primary_sources: array,
  related_concepts: array,
  papers: array
}

-- Link relationships
TABLE links {
  from_paper: record,
  to_concept: record,
  link_type: string,
  created_at: datetime
}
```

**Sample Queries:**
```surql
-- Find papers with concept
SELECT * FROM papers WHERE concepts CONTAINS ['machine-learning']

-- Find all concepts for a paper
SELECT concepts FROM papers WHERE title CONTAINS 'transformer'

-- Graph traversal: Paper → Concepts → Related Papers
SELECT
  paper.title,
  paper.concepts[*].name as concepts,
  concepts[*].papers[*].title as related_papers
FROM papers as paper
WHERE paper.title CONTAINS 'attention'
LIMIT 10
```

### 5. Google Sheets Integration

**Location:** Cohesion_Research sheet

**Role:** Maintain research database with programmatic access

**Columns:**
- A: Link (source URL)
- B: Status (researched, pending, skipped)
- C: Key Abstractions (comma-separated)
- D: Domain (AI, biology, etc.)
- E: Integration Point (where used)
- F: Vault Note (link to paper note)

**Access Method:**
```python
from sheets_bridge import SheetsBridge

bridge = SheetsBridge(sheet_id="1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk")

# Get all rows
all_rows = bridge.get_all_rows()

# Update cell
bridge.update_row(row_idx=10, column="C", value="ML, AI, transformers")

# Batch update (faster)
updates = [
  {"row": 10, "column": "C", "value": "new value"},
  {"row": 11, "column": "D", "value": "Biology"}
]
bridge.batch_update(updates)
```

**Authentication:**
Requires Google Cloud credentials via Application Default Credentials (ADC):
```bash
gcloud auth application-default login
# Creates: ~/.config/gcloud/application_default_credentials.json
```

### 6. Obsidian Vault

**Location:** `/home/mike-anderson/vaults/cohezion-vault/`

**Role:** Local file-based knowledge base with cross-linking

**Structure:**
```
cohezion-vault/
├── papers/          # 84 paper notes (enriched with concepts)
├── concepts/        # 21 concept definitions
├── decisions/       # ADRs (architecture decisions)
├── patterns/        # Reusable solutions
├── experiments/     # Hypothesis testing
├── lessons/         # Insights from research
├── daily/           # Session logs
├── projects/        # Long-term work
├── inbox/           # Unsorted inbox
└── .obsidian/       # Obsidian config
```

**Wiki-linking:**
```markdown
# Paper: Attention is All You Need

## Key Concepts
- [[transformer-architecture]]
- [[self-attention-mechanism]]
- [[neural-network-architecture]]

## Related Papers
- [[transformer-architecture]] (original)
- [[neural-network-architecture]] (successor)
- [[transformer-architecture]] (application)
```

## Health Check Monitoring

**Endpoint:** `GET http://localhost:8360/health`

**Checks 5 dependencies:**

1. **Vault Accessible** - Can read vault directory?
2. **SurrealDB Connection** - Database responding?
3. **Sheets API Auth** - Credentials valid?
4. **Ollama Service** - Inference service running?
5. **Ollama MCP** - MCP server responding?

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-02-10T14:32:45Z",
  "checks": {
    "vault_accessible": {"status": "healthy", "response_time_ms": 5},
    "surrealdb_connection": {"status": "healthy", "response_time_ms": 12},
    "sheets_api_auth": {"status": "healthy", "response_time_ms": 8},
    "ollama_service": {"status": "healthy", "response_time_ms": 45},
    "ollama_mcp": {"status": "healthy", "response_time_ms": 32}
  }
}
```

## Deployment Checklist

### Prerequisites
- [ ] Python 3.11+ installed
- [ ] Ollama service installed and running
- [ ] SurrealDB installed and running (optional)
- [ ] Google Cloud credentials configured
- [ ] Vault directory accessible

### Installation
```bash
# Clone repositories
cd /home/mike-anderson/dev/cohezion

# Cloud Vault MCP
cd cloud-vault-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ollama MCP
cd ../ollama-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Configuration
```bash
# Set environment variables or create .env file
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
export OLLAMA_URL=http://localhost:11434
export SURREALDB_URL=http://localhost:8000
export GOOGLE_CLOUD_PROJECT=cohezion-477604

# Or create .env file
cat > /home/mike-anderson/dev/cohezion/.env << EOF
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
OLLAMA_URL=http://localhost:11434
SURREALDB_URL=http://localhost:8000
EOF
```

### Verification
```bash
# Test each service
curl http://localhost:8360/health           # Cloud Vault MCP
curl http://localhost:11434/api/tags        # Ollama service
curl http://localhost:8000/health           # SurrealDB

# Run tests
cd cloud-vault-mcp && pytest tests/ -v
cd ../ollama-mcp && pytest tests/ -v

# Check health
curl http://localhost:8360/health | jq .
```

## Performance Targets (Phase A Baseline)

| Operation | Baseline | Target | Notes |
|-----------|----------|--------|-------|
| Ollama query (8B) | ~2350ms | < 2000ms | First call includes model load |
| Ollama query (warm) | ~1850ms | < 1500ms | Subsequent calls (model in memory) |
| Vault read | ~12ms | < 20ms | File system latency |
| SurrealDB batch (100x) | ~850ms | < 700ms | Depends on index efficiency |
| Sheets API call | ~500ms | < 1000ms | Network + auth overhead |
| Health check | ~100ms | < 5000ms | All checks combined |

## Configuration Variables (Complete Reference)

| Variable | Default | Type | Purpose |
|----------|---------|------|---------|
| VAULT_PATH | /vault | string | Obsidian vault directory |
| MCP_HOST | 0.0.0.0 | string | Cloud Vault MCP listen address |
| MCP_PORT | 8360 | int | Cloud Vault MCP port |
| OLLAMA_ENABLED | true | bool | Enable Ollama MCP tools |
| OLLAMA_URL | http://localhost:11434 | string | Ollama service endpoint |
| OLLAMA_TIMEOUT | 30 | int | Ollama request timeout (sec) |
| SURREALDB_ENABLED | true | bool | Enable SurrealDB tools |
| SURREALDB_URL | http://localhost:8000 | string | SurrealDB endpoint |
| SURREALDB_TIMEOUT | 10 | int | SurrealDB request timeout (sec) |
| SHEETS_ENABLED | true | bool | Enable Sheets API tools |
| GOOGLE_CLOUD_PROJECT | cohezion-477604 | string | GCP project ID |
| HEALTH_CHECK_TIMEOUT | 5 | int | Health check timeout (sec) |
| LOG_LEVEL | INFO | string | Log verbosity |
| CACHE_ENABLED | true | bool | Enable query caching |
| MAX_REQUEST_SIZE | 10MB | int | Max request body size |

## Related Documentation
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-ollama-mcp-operations]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-health-checks]]
- [[troubleshooting-mcp-infrastructure]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[2026-02-08-bmad-framework-removal]]
- [[2026-02-09-fastmcp-asgi-integration-fix]]
- [[2026-02-12-cloudflare-tunnel-for-persistent-mcp-remote-access|Cloudflare Tunnel for MCP Remote Access]] — extends this architecture to persistent remote access via Cloudflare tunnel
