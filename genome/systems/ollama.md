---
title: "System Card: Ollama"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, system-card, ollama, inference, embeddings, infrastructure]
card_type: system
status: active
aspect: knower
neural:
  activation: 0.506
  stage: growing
  cluster: specs
---

# System Card: Ollama

> [!abstract] Summary
> Ollama provides local model inference and embedding generation for the Cohezion stack. It hosts 38+ models locally, serving both the Ollama MCP server (port 22360, stdio) for agent access and direct API calls for embedding pipelines. Critical for offline operation and semantic search capabilities.

## Identity

| Field | Value |
|-------|-------|
| **Component** | Ollama |
| **Type** | service |
| **Owner** | Cohezion platform team |
| **Status** | active |
| **Version** | 0.6.x |
| **Source** | `ollama` binary (installed via official script) |
| **Deployed As** | systemd service (`ollama.service`) |

## Connection Details

| Field | Value |
|-------|-------|
| **Host** | `localhost` |
| **Port** | 11434 |
| **Protocol** | HTTP REST |
| **Auth** | None (localhost only) |
| **Health Endpoint** | `GET http://localhost:11434/` |
| **MCP Access** | Ollama MCP server (stdio, port 22360) |

## Dependencies

| Dependency | Type | Required | Notes |
|-----------|------|----------|-------|
| NVIDIA GPU drivers | runtime | Recommended | CUDA for GPU acceleration |
| 16GB+ RAM | runtime | Yes | Model loading requires significant memory |
| ~50GB disk | storage | Yes | Model files (~1-8GB each) |

## Capabilities

### What It Does
- **Local inference:** Run LLMs locally without API keys or internet
- **Embedding generation:** `nomic-embed-text`, `mxbai-embed-large` for vector search
- **Model management:** Pull, run, stop models via CLI or API
- **Concurrency:** Serve multiple models simultaneously
- **Quantization:** Run quantized models (Q4, Q8) for memory efficiency

### What It Does NOT Do
- Does not provide training or fine-tuning
- Does not manage vector indexes (that's [[surrealdb]])
- Does not serve MCP protocol directly (that's the Ollama MCP wrapper)

### Loaded Models (38+)

Key models for Cohezion workflows:

| Model | Size | Use Case |
|-------|------|----------|
| `nomic-embed-text` | 274M | Primary embedding model (768d) |
| `mxbai-embed-large` | 335M | Alternative embedding (1024d) |
| `llama3.2:3b` | 3B | Fast local inference |
| `deepseek-coder-v2` | 16B | Local code generation |
| `mistral:7b` | 7B | General local tasks |

## Configuration

```bash
# Environment
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS=~/.ollama/models

# MCP server wrapper config (in ~/.claude/mcp.json)
# Type: stdio, timeout: 30s, python venv
```

## Monitoring & Health

| Check | Method | Frequency | Alert Threshold |
|-------|--------|-----------|-----------------|
| Server alive | `GET http://localhost:11434/` | Continuous | Restart on failure |
| Model loaded | `ollama list` | On demand | Warn if embedding models missing |
| GPU utilization | `nvidia-smi` | Periodic | >90% sustained |
| Memory usage | `ollama ps` | Periodic | >80% VRAM |

## Known Limitations

- First request after model unload has cold-start latency (~5-15s)
- VRAM limits concurrent large model loading
- No auth — relies on localhost-only binding
- Embedding quality inferior to commercial APIs (OpenAI, Anthropic)

## Reconstruction Steps

> [!tip] Disaster Recovery
> Steps to rebuild this system from scratch using only vault knowledge.

1. Install Ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
2. Start service: `systemctl start ollama`
3. Pull embedding models: `ollama pull nomic-embed-text && ollama pull mxbai-embed-large`
4. Pull inference models: `ollama pull llama3.2:3b && ollama pull mistral:7b`
5. Verify: `curl http://localhost:11434/ && ollama list`
6. Configure MCP wrapper in `~/.claude/mcp.json`

## Security Considerations

- Localhost-only binding — no external access without tunnel
- No authentication mechanism — physical access = full access
- Model files are public weights — no proprietary data risk

## Related

- [[ollama-mcp-server|Ollama MCP Server]] — MCP wrapper providing agent access
- [[semantic-search]] — Concept note on vector search using Ollama embeddings
- [[nomic-embed-text|Embedding Card: nomic-embed-text]] — Primary embedding model card
- [[mxbai-embed-large|Embedding Card: mxbai-embed-large]] — Alternative embedding model card
- [[2026-02-09-ollama-mcp-server]] — Session log from Ollama MCP server implementation

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial system card |
