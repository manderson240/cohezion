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

### ✅ All skills (225-skill library) — ALREADY REACHABLE (verified 2026-06-07)
Verify-before-build finding: `plan_team(intent)` already searches `CapabilityRegistry.find()`,
which indexes the 225 skills, and composes the MATCHING skills into the team. Proven live —
skill-specific intents pull their domain skills:

| intent | composed agents |
|---|---|
| "optimize AMD GEMM MXFP4 kernels" | amd-gemm-mxfp4, amd-moe-mxfp4 |
| "audit SurrealDB schema + bitemporal writes" | surrealdb-mcp, surrealdb-operations |
| "run adversarial TDD" | adversarial-tdd, adversarial-testing |

So `swarm_tick(intent)` ALREADY reaches any of the 225 skills relevant to the intent — no new
wiring needed. Locked in by `tests/swarm/test_skill_reach.py` (discriminating: a registry
missing the skills would not surface the domain agent).

## How it stays OOM-safe & human-visible (invariant)
Every extension runs through `swarm_tick` → `agentic_tick`: Chronos gates the whole team under
memory pressure (the swarm is never spun up when tight), each `TickResult` is reviewable, work
runs on the local silicon fleet ($0, loaded models). Extending to all agents does NOT relax
these — it inherits them.

## Definition of done
- Every registered specialist reachable by capability — ✅ (`route_capability`, keystone).
- The 225-skill registry reachable by the swarm; a tick targets skills by intent — ✅
  (already via `CapabilityRegistry.find`, verified + locked by `test_skill_reach.py`).
- A driver usable with a swarm/skill intent producing a Chronos-gated, HITL-visible, $0 local
  run — ✅ (`swarm_tick(intent)`; convenience CLI flag on `agentic_fleet_tick` is the only
  remaining nicety, not a missing capability).

**Net (2026-06-07):** "extend to all skills and specialists" is functionally ACHIEVED — both
are reachable now, governed (Chronos), local ($0), and tested. What remained turned out to be
already wired; the honest residual is CLI ergonomics, not capability.
