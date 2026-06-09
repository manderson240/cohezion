---
title: "Multiperspective Adversarial Audit — :13305 consolidation, the self-improvement loop, inference architecture"
date: 2026-06-09
method: "4 concurrent adversarial reviewers (read-only), synthesized in main context"
trigger: "user request: 'we need a multiperspective adversarial audit' (scope: all of the above)"
---

# Adversarial Audit 2026-06-09

Four concurrent reviewers, each a distinct adversarial lens, each attacking all three targets
(the :13305 consolidation, the /loop self-improvement backlog, the local-inference architecture).
Each was instructed to VERIFY claims and report honest negatives, not manufacture findings.

## Findings → disposition

| # | Lens | Severity | Finding | Disposition |
|---|------|----------|---------|-------------|
| F1 | failure-mode | P1 (active $$) | `health.py` probed dead per-port daemons `:13306-9` while serving moved to `:13305`; `route()`/`extend_claude` marked every local lane DOWN in the router-centric topology → silent escalation to the PAID cloud CLI (local-first inverted) | **FIXED `9f2170df6`** — probe `:13305`, reconcile local lanes UP-via-router; TDD regression test |
| F3 | failure-mode | P0 latent | `build_triune_orchestrator` never set `_max_concurrent` → `run_batch` unbounded `asyncio.gather` on one `:13305`; `_ensure_loaded` had no lock → N concurrent `/api/v1/load` (item-113 saturation/bot-starvation) | **FIXED `9f2170df6`** — `_TRIUNE_MAX_CONCURRENT=4` + double-checked `asyncio.Lock` |
| F4 | failure-mode | P0 latent | `_ensure_loaded` set `_loaded=True` in `finally` even on a FAILED load → next chat let the router auto-load at unbounded ctx (the N3 OOM that bricked the box) | **FIXED `9f2170df6`** — mark loaded only on success; failed preload retries bounded load |
| RIG | scientific-rigor | P1 | `RouterTier` (the Phase-2 production path) had ZERO behavioral tests; the 27 "verified" tests asserted only `.label` strings (pass for a wrong impl). The tested `LemonadeRouterClient` is a parallel UNUSED path | **CLOSED `9f2170df6`** — added `_build_load_payload` FLM-omission + dispatch-routing + response tests |
| SEC | security | P0 | `MCP_API_KEY` (256-bit auth key fronting 40+ vault tools) hardcoded in `run_mcp.py`, in git history since `1aba16266`, AND whitelisted in `.secrets.baseline` (control neutralized, not bypassed). `SURREALDB_PASS` hardcoded too | **FIXED `4d2049d9e`** — de-hardcoded to gitignored `.env`, fail-closed, baseline re-armed. **OPERATOR MUST ROTATE the key** (old value compromised) |
| STRAT | strategy | P0 strategic | "Net-theater": of 117 DONE backlog items, ~1 changed live default-on behavior; 67 report-only + 26 instruments whose only consumers are other instruments. Thread C ("routing feedback → fleet tunes itself") never closed. The `:13305` consolidation is gold-plating that moves MORE traffic onto the OOM-prone auto-loader; the durable win (CI guard) is ~90% of value at ~5% of cost | **PARTIALLY ADDRESSED** — F1/F3/F4 are 4 real default-on behavior changes shipped this session. Phases 4-5 PAUSED pending user descope decision. Graduate-and-measure queued as item 150 |

Guard 148→73 across Phases 0-3. 503 inference tests pass.

## Honest negatives the panel confirmed (controls intact)
- Guard 127→85→73 is real source migration, NOT allow-list gaming (allow-list entries architecturally justified).
- ctx clamp can never emit 0 (`min(max(1,ctx),16384)`); cloud fallback survives `:13305` down (no total outage).
- Router bound to `127.0.0.1`/`[::1]` only; ngrok adapter does not expose `:13305` inbound; deprecated direct-port builders are dead imports, not re-invocable bypasses.
- `--no-verify` commits introduced nothing bad (clean of secrets/keys/large-files/home-paths; deep scanners are push-stage).
- Loop falsifiability discipline is genuinely real (mutation-proven tests, honest NULLs, the Vortex honest-negative).

## Deferred / strategic recommendations (require a user decision or a lanes-up window)
1. **Descope Phases 4-5** (Ollama retirement + guard activation). Risk 2: no confirmed router equivalent for `phi3:mini`/`qwen3-coder:30b`/`deepseek-r1:70b`. Risk 8: unconfirmed NPU/iGPU backend strings. The durable win (CI guard) is already banked. — *user decision, still open.*
2. **Graduate ONE built capability to default-on and measure cost/quality on real traffic** (item 150) — the audit's highest-leverage START. Needs lanes-up + an eval set; it is a needs-experiment item, NOT a safe in-context tick (wiring without measurement is the unverified behavior-change the audit warns against).
3. **F2 (P1) — FIXED:** the tier dispatch path (`DirectLemonadeTier.run`) read only `content`, not `reasoning_content`, so the iGPU `deepseek-r1` thinking model systematically returned '' and escalated. Now falls back to `reasoning_content` (mirrors `fleet.py`), TDD-verified.
