---
title: "HuggingFace MCP Server"
date: 2026-03-09
version: 1
last_revised: 2026-03-09
tags: [spec, mcp-server, huggingface, infrastructure]
source: "~/.claude/mcp.json"
status: active
aspect: knower
neural:
  activation: 0.500
  stage: growing
  cluster: genome
---

# HuggingFace MCP Server

> [!abstract] Purpose
> Access the HuggingFace ecosystem from Claude Code — search models, datasets, papers, Spaces, and use Inference API. Provided by HuggingFace's official MCP endpoint.

## Connection

| Field | Value |
|-------|-------|
| Type | stdio (via `mcp-remote` proxy to HTTPS) |
| Endpoint | `https://huggingface.co/mcp` |
| Auth | `HF_TOKEN` env var (sourced from `~/dev/cohezion/.env`) |
| Transport | npx `mcp-remote` wraps the HTTP endpoint as stdio |

## MCP Config

```json
{
  "huggingface": {
    "command": "bash",
    "args": [
      "-c",
      "source /home/mike-anderson/dev/cohezion/.env && export HF_TOKEN=\"$HUGGING_FACE_API_TOKEN\" && exec npx -y mcp-remote https://huggingface.co/mcp"
    ]
  }
}
```

## Tools Catalog

### Models

| Tool | Purpose |
|------|---------|
| `search_models` | Search HuggingFace Hub models by query, task, library |
| `get_model_info` | Get model card, config, tags, downloads |
| `list_trending_models` | See currently trending models |

### Datasets

| Tool | Purpose |
|------|---------|
| `search_datasets` | Search HF datasets by query, task |
| `get_dataset_info` | Get dataset card, splits, size |

### Papers

| Tool | Purpose |
|------|---------|
| `search_papers` | Semantic search across HF daily papers |
| `get_paper_info` | Get paper details, abstract, authors |

### Spaces

| Tool | Purpose |
|------|---------|
| `search_spaces` | Search HF Spaces (hosted demos) |

### Inference

| Tool | Purpose |
|------|---------|
| `text_generation` | Run text generation via HF Inference API |
| `text_to_image` | Generate images via HF Inference API |
| `feature_extraction` | Get embeddings from HF models |

> **Note:** Available tools depend on the HF MCP server version. Run `mcp-cli huggingface -d` to see the current full catalog.

## Authentication

The HF token is stored in `~/dev/cohezion/.env` as `HUGGING_FACE_API_TOKEN`. The bash wrapper in the MCP config sources this file and exports it as `HF_TOKEN` (the name the HF MCP server expects).

To rotate the token:
1. Generate new token at https://huggingface.co/settings/tokens
2. Update `HUGGING_FACE_API_TOKEN` in `~/dev/cohezion/.env`
3. Restart Claude Code (the server is spawned per-session)

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `npx` | Node.js 18+ | Package runner |
| `mcp-remote` | latest | HTTP→stdio MCP bridge |
| `~/dev/cohezion/.env` | — | Token source |

## Related

- [[cloud-vault-mcp]] — Local vault MCP server (complementary)
- [[2026-03-05-huggingface-integration-remaining-work]] — Integration roadmap
- [[MOC-platform-infrastructure]] — Infrastructure overview
