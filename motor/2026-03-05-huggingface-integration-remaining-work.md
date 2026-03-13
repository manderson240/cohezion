---
title: "HuggingFace Integration — Remaining Work"
date: 2026-03-05
status: active
tags: [project, huggingface, integration, mcp, embeddings]
aspect: doer
neural:
  activation: 0.61
  stage: growing
  synapse_in: 1
  synapse_out: 4
---

# HuggingFace Integration — Remaining Work

> [!abstract] Context
> The integration map at [[huggingface]] (`specs/integrations/huggingface.md`) is complete. These are the follow-up actions that still need doing.

## Completed

- [x] Research HuggingFace ecosystem (MCP server, Hub API, Inference, MTEB, smolagents, Datasets, LightEval, TGI, Spaces)
- [x] Research Claude Code plugin system, skills.sh, gemini-cli-extensions
- [x] Write integration spec: [[huggingface]] (11 integration points, priority matrix, architecture diagram)

## Remaining Work

### P0 — Do Today

- [x] **Add HF MCP Server to Claude Code config** — Added to `~/.claude/mcp.json` with HF_TOKEN sourced from `.env`. Uses `mcp-remote` as stdio bridge.
- [x] **Create `genome/mcp-servers/huggingface.md`** — Server card documenting the HF MCP server (tools, transport, auth). Modeled on [[cloud-vault-mcp]].

### P1 — Do This Week

- [ ] **Add HF Papers search to `/daily-research` skill** — The HF MCP Server's Papers Semantic Search tool can supplement the existing research pipeline. Update the skill to query HF papers alongside web search.
- [ ] **Run MTEB on current embeddings** — Benchmark `nomic-embed-text` and `mxbai-embed-large` against MTEB leaderboard models. Install `mteb` package. Document results in embedding cards.
- [ ] **Hub API for Model Wrangler** — Install `huggingface_hub`, add `list_models(sort="trending")` to the daily model monitoring.

### P2 — Do This Month

- [ ] **LightEval integration** — Replace/supplement Model Wrangler benchmarking with `lighteval`. 1000+ eval tasks, multi-backend.
- [ ] **RTEB adoption** — Use HF's Retrieval Embedding Benchmark for vault search quality measurement. More relevant than generic MTEB for our use case.
- [ ] **smolagents MCP bridge** — Test `smolagents` CodeAgent calling Cloud Vault MCP tools via Ollama. Could enable lightweight local agent loops.
- [ ] **Inference API fallback** — Configure HF Inference as Ollama fallback for embeddings when local service is down.
- [ ] **Spaces as MCP tools** — Explore adding community AI Spaces (transcription, image gen) as vault tools via HF MCP dynamic discovery.

### P3 — Backlog

- [ ] Claude Code HuggingFace plugin — Build and publish to marketplace
- [ ] TGI as Ollama alternative for production workloads
- [ ] Host COHEZION benchmark datasets on HF Datasets Hub
- [ ] Deploy Cohezion demo on HF Spaces

## Cross-Linking Status

- [ ] Add `[[huggingface]]` link from [[ide-and-model-providers]] (Model Provider section)
- [ ] Add `[[huggingface]]` link from [[MOC-platform-infrastructure]]
- [ ] Create `specs/mcp-servers/huggingface.md` server card

## Key References

- Integration spec: [[huggingface]]
- MCP server template: [[cloud-vault-mcp]]
- [[MOC-platform-infrastructure]]
- [[ide-and-model-providers]]
