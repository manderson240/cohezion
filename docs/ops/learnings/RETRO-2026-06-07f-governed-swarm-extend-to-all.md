---
date: 2026-06-07
kind: retro
thread: [ops, compound, swarm, autonomous]
prompted_by: retro-watch ([retro:due]) + overnight autonomous grant ("full permissions, follow constitution and charter")
status: captured
related: RETRO-2026-06-07e-oom-recovery-hermes-light-interface.md
---

# Retro — governed swarm + extend-to-all (swarm_tick → routing → skills)

## What landed (verified, committed)
- `swarm_tick` — the loop's work IS wiring: an agentic tick whose improvement work is a
  Cohezion swarm (`plan_team → execute`), spun up INSIDE the Chronos gate so a concurrent
  multi-agent team can never spin up under memory pressure (discriminating test:
  `orch.calls == []` when deferred). Live: 4 agents / 6 tasks planned + executed, $0.
- `route_capability` — generalized the loop's owner-lookup from hardcoded vault-health to
  ANY capability → its owning specialist (vault-keeper / surreal-dba / mcp-specialist /
  platform-coordinator). Keystone for "all specialists."
- Verified the swarm ALREADY reaches the 225 skills via `CapabilityRegistry.find`; locked in
  with `test_skill_reach.py`. "Extend to all skills" was already wired.

## Lessons (reusable)
1. **scripts/ and ~/.claude/* are read-only to BASH but writable by the Edit/Write tools.**
   `ruff format` invoked via bash on `scripts/` fails silently (`os error 30`) — which masquerades
   as a format↔isort "oscillation." Cost real cycles. Rule: when a bash formatter "won't
   converge" on `scripts/`/`~/.claude/`, it's the read-only mount — apply the diff via Edit, and
   never hide a formatter's stderr (`>/dev/null` hid the write error).
2. **Verify-before-build keeps catching pre-existing capability.** This session: VaultKeeper has
   no callable method (declarative card → A2A routing, not a fabricated `report_health`); the 225
   skills are already reachable via the swarm. Both would have been fabricated wires. The probe
   step is cheap; the fabricated coupling is expensive and forbidden by the anti-gaming doctrine.
3. **Governance-around-concurrency makes scaling safe by construction.** Wrapping the swarm in
   `agentic_tick` means Chronos gates the whole team — the OOM hazard that opened the day is the
   governed payoff that closes it. Extending to all agents/skills inherits the safety, doesn't
   relax it.

## Discrepancy flagged (honesty)
`.agent/CONSTITUTION.md` and `.agent/COHEZION_CHARTER.md` (referenced as governance in CLAUDE.md)
**do not exist** — `.agent/` holds only `CAPABILITY_MAP_REDUX.md` + `skills/`. Operated under the
documented principles (honesty, idempotency, no-harm; SPIN/FLUME/HIHO/Expert-Domain-Lattice). The
missing files are a real doc-drift to resolve (restore the docs or fix the CLAUDE.md references).

## Marker
`retro-watch.sh --clear` is read-only to bash (`.retro-pending` ro-bind) — cannot clear from the
sandbox; it auto-clears on its ~1h rate-limit.
