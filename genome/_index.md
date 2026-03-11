---
title: "Specs — Directory Index"
purpose: "System definitions for skills, agents, MCP servers, tools, hooks, and workflows"
type: directory-index
aspect: knower
neural:
  activation: 0.416
  stage: growing
  cluster: specs
---

# Specs — System Definitions

**Purpose:** The vault's reconstruction manual. Everything an agent (or human) needs to rebuild the Cohezion system from scratch — skills, agents, MCP servers, tools, hooks, workflows, and IDE/model integrations.

> [!danger] Why This Exists
> If the repo is lost, if MCP config is corrupted, if `.claude/` is wiped — these specs are the blueprint for reconstruction. Every system definition lives here as a structured, cross-linked, versioned vault note.

**Put here when:** You create, modify, or document a system-level component (skill, agent, MCP server, tool, hook, workflow, or integration).

## Subdirectories

### Component Specs

| Subdirectory | Contents | Naming |
|-------------|----------|--------|
| `skills/` | Skill specs — purpose, triggers, steps, examples | `<skill-name>.md` |
| `mcp-servers/` | MCP server specs — URL, tools catalog, auth, examples | `<server-name>.md` |
| `tools/` | Tool specs — commands, flags, install, examples | `<tool-name>.md` |
| `hooks/` | Hook specs — trigger, logic, alerts, cooldown | `<hook-name>.md` |
| `workflows/` | Workflow specs — phases, gates, transitions | `<workflow-name>.md` |
| `integrations/` | IDE and model provider integration points | `<integration-name>.md` |

### Cards (Structured Documentation)

> [!tip] Card Types
> Cards are standardized documentation formats inspired by [Anthropic System Cards](https://docs.anthropic.com/en/docs/about-claude/model-card), [Google DeepMind Model Cards](https://deepmind.google/models/model-cards/), and the original [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993) paper. Each card type has a `_template.md` — copy it when creating new cards.

| Subdirectory | Card Type | Contents | Naming |
|-------------|-----------|----------|--------|
| `systems/` | System Card | Infrastructure components — services, databases, CLIs, plugins | `<system-name>.md` |
| `models/` | Model Card | AI models — provider, capabilities, benchmarks, safety, cost | `<model-name>.md` |
| `agents/` | Agent Card | Agent definitions — role, tools, triggers, constraints, I/O | `<agent-name>.md` |
| `embeddings/` | Embedding Card | Embedding models & indexes — dimensions, MTEB scores, index config | `<model-or-index-name>.md` |

## Required Frontmatter

### Component Specs

```yaml
---
title: "Component Name"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, <type>]  # type = skill | mcp-server | tool | hook | workflow | integration
source: ".claude/skills/vault-keeper/SKILL.md"  # path to canonical source
status: active  # active | deprecated | draft
---
```

### Cards

```yaml
---
title: "Card Type: Name"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, <card-type>-card]  # system-card | model-card | agent-card | embedding-card
card_type: system | model | agent | embedding
status: active  # active | deprecated | draft
# Additional card-specific fields — see _template.md in each subdirectory
---
```

## Versioning Convention

- `version:` increments on every significant change
- `last_revised:` updates on any edit
- `revision_history:` optional array of `{v, date, change}` entries
- Git history provides full diff trail: `git log --follow specs/<path>`

## Sync Protocol

1. After modifying a skill/agent/tool → update the corresponding spec note
2. `/sync` skill writes vault specs as part of the sync cycle
3. Vault-keeper can detect stale specs (source timestamp > spec timestamp)

## Related

- [[2026-03-05-vault-as-system-of-record]] — ADR establishing this directory's purpose
- [[compound-engineering]] — System definitions compound like knowledge
