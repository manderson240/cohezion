# Cohezion Integrations

This directory holds bridges and connectors between Cohezion and external platforms.

## Hermes Agent MCP Bridge (NEW)

**File**: `hermes_mcp_bridge.py`

MCP server exposing Cohezion tools to Hermes Agent via stdio JSON-RPC.

Quick Start:
```bash
hermes mcp add cohezion \
  --command python3 \
  --args src/cohezion/integrations/hermes_mcp_bridge.py
```

Tools exposed:
- `cohezion_crawl_codebase` — file tree + line counts
- `cohezion_list_skills` — 225 PRIME skills + local Hermes skills
- `cohezion_get_skill` — read any PRIME skill
- `cohezion_port_skill_to_hermes` — port skill via converter
- `cohezion_batch_port_skills` — batch port
- `cohezion_run_cli` — execute `python -m cohezion <cmd>`
- `cohezion_hermes_status` — bridge diagnostics
- `cohezion_read_source` — line-numbered source read

Full docs: `docs/HERMES_MCP_BRIDGE.md`

## Existing Integrations

| File | Purpose |
|------|---------|
| `agentverse/` | AgentVerse task integration |
| `flume_wiki_bridge.py` | FLUME ↔ Wiki bridge |
| `wiki_mirix_bridge.py` | Wiki ↔ Mirix bridge |
| `obsidian_wiki.py` | Obsidian vault integration |
| `ulogme_bridge.py` | uLogMe time-tracking bridge |
| `kaggle_api.py` | Kaggle API wrapper |
| `competition_rate_limiter.py` | Rate limiting for competitions |
