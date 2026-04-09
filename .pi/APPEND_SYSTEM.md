# Cohezion Project Context

## Project Identity
- **Name**: Cohezion — Compound AI Orchestration
- **Stack**: Python 3.11+, AMD ROCm (Ryzen AI MAX+ 395), SurrealDB, FastAPI
- **Package Manager**: `uv` (NEVER bare pip or pip install)
- **Test Suite**: 6,100+ tests via pytest, run with `uv run pytest tests/ -q`

## Critical Rules
1. **FLUME-First**: New modules MUST encode/decode through FLUME. Start with `encode()` → latent reasoning → `decode()`
2. **Wire-at-Creation**: New modules MUST declare a wiring target at creation time
3. **Vault-First Knowledge**: All session learnings go to vault (`~/vaults/cohezion-vault/`), not MEMORY.md directly
4. **Execute First, Plan Second**: If you can execute NOW with existing tools, do it. No planning phase needed.
5. **No WMD/infrastructure attacks**: Governed by `.agent/CONSTITUTION.md`
6. **Report honest metrics**: 98.8% beats inflated 100% for decision-making

## Key Commands
```bash
uv run pytest tests/ -q              # Full test suite
uv run pytest tests/compound/ -v     # Module tests
make validate                         # Compound loop validation (~18s)
make format && make lint && make all  # Check → fix → verify
```

## Architecture Quick Ref
| Layer | Entry Point |
|-------|-------------|
| Compound | `CompoundExecutor` (11-step pipeline) |
| Swarm | `TeamExecutor`, `CostAwareRouter` (27% savings) |
| FLUME VAE | `flume_vae.py` (256D latent space) |
| Physics | `SpinorState`, cosmogony, gauge theory |
| Knowledge | Vault-First via `vault_find_relevant_context` |
| Data Mesh | Typed data products with SLA for 17+ MCP servers |

## Your Extensions
- **kg_search**: Search the Cohezion Knowledge Graph for learnings, patterns, and project history
- **kg_history**: Retrieve recent agent execution records (journeys)
- **kg_stats**: Get system statistics including total executions and average coherence
- **/retro**: Run a retrospective on the current session
- **web_search/web_fetch**: Search/fetch web content via local Ollama
- **autoresearch tools**: init_experiment, run_experiment, log_experiment (Ctrl+X for dashboard)

## Ollama Cloud Models
When local models aren't sufficient, use these cloud-routed models (Ctrl+P to cycle):
- `kimi-k2.5:cloud` — 262K context, vision + reasoning
- `glm-5.1:cloud` — 202K context, reasoning (default)
- `gemma4:31b-cloud` — 262K context, vision + reasoning
- `minimax-m2.7:cloud` — 204K context, reasoning

## Session Tips
- Use `/retro` at session end to generate a retrospective report
- Use `/autoresearch` for autonomous optimization loops
- Use `@file.md` in prompts to attach files
- Use `!command` to run bash and send output, `!!command` to run without sending
- Use `/compact` when context gets long — compaction is lossy but history persists in JSONL
- Use `/tree` to navigate and branch from any previous point
- Use `/fork` to create a new session from the current branch