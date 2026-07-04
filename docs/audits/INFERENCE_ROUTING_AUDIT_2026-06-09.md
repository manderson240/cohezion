---
type: audit
date: 2026-06-09
title: "Local inference routing audit — consolidate everything onto :13305"
directive: "All local inference should go through :13305 (the lemonade unified router)"
status: findings (remediation not yet started)
related: [harness.md N1/N2/N3, learnings:mcp_caddy_443_resolution_2026_06_09, decisions/2026-04-29-lemonade-max-loaded-models-1.md]
---

# Inference Routing Audit (2026-06-09)

## Verdict
**No — local inference does NOT all go through `:13305`.** It is fragmented across three
substrates, and the canonical router is the *minority* path.

| Endpoint | Meaning | Files referencing (src/cohezion) |
|---|---|---|
| `:13305` | **canonical lemonade router** (target) | **16** |
| `:11434` | **Ollama** (legacy local backend) | **49** |
| `:13306`–`:13309` | direct per-port lemonade servers (NPU/iGPU/CLaSp/CPU) | **28** |
| `"ollama"` (any) | Ollama mentions overall | 81 |

## Three bypass classes (remediation targets)

### Class A — Ollama `:11434` (largest; 49 files)
Legacy backend. Harness N2 already records the CPU tier migrated Ollama→lemonade(:13309) on
2026-05-21, but the wider codebase never followed. Live wiring includes:
- `swarm/providers/ollama_provider.py` (+ `gemma4_provider.py` subclasses it), `swarm/dynamic_model_router.py`,
  `swarm/smart_router.py`, `swarm/model_manager.py`, `swarm/semantic_cache.py`, `swarm/token_client.py`,
  `swarm/ollama_resilience.py`
- `inference/registry.py`, `inference/langchain_tier.py`, `inference/autoharness.py`, `inference/__init__.py`
- `flume/embedding_provider.py`, `platform/resource_manager.py`, `reliability/monitor.py`,
  `substrate/overload_coordinator.py`, `gateway/{mcp_server,ngrok_adapter,demo_gateway}.py`,
  `skills/mcp_{inference,reliability}_tools.py`, `integrations/telegram_bot.py`
- Likely dead/test/benchmark (lower priority): `competition/orchestrator/benchmark_ollama_phi4.py`,
  `swarm/providers/{tip_spear_provider,multi_model_orchestrator}.py`

### Class B — direct lemonade ports `:13306`–`:13309` (28 files)
The triune/direct-tier architecture that *deliberately* bypasses `:13305` to dodge the router's
auto-load/eviction anomaly (harness N1) — the same anomaly that caused the 2026-06-09 OOM.
Now that `ctx_size` is capped (N3), the bypass rationale is largely retired.
- `inference/direct_tier.py` (`build_direct_{npu,igpu,cpu}_tier`), `inference/triune_orchestrator.py`
  (`npu_port=13306, igpu_port=13307, cpu_port=13309`), `inference/registry.py` (:13307),
  `inference/gaia_adapter.py` (:13306), `compound/dynamic_system_integration.py` (:13307),
  `swarm/providers/lemonade_provider.py` (:13307)
- **In flight**: the CPU tier is being moved to `:13305 backend=cpu` by a running agent (slice 1 of B).

### Class C — scripts that SPAWN dedicated servers
Create the very per-port servers that should be redundant under a router-centric model:
- `~/.claude/hooks/lemonade-warmup.sh` (`lemond --port 13306`), `~/.claude/hooks/post-compact-context.sh`,
  `compound/cron_manager.py`, `skills/LOCAL_INFERENCE_ROUTING.md`

## Why this matters
- One endpoint = the lemonade benefit: on-demand model load + NPU/iGPU/CPU backend dispatch, one
  health surface, one OOM guard, one place to enforce the `ctx_size` cap (N3).
- Fragmentation = N independent OOM/eviction surfaces, the dead `:11434`/`:1330x` servers that
  silently fail, and routing logic duplicated across swarm + inference + gateway.

## Recommended remediation (phased — do NOT mass-edit blind)
1. **Classify live vs dead** — confirm which of the 49+28 files are import-reachable vs test/benchmark/archive
   (cheap import-graph pass). Dead code → delete per non-destructive-wiring (integrate-then-empty).
2. **Single router client** — one `LemonadeRouterClient(base_url="http://localhost:13305/api/v1",
   backend=...)` that all tiers/providers call; backend selected per task (npu/vulkan/cpu).
3. **Retarget Class B** — point `build_direct_*` + triune at `:13305` with per-task backend (CPU slice in flight).
   Tune `max_loaded_models` so NPU+iGPU+CPU models stay resident (no swap-churn) — bounded by RAM, safe post-N3.
4. **Retire Class A** — replace `OllamaProvider`/`:11434` usage with the router client; keep one adapter shim if any caller needs the old interface.
5. **Stop Class C spawns** — warmup/post-compact should warm `:13305`, not spawn `:13306`.
6. **Guard it** — add a harness invariant: no `:1130[6-9]`/`:11434` in live `src/cohezion` inference paths; CI greps for regressions.

## Scope estimate
~50–80 files touched; a multi-phase campaign, not a single PR. Sequence: classify → router client →
retarget B → retire A → stop C → add guard.
