---
name: graph-context
description: |
  Query the vault's SurrealDB graph for token-efficient context.
  Use when: (1) you need to understand what a note connects to,
  (2) you want to find related concepts without reading files,
  (3) you need cluster-level awareness of a domain,
  (4) you want to find cross-domain bridge notes,
  (5) you need a vault health snapshot.
  Key insight: one graph query (~460 tokens) replaces reading 13 files (~39,500 tokens).
  86x compression ratio. Not all tokens are created equal.
  Automated layers: (6) briefing at session start (~910 tokens, pre-computed in
  metabolism/graph-briefing.md), (7) per-prompt hook injects ~275 tokens of
  graph context automatically via UserPromptSubmit hook.
author: Claude Code
version: 1.1.0
---

# Graph Context — Token-Efficient Vault Awareness

## When to Use

Before reading vault files to understand relationships, query the graph first.
The graph tells you WHAT connects to WHAT and HOW STRONGLY — in 460 tokens
instead of 39,500.

| Situation | Command | Tokens Saved |
|-----------|---------|-------------|
| Understanding a note's connections | `neighborhood <name>` | ~9x vs reading the note |
| Finding related concepts | `search <query>` | ~20x vs grepping files |
| Domain overview | `cluster <name>` | ~50x vs reading all cluster files |
| Cross-domain connections | `bridges <a> <b>` | No file equivalent |
| Vault health check | `stats` | ~100x vs auditing manually |

## Commands

All commands run via `python3 scripts/graph_context.py <command> [args]`.

### neighborhood (alias: n)

Returns a neuron's metadata, all outbound/inbound connections with activation
scores, and top cluster siblings.

```bash
python3 scripts/graph_context.py neighborhood sarfatti
python3 scripts/graph_context.py n "exotic vacuum"
```

### search (alias: s)

Finds neurons by title or tag substring match, sorted by activation.

```bash
python3 scripts/graph_context.py search quantum
python3 scripts/graph_context.py s "back-reaction"
```

### cluster (alias: c)

Returns cluster summary: neuron count, average activation, coherence score,
and top 10 neurons.

```bash
python3 scripts/graph_context.py cluster cortex
python3 scripts/graph_context.py c sensory
```

### hops (alias: h)

N-hop graph traversal from a starting neuron. Default depth: 2.

```bash
python3 scripts/graph_context.py hops sarfatti 2
python3 scripts/graph_context.py h "pilot wave" 1
```

### bridges (alias: b)

Finds neurons that bridge two clusters — cross-domain connectors.

```bash
python3 scripts/graph_context.py bridges cortex sensory
python3 scripts/graph_context.py b prefrontal laboratory
```

### stats

Global vault health snapshot.

```bash
python3 scripts/graph_context.py stats
```

### resolve (alias: r)

Find neuron IDs from partial name matches.

```bash
python3 scripts/graph_context.py resolve bohm
```

### briefing

Compact vault overview for agent session-start context injection. Outputs:
- Vitals (neuron/synapse counts, stage distribution)
- Hot neurons (top 15 by activation)
- Cross-domain bridges (top 10 by connectivity)
- Attention needed (embryos, orphans)
- Highest energy (activation ≥ 0.9)

```bash
python3 scripts/graph_context.py briefing
# Used by cron to pre-compute:
# python3 scripts/graph_context.py briefing > metabolism/graph-briefing.md
```

**Pre-computed version:** `metabolism/graph-briefing.md` (~910 tokens) is regenerated
by `scripts/dreaming-cron.sh` after each dreaming engine run. Read this at session
start instead of running the command live.

## Automated Context Injection (Hook Layer)

Two automated layers run without any explicit command:

### Layer 1: Session-Start Briefing

`metabolism/graph-briefing.md` is injected as startup context via CLAUDE.md directive.
~910 tokens, pre-computed by cron.

### Layer 2: Per-Prompt Hook (UserPromptSubmit)

`scripts/graph_context_hook.py` fires on every user prompt. It:
1. Extracts keywords using sliding 3/2/1-word windows
2. Queries SurrealDB for the best-matching neuron
3. Injects ~275 tokens of context (neuron + 5 outbound + 5 inbound connections)
4. Is silent (zero output) when no match or SurrealDB unavailable

Registered in `.claude/settings.json`:
```json
{
  "type": "command",
  "command": "python3 /home/mike-anderson/vaults/cohezion-vault/scripts/graph_context_hook.py"
}
```

**Hook output format:**
```
--- Graph Context: "Pilot Wave Theory" ---
[████░] 0.85 Pilot Wave Theory (mature, cortex, out:8 in:12)
  Path: cortex/pilot-wave-theory.md
  Tags: quantum, bohmian, determinism
  -> [████░] 0.82 Quantum Potential (cortex)
  <- [███░░] 0.71 David Bohm (sensory)
────────────────────────────────────────
```

**Latency:** ~259ms total (well within 300ms budget). Skip patterns prevent firing
on short replies ("yes", "no", "/commands", numbers).

## Reading the Output

Each neuron line shows:

```
[████░] 0.85 Quantum Entanglement (mature, cortex, out:12 in:8)
 ^^^^^  ^^^^  ^^^^^^^^^^^^^^^^^    ^^^^^^  ^^^^^^  ^^^^^^^^^^^
 bar    act   title                stage   cluster synapses
```

- **Activation bar**: Visual 5-block indicator (0.0 = [░░░░░], 1.0 = [█████])
- **Activation**: 0.0-1.0 score based on content, links, and recency
- **Stage**: embryo → growing → mature → resting
- **Cluster**: Which vault directory/domain
- **Synapses**: outbound and inbound link counts

## Workflow Pattern

1. **Start with search** — find the neuron you care about
2. **Run neighborhood** — see its immediate connections
3. **Use hops for broader context** — 2-hop shows the extended network
4. **Read only the files that matter** — use the graph to decide WHICH files to read

This inverts the typical workflow: instead of reading files to discover relationships,
you discover relationships first and read files only when needed.

## Requirements

- SurrealDB running on port 8001 (check: `ss -tlnp | grep 8001`)
- Context functions installed (run: `curl -X POST http://localhost:8001/sql -u root:root -H "surreal-ns: cohezion" -H "surreal-db: vault" --data-binary @scripts/dba/context_functions.surql`)
- Python 3.10+ (uses stdlib only — no pip dependencies)
