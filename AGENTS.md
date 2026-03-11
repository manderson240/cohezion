# Cohezion Vault

Knowledge base for the Cohezion agentic AI framework. Obsidian vault with 1,400+ notes, 11,000+ wiki-links, and 8 Maps of Content.

## Quick Orientation

**Read `VAULT_MANIFEST.md` first.** It maps every directory, explains output routing, and lists conventions. Each directory also has a `_index.md` with purpose, naming rules, and key notes.

## Structure

| Directory | Purpose |
|-----------|---------|
| `concepts/` | Core definitions, frameworks, techniques |
| `papers/` | Research papers and external sources |
| `decisions/` | Architecture Decision Records (ADRs) |
| `patterns/` | Reusable solutions and code patterns |
| `lessons/` | Hard-won knowledge from mistakes |
| `experiments/` | Hypothesis testing and results |
| `projects/` | Multi-session project tracking |
| `inbox/` | Unsorted intake — safe default for any output |
| `daily/` | Session logs and daily notes |
| `canvas/` | Standalone visual canvases |

## Conventions

- **Frontmatter:** YAML with `title`, `date`, `tags` (always arrays: `[tag1, tag2]`)
- **Cross-references:** Obsidian wiki-links `[[note-name]]` — bare filename, no path prefix
- **Rich formats encouraged:** Mermaid diagrams, callouts (`> [!tip]`), LaTeX math, `.canvas` files
- **Templates:** `_template.md` in each content directory — copy when creating notes

## Output Routing

```
Research summaries       → papers/
Techniques/definitions   → concepts/
Architectural choices    → decisions/
Reusable solutions       → patterns/
Mistakes and learnings   → lessons/
PRDs and project plans   → projects/
Hypothesis testing       → experiments/
Skills/agents/tools      → specs/<type>/
MCP server configs       → specs/mcp-servers/
IDE/model integrations   → specs/integrations/
System component docs    → specs/systems/      (system cards)
AI model documentation   → specs/models/       (model cards)
Agent definitions        → specs/agents/       (agent cards)
Embedding model docs     → specs/embeddings/   (embedding cards)
Visual relationship maps → companion .canvas alongside .md, or canvas/
Don't know where it goes → inbox/
```

## Project Artifacts — MANDATORY

**All project artifacts belong in the vault.** PRDs, architecture docs, epics, stories, and specs are vault notes — not ephemeral output. The vault is disaster recovery for institutional memory.

| Artifact | Directory |
|----------|-----------|
| PRD / Requirements | `projects/YYYY-MM-DD-name.md` |
| Architecture Decision | `decisions/YYYY-MM-DD-name.md` |
| Spike / Investigation | `experiments/YYYY-MM-DD-name.md` |
| Retrospective | `retrospectives/YYYY-MM-DD-name.md` |
| Runbook / How-to | `patterns/name.md` |

Cross-link everything: ADRs link to PRDs, PRDs link to concepts and lessons.

## Entry Points (Maps of Content)

| Topic | MOC |
|-------|-----|
| Agent architecture | `concepts/MOC-agentic-ai.md` |
| Quantum physics | `concepts/MOC-quantum-physics.md` |
| Vault structure | `concepts/MOC-vault-architecture.md` |
| Infrastructure | `concepts/MOC-platform-infrastructure.md` |
| Machine learning | `concepts/MOC-machine-learning.md` |
| Astrophysics | `concepts/MOC-astrophysics.md` |
| Methodology | `concepts/MOC-compound-engineering.md` |
| AI safety | `concepts/MOC-safety-alignment.md` |

## Build Commands (Tooling)

```bash
# Cohezion Engine CLI
cd tools/cohezion-engine && uv pip install -e .
cz --help

# 3D Graph Plugin
cd obsidian-plugin/3d-graph-plugin && npm install && npm run dev

# MCP Server
cd mcp-server && pip install -e ".[dev]" && pytest
```

## MCP Integration

- **Cloud Vault MCP** on port 8360 — programmatic vault access (VaultOps, CompoundOps, ObsidianOps, SurrealDB)
- **Ollama MCP** on port 22360 — semantic search and embeddings

## Vault Health

The vault maintains these invariants automatically:
- 0 orphan notes, 0 frontmatter issues, 0 broken links
- 8+ Maps of Content, 6+ avg wiki-links per note
- Proactive hooks detect and alert on violations

## See Also

- `VAULT_MANIFEST.md` — full directory map, rich format specs, agent workflow
- `CLAUDE.md` — Claude Code-specific instructions and tool conventions
