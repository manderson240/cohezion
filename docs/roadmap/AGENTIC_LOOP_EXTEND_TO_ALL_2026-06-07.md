---
type: roadmap
title: Extend the agentic loop to ALL skills and specialists
date: 2026-06-07
status: keystone landed; extension tracked
owner_loop: swarm_tick (the loop self-drives these via plan_team -> execute)
---

# Extend the agentic loop to all skills & specialists

User directive (2026-06-07): *"eventually extend to all skills and specialists."* The loop
started bound to two agents (vault-keeper, surreal-dba). This is the path to all of them.

## ✅ Keystone — capability routing (landed)
`agentic_loop.route_capability(capability) -> specialist` resolves the OWNING specialist for
ANY capability from the live A2A registry (not hardcoded). `agentic_tick(capability=…)` routes
its knowledge step to that owner. Verified live across 4 specialists:

| capability | owner |
|---|---|
| `report.vault.health` | vault-keeper |
| `audit.surreal.schema` | surreal-dba |
| `monitor.mcp.health` | mcp-specialist |
| `route.llm.tier_dispatch` | platform-coordinator |

This is the unblock: any tick can now route to any of the 7 registered specialists by
capability. (Discriminating test: distinct capabilities → distinct owners.)

## Remaining extension (the loop drives these as `swarm_tick(intent)`)

### All specialists (7 registered, each owns capabilities)
- claude-specialist, gemini-specialist, mcp-specialist, ollama-specialist,
  platform-coordinator, surreal-dba, vault-keeper.
- **Next:** a tick per specialist domain — `agentic_tick(capability=<owned cap>)` — so the
  loop's knowledge/health step is owned by the right specialist for the work at hand. No new
  routing code needed; just point ticks at the capability.

### All skills (225-skill library)
- The swarm already composes agents from skills/capabilities
  (`TeamOrchestrator.generate_agent_spec_from_capability`). `swarm_tick(intent)` decomposes an
  intent into a team that pulls the relevant skills.
- **Next:** wire the skill registry (`src/cohezion/registry/skill_registry.json`) as the
  swarm's skill source so `plan_team` can compose ANY of the 225 skills into a team, and a tick
  can target a skill by name. Falsifiable gate: a `swarm_tick` for an intent that needs skill X
  produces a plan whose agents reference X.

## How it stays OOM-safe & human-visible (invariant)
Every extension runs through `swarm_tick` → `agentic_tick`: Chronos gates the whole team under
memory pressure (the swarm is never spun up when tight), each `TickResult` is reviewable, work
runs on the local silicon fleet ($0, loaded models). Extending to all agents does NOT relax
these — it inherits them.

## Definition of done
- Every registered specialist reachable by capability (keystone: ✅).
- The 225-skill registry wired as the swarm's skill source; a tick can target any skill.
- A driver (`agentic_fleet_tick` / `swarm_tick`) usable with `--specialist <name>` / a skill
  intent, each producing a Chronos-gated, HITL-visible, $0 local run.
