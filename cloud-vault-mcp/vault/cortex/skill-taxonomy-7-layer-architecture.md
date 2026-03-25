---
title: "Skill Taxonomy: 7-Layer Architecture"
date: 2026-03-07
tags: [concept, skill-routing, agentic-ai, workflow-orchestration, taxonomy]
related_concepts: [agentic-ai, workflow-orchestration, mcp-model-context-protocol, agent-architecture]
aspect: knower
neural:
  activation: 0.84
  stage: growing
  synapse_in: 1
  synapse_out: 7
---

## Definition

The 7-layer skill architecture describes how Cohezion's ~258 installed capabilities (skills, commands, agents, MCP tools) are organized across 7 distinct source layers, each with different load mechanisms and token costs.

## The 7 Layers

| # | Layer | Location | Count | Load Mechanism |
|---|-------|----------|-------|----------------|
| 1 | BMAD Commands | `.claude/commands/bmad-*.md` | ~90 | Slash commands loading workflow `.md` |
| 2 | Project Commands | `.claude/commands/{audit,deploy,...}.md` | ~10 | Direct slash command execution |
| 3 | Project Skills | `.claude/skills/` | 1 | `Skill()` tool invocation |
| 4 | Global Commands | `~/.claude/commands/` | 7 | Structured workflow slash commands |
| 5 | Global Rules | `~/.claude/rules/*.md` | ~15 | Auto-loaded (enforcement, not invocable) |
| 6 | Plugin Skills | Marketplace + custom | ~55 | `Skill()` tool call |
| 7 | MCP Tools | `.mcp.json` + `~/.claude/mcp.json` | ~80 | `ToolSearch` then direct tool call |

**Effective unique capabilities:** ~198 (after removing ~60 redundant/duplicate entries).

## Key Properties

- **Token cost asymmetry**: Layers 1-4 are lightweight (3-6 lines each); Layer 6 plugins can have verbose descriptions; Layer 7 MCP tools are deferred (loaded only when needed)
- **Load timing**: Rules (Layer 5) load at session start; commands (1-4) load on invocation; plugins (6) load on `Skill()` call; MCP (7) loads on `ToolSearch`
- **Overlap zones**: BMAD BMM/GDS modules share ~12 skill names with domain variants; 3 plugin namespaces duplicate ~17 content creation skills each
- **Routing priority**: Exact match > lifecycle phase > domain > meta > creative > tool need

## BMAD Module Organization

BMAD (Layer 1) is subdivided into 5 modules:
- **BMM** — Business Model Module (product lifecycle: research → PRD → architecture → stories → dev → review)
- **GDS** — Game Development Studio (preproduction → design → technical → production → testing)
- **CIS** — Creative Innovation Studio (brainstorming, design thinking, innovation, storytelling)
- **TEA** — Test Engineering Academy (test design, automation, ATDD, CI, NFR, traceability)
- **BMB** — BMAD Module Builder (meta: create/edit/validate agents, workflows, modules)

## Relationship to Other Concepts

- [[agentic-ai]] — Skills are the action vocabulary of agentic systems
- [[workflow-orchestration]] — The routing decision tree is an orchestration pattern
- [[mcp-model-context-protocol]] — Layer 7; provides external data access for all other layers
- [[agent-architecture]] — Agent personas (Layer 1 agents) define role-based expertise domains

## Experiments

- [[test_routing_pattern]] — test pattern for routing validation

## Decisions

- [[2026-03-07-skill-pruning-consolidation-plan]] — Pruning and consolidation plan to remove ~60 redundant entries identified by this taxonomy

## See Also

- Full taxonomy: `_bmad-output/planning-artifacts/research/technical-skills-taxonomy-research-2026-03-07.md`
- Routing pattern: [[skill-routing-decision-tree]]
- Skills index: `~/vaults/cohezion-vault/skills_index/`
