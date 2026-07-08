# Diamond Backlog — polishing Cohezion on local inference

Seeded 2026-07-08 from a deterministic facet sweep + this week's verified punch list.
Every item is bounded, gated, and executable at $0 (lane noted). The drain loop:
Ada (`scripts/agents/ada_lovelace.py --daemon`) proposes and annotates;
`~/.cohezion/ada_proposals.jsonl` is the queue; a local session (or
`compound_daemon.py` overnight) picks the top item, executes with its gate,
commits, and logs a vault decision. One facet per session — a diamond is cut
one face at a time.

## Facet map (measured 2026-07-08)

| Facet | Signal | Cut with | Gate |
|---|---|---|---|
| Mechanical lint | 296 auto-fixable ruff findings in src/cohezion (173 I001, 59 UP037, 43 RUF100...) | `uv run ruff check --fix` from a NORMAL shell (this sandbox's writes are blocked) — deterministic tool, no model | `ruff check` clean-er + full pytest unchanged |
| Frontend types | **already 0 tsc errors** (polished this week) | keep it at zero | `npx tsc --noEmit` |
| vault-keeper A2A discovery | regression found 2026-07-08: `test_list_agents_finds_all_7_specialists` fails even in isolation; passed earlier same night | investigate card-discovery path (env-dependent); CPU lane Qwen3-Coder for the trace | that test green in isolation AND full suite |
| SurrealDB watcher | `surrealdb_start_watching` returns success, indexes nothing (verified over 3.5h) | debug vault MCP watcher; NPU lane for log triage | write note → `surrealdb_query` finds it |
| FLUME text-encode | `narrate()` assumes `flume.get_vae().encode(text)`; tests mock it; runtime path unproven | wire a real text→256D path (LemonadeEmbedBridge per LC2, or nomic-embed via :13305) | un-mocked narrate smoke returns coherence in [0,1] |
| JepaGate gravity bias | spec'd (vault §4) but NOT wired — needs ExecutorFactory injection + discriminating tests (W-series discipline) | CPU lane drafts tests-first from the spec; cortex reviews wiring | new discriminating tests + compound suite green |
| Journey-nexus omni pipeline | `_OmniFacade.run()` + image tier are honest NotImplementedError placeholders | wire OmniModel.generate/generate_image behind them | service tests stay green + one live smoke |
| Orphan modules | prior audits in docs/audits/ + ORPHAN_AUDIT list | wire-don't-delete per non-destructive policy; one orphan per session | importer grep shows a production consumer |
| Genesis visuals on real GPU | never seen rendered pixels (container limit) | human: `node scripts/vacuum-verify.mjs` on desktop | FPS number + screenshot judged by human |

## The polish loop (all local)

1. `uv run python scripts/agents/ada_lovelace.py --daemon --interval-min 30` — Ada
   observes each facet's signals and keeps proposing the next cut.
2. A local session drains one queue item: warm the lanes (see the playbook email /
   vault decision 2026-07-08-multi-lane-parallel-local-inference), draft with
   Qwen3-Coder, review with E4B (≥2000 tokens for code review), gate with
   compile/pytest/ruff/tsc, commit with honest attribution.
3. Log the vault decision; Ada's next Note sees the commit and re-prioritizes.
4. `python ~/cohezion-labs/compound_daemon.py --interval 10` overnight runs the
   compound cycle against the same queue.

Rule: local models obey ADD well and KEEP poorly — always diff the contract
surface; deterministic tools before models; tests are the spec wherever they
already exist.
