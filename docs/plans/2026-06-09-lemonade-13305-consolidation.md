---
title: "Route ALL local inference through :13305 lemonade router (lasting consolidation)"
status: PENDING
worktree: Yes
date: 2026-06-09
audit: docs/audits/INFERENCE_ROUTING_AUDIT_2026-06-09.md
related:
  - harness.md N1/N2/N3/CL1-3/CC2
  - docs/audits/INFERENCE_ROUTING_AUDIT_2026-06-09.md
  - decisions/2026-04-29-lemonade-max-loaded-models-1.md
slug: lemonade-13305-consolidation
---

# Lemonade :13305 Consolidation Plan

## Objective

Route ALL local inference in `src/cohezion/**` through the canonical lemonade unified router at
`:13305`, retiring Ollama (`:11434`) and the direct per-port lemonade servers (`:13306–:13309`)
as active inference endpoints. The fix is permanent because a CI grep guard (Phase 0) will
fail the build if `:11434` or `:1330[6-9]` reappears in any live inference path.

## Hard Pre-Condition (MUST be satisfied before worktree is created)

> **CPU-lane agent must land first.** `RouterCpuTier` / `build_router_cpu_tier` are being
> added to `direct_tier.py` and `triune_orchestrator.py` by a running parallel agent. This
> plan's worktree MUST be branched from the commit that merges that work. If the CPU-lane PR
> has not yet merged, open the worktree only after merge. Two agents editing those two files
> simultaneously will produce a merge conflict that invalidates both changes.
>
> Verification: `grep "RouterCpuTier\|build_router_cpu_tier" src/cohezion/inference/direct_tier.py`
> must return results before Phase 0 begins.

---

## Specialist Assignment Table

| Work Package | Owner Specialist | Rationale |
|---|---|---|
| Phase 0 — canonical client + CI guard skeleton | `compound-engineering-specialist` + `autoharness-specialist` (parallel) | Client is the foundation all later phases depend on; guard is the permanent durability element |
| Phase 0 — model-catalog discovery & mapping | `compound-engineering-specialist` | Needs inference domain context to enumerate Ollama models used by live callers |
| Phase 1 — swarm/ migration (Class A heavy callers) | `swarm-orchestration-specialist` | Owns the 15 swarm files: providers, routers, model_manager, caches, democratic_debate |
| Phase 2 — inference/ retarget (Class B direct ports) | `compound-engineering-specialist` | Owns direct_tier, triune, registry, gaia_adapter, unified_orchestrator |
| Phase 2 — CLaSp exception ruling | `compound-engineering-specialist` | Architectural call: retain or retire dual-port speculative decoding |
| Phase 3 — gateway/ + skills/ + MCP tools | `mcp-specialist` | Owns gateway/mcp_server, gateway/ngrok_adapter, gateway/demo_gateway, skills/mcp_inference_tools, skills/mcp_reliability_tools |
| Phase 3 — SurrealDB token accounting paths | `surreal-dba` | inference paths that call token-accounting records (token_client, session usage tracking) |
| Phase 4 — retire OllamaProvider, stop Class C spawns | `compound-engineering-specialist` + `swarm-orchestration-specialist` | OllamaProvider retirement spans both domains; Class C hooks need compound context |
| Phase 4 — healing/ + agents/ + platform/ + substrate/ | `swarm-orchestration-specialist` | These modules use Ollama only for health probes; migration is mechanical but needs test coverage |
| Phase 5 — activate guard, verify, persist decision | `autoharness-specialist` + `vault-keeper` | Guard activation is a CI change; vault-keeper writes the decision record |

---

## Phase Sequence

### Phase 0 — Canonical client + CI guard skeleton (pre-work, ~3 days)

All later phases depend on this landing first. Two work-packages run in parallel.

#### 0a. Canonical `LemonadeRouterClient` (compound-engineering-specialist)

**Files to create/modify:**
- `src/cohezion/inference/router_client.py` — NEW (the canonical client, leaf module)
- `src/cohezion/inference/__init__.py` — expose `LemonadeRouterClient` in `__all__`

**Design contract for the canonical client:**

```
LemonadeRouterClient(
    base_url: str = "http://localhost:13305",
    model_id: str,
    backend: Literal["npu", "vulkan", "cpu", "auto"] = "auto",
    ctx_size: int = 16384,          # N3: capped ≤16384
    max_tokens: int = 512,
    temperature: float = 0.3,
    timeout_s: float = 60.0,
)
```

The client speaks OpenAI `/v1/chat/completions` (same shape as `RouterCpuTier`). It also
exposes `async load(save_options=True)` for explicit pre-loading with bounded ctx (N3
compliance: never let router auto-load at ctx_size=0). `RouterCpuTier` in `direct_tier.py`
is the prototype -- the canonical client subsumes it.

**Placement rule:** This module MUST be a leaf — it imports only `httpx` and stdlib. No
imports from `swarm/`, `compound/`, or `inference/orchestrator`. This is the cycle-safety
constraint: `swarm/providers` will import from it, so if it imports from `swarm/` we get a
circular dependency identical to the one documented in `inference/__init__.py:34-43`.

**Backend parameter validation (Phase 0 discovery item):** The only confirmed backend
string from production code is `llamacpp_backend=cpu` (RouterCpuTier) and `llamacpp_backend=rocm`
(model_pool_manager). The NPU backend string for the lemonade load API (`npu`, `xdna2`, `flm`,
or something else) is NOT yet confirmed in source. Compound-engineering-specialist MUST:
1. Query `GET :13305/api/v1/models` on the running router to enumerate loaded models and backend labels.
2. Run `POST :13305/api/v1/load {"model_name": "llama3.2-1b-FLM"}` and inspect the response for the
   correct backend key.
3. Record confirmed backend strings in a `BACKEND_STRINGS.md` note (or inline in `router_client.py`
   docstring) before Phase 2 begins.

If the NPU and iGPU backend strings cannot be confirmed offline (router down), Phase 2 NPU/iGPU
migration is deferred until a live confirmation run; Phase 2 CPU work proceeds unblocked.

**Phase 0a test gate:**
```python
# tests/unit/inference/test_router_client.py
# 1. Instantiate LemonadeRouterClient — no imports from swarm/compound/orchestrator
# 2. Mock httpx to return OpenAI-shaped completions; verify response parsing
# 3. Verify ctx_size is clamped to ≤16384 (N3)
# 4. Verify `load()` posts to /api/v1/load with save_options=True
# 5. Verify the client's label attribute is "router:<model_id>"
# Cycle guard: python -c "import cohezion.inference.router_client" in a venv that has
#   swarm/ removed from sys.path must succeed.
```

#### 0b. CI guard (autoharness-specialist) — runs in parallel with 0a

**Files to create/modify:**
- `scripts/ci/check_inference_port_bypass.sh` — NEW grep-based CI check
- `.claude/rules/harness.md` — NEW invariant section at end

**CI guard specification:**

```bash
# scripts/ci/check_inference_port_bypass.sh
#
# Fails the build if :11434 or :1330[6-9] appears in any live src/cohezion/** inference path.
# "Live" = import-reachable, not in the allow-list below.
#
# Allow-list (inline markers take precedence over file-level skips):
#   # allow-direct-port: <reason>     <- single line skip
#
# Whole-file allow-list (never import-reachable inference paths):
#   tests/**
#   src/cohezion/competition/orchestrator/benchmark_ollama_phi4.py
#   src/cohezion/swarm/providers/tip_spear_provider.py
#   src/cohezion/swarm/providers/multi_model_orchestrator.py
#   src/cohezion/inference/direct_tier.py  (retains build_direct_* for legacy reference)
#   src/cohezion/inference/clasp_tier.py   (CLaSp retains :13307/:13308 — see Phase 2 exception)
#   docs/**
#   *.md
```

The regex pattern is: `\b(11434|1330[6-9])\b` (word-boundary match, NOT colon-prefixed).
Using word boundaries rather than a leading colon is critical: a colon-prefixed pattern misses
bare integer defaults such as `npu_port: int = 13306`, `port: int = 13307`, `lemonade_port: int = 13307` —
exactly the Class B direct-tier signatures the guard exists to prevent from re-appearing.
Verify the pattern against `triune_orchestrator.py` before committing: it MUST flag
`npu_port: int = 13306` / `igpu_port: int = 13307` / `cpu_port: int = 13309`.
The check EXCLUDES `:13305` because `13305` is not in `1330[6-9]`.
Pattern accuracy: `\b1330[6-9]\b` matches 13306, 13307, 13308, 13309 and NOT 13305.

The guard is committed but NOT activated (does not run in CI) until Phase 5. It DOES run
locally as a pre-commit step from Phase 0b forward so that the guard design can be validated.

**Harness.md invariant (to be added in Phase 5 when activated):**

```
### N4: No direct port bypass in live inference paths
- Pattern :(11434|1330[6-9]) must not appear in src/cohezion/**
  outside the allow-list (tests/, benchmark files, direct_tier.py legacy builders,
  clasp_tier.py exception — see allow-list in scripts/ci/check_inference_port_bypass.sh)
- Inline override: # allow-direct-port: <reason> on any line grants per-line exemption
- Verification: bash scripts/ci/check_inference_port_bypass.sh exits 0
```

**Phase 0b deliverable:** `check_inference_port_bypass.sh` runs locally and exits 0 (no
live files yet migrated, all legacy files are in the allow-list).

#### 0c. Model-catalog discovery and mapping (compound-engineering-specialist)

This is a required DECISION GATE before Phase 4 (Ollama retirement). Perform before or
during Phase 1 so the decision is ready before Phase 4 starts.

**Ollama models in live caller scope (from audit scan):**

| Caller file | Model requested | Purpose |
|---|---|---|
| `agents/base.py` | `model_name` (parameterized) | Agent inference |
| `swarm/model_manager.py` | phi3:mini, deepseek-r1, qwen3-coder | Swarm model pool |
| `inference/registry.py:430-446` | qwen3-coder, deepseek-r1, phi3:mini | Task specialists |
| `flume/embedding_provider.py` | Ollama embedding model | Embeddings |
| `substrate/overload_coordinator.py` | (first available Ollama model) | Offload |
| `healing/__init__.py`, `platform_audit.py` | (health probe only, no model) | Health check |

**Action:** For each live-caller model, confirm whether the lemonade router at `:13305`
serves an equivalent model. If no equivalent exists, document as a user decision: either
(a) accept capability loss, (b) add the model to the lemonade catalog, or (c) retain the
Ollama shim for that specific caller only. Models used ONLY for health probes (no actual
inference) can be trivially replaced with a router health probe.

---

### Phase 1 — swarm/ migration (swarm-orchestration-specialist, ~3 days)

**Pre-condition:** Phase 0a canonical client is merged.

**Work package — 15 swarm files (Class A heavy callers):**

| File | Change |
|---|---|
| `swarm/providers/ollama_provider.py` | Retain class (non-destructive); add `LemonadeRouterOllamaAdapter` shim that forwards `generate()` calls to `LemonadeRouterClient` using the model-catalog map from Phase 0c. Mark `OllamaProvider.generate()` as deprecated in docstring. |
| `swarm/providers/lemonade_provider.py` | Update default `base_url` from `:13307` to `:13305`; expose `backend` param. |
| `swarm/providers/gemma4_provider.py` | Inherits OllamaProvider — once OllamaProvider is updated to use router via shim, this is automatically migrated. Verify. |
| `swarm/dynamic_model_router.py` | Line 605: replace `/api/generate` Ollama call with `LemonadeRouterClient.chat()`. |
| `swarm/compute_backend_router.py` | Line 536/572: replace direct `:13306` + `:11434` calls with `LemonadeRouterClient` using `backend="npu"` (pending Phase 0a confirmation) and `backend="cpu"`. |
| `swarm/smart_router.py` | Replace `ollama_host` default with router URL; delegate to canonical client. |
| `swarm/model_manager.py` | `OLLAMA_HOST` constant → `LEMONADE_ROUTER_URL = "http://localhost:13305"`. Audit all downstream uses. |
| `swarm/semantic_cache.py` | Replace `ollama_base_url` with router URL (embeddings via router, or lemonade embedding endpoint). |
| `swarm/token_client.py` | `ollama_base_url` → router URL. **surreal-dba review gate:** token_client feeds token accounting records to SurrealDB — verify the accounting model still works when the provider name is `lemonade` not `ollama`. |
| `swarm/ollama_resilience.py` | `_DEFAULT_BASE_URL` → router URL; rename to `LemonadeResilientRetry` if scope permits, otherwise update in place. |
| `swarm/compound_client.py` | `ollama_host` default → router URL. |
| `swarm/swarm_types.py` | `SwarmConfig.ollama_base_url` → add `lemonade_router_url` field with default `"http://localhost:13305"`; keep `ollama_base_url` as deprecated alias. |
| `swarm/democratic_debate.py` | `ollama_host` → router URL. |
| `swarm/lemonade_manager.py` | Default port `13307` → `13305`. |
| `swarm/agents/base_scout.py` | `ollama_url` → router URL. |
| `swarm/agents/eigent_agent.py` | `lemonade_url: str = "http://localhost:13307"` → `"http://localhost:13305"`. |

**Non-destructive-wiring rule for OllamaProvider:** The `OllamaProvider` class MUST NOT be
deleted. Instead, its `generate()` body should delegate to `LemonadeRouterClient` (model-catalog
map applied). The `register_model_provider("ollama", ...)` call stays; existing callers that
construct `OllamaProvider` continue to work but now route through `:13305`. The retirement of
the class shell is a downstream bookkeeping step after full verification.

**Protocol shape note (critical):** Ollama callers use `/api/generate` with `prompt` (string).
The lemonade router uses OpenAI `/v1/chat/completions` with `messages` (list). The canonical
client handles this translation. The shim layer must not silently drop structured input -- the
Ollama `options` dict (num_predict, temperature, top_k etc.) maps to the `LemonadeRouterClient`
constructor params, NOT to arbitrary kwargs. The shim must be explicit about what it passes.

**Phase 1 test gate:**
- `uv run pytest tests/swarm/ -q` passes on migrated files.
- Integration test: construct `OllamaProvider` → call `generate("phi3:mini", "hello")` → router
  mock at `:13305` receives OpenAI-shaped request. Verify model-catalog translation.
- `swarm/swarm_types.py`: `SwarmConfig()` instantiation has no regression (deprecated field alias
  still accepted).

---

### Phase 2 — inference/ retarget, Class B direct ports (compound-engineering-specialist, ~2 days)

**Pre-condition:** Phase 0a merged; backend strings confirmed (Phase 0c discovery item).

**CLaSp exception ruling (decision gate — required before this phase starts):**

`inference/clasp_tier.py` + `triune_orchestrator.py` lines 108-133 implement speculative
decoding across TWO ports: E2B draft (`:13308`) + E4B verify (`:13307`). The lemonade router
has no known mechanism for server-side speculative decoding across backends — this is a
single-request feature that requires two model instances coordinating at sub-request granularity.

Options (present to user before this phase):
1. **Retain CLaSp as-is** — add `clasp_tier.py` to the CI guard allow-list; document explicitly.
   Both `:13307` and `:13308` remain valid in `clasp_tier.py` only.
2. **Retire CLaSp** — accept throughput regression (CLaSp delivers ~1.5-2.5x iGPU speedup when
   draft acceptance ≥50%); retarget iGPU tier to single-model router backend.

Default recommendation: Option 1 (retain). The CLaSp speedup is architecturally unique and
has no router-level equivalent. The CI guard allow-list makes the exception auditable.

**Files to migrate:**

| File | Change |
|---|---|
| `inference/direct_tier.py` | `build_direct_npu_tier`, `build_direct_igpu_tier`, `build_direct_cpu_tier` get updated to use `LemonadeRouterClient` internally (or are deprecated in favor of `LemonadeRouterClient` factory functions). `RouterCpuTier` is subsumed by canonical client. Legacy `build_direct_*` builders retained for tests with `# allow-direct-port: legacy builder` markers. |
| `inference/triune_orchestrator.py` | NPU and iGPU tiers: replace `DirectLemonadeTier(port=13306/13307)` with `LemonadeRouterClient(backend="npu"/"vulkan")` — pending backend string confirmation. CPU tier already uses `RouterCpuTier` (CPU-lane agent). |
| `inference/registry.py` | Lines 210-446: all `endpoint="http://localhost:1330x"` and `endpoint="http://localhost:11434"` → `endpoint="http://localhost:13305"`. The `runtime_backend` field on each `ModelEntry` already captures the intended backend; update endpoint to the router. |
| `inference/gaia_adapter.py` | Lines 160/191: `http://localhost:13306/v1` → `http://localhost:13305/v1`. |
| `inference/__init__.py` | Fix stale doc-comment (lane layout lists `:13306`-`:13309` and `:11434`). Replace with router-centric description. |
| `compound/dynamic_system_integration.py` | Lines 605/615: `http://localhost:13307` → `http://localhost:13305`. |

**Phase 2 test gate:**
- CL1-3 invariant checks all pass (classifier routes NPU/iGPU/CPU tasks correctly).
- `uv run pytest tests/inference/ -q` passes.
- N2 invariant preserved: `llama3.2-1b-FLM` is still the NPU model, now served by router.
- CC2 invariant preserved: `feynman_path_weight(0.5, 0.0) > feynman_path_weight(1.0, 0.01)`.

---

### Phase 3 — gateway/ + skills/ + MCP tools (mcp-specialist + surreal-dba, ~2 days)

**Pre-condition:** Phase 0a merged; Phase 0c model-catalog map available.

**mcp-specialist work package:**

| File | Change |
|---|---|
| `gateway/mcp_server.py` | Lines 79/95/194/387: `ollama_url` default and references → `lemonade_router_url = "http://localhost:13305"`. Parameter rename in MCP tool schema (backwards-compat alias for `ollama_url` input). |
| `gateway/ngrok_adapter.py` | Lines 23/107: `fallback_ollama_url` → `fallback_router_url = "http://localhost:13305"`. |
| `gateway/demo_gateway.py` | Lines 16/66: `ollama_url` → router URL. |
| `skills/mcp_inference_tools.py` | Lines 67/187: `/api/generate` calls → canonical client; MCP tool descriptions updated. |
| `skills/mcp_reliability_tools.py` | Audit for `:11434`/`:1330x` — migrate any found. |

**surreal-dba review gate (runs in parallel with mcp-specialist):**

`swarm/token_client.py` feeds token usage into SurrealDB records. When the provider changes
from `"ollama"` to `"lemonade"`, existing queries that GROUP BY provider name will see a new
value. surreal-dba must:
1. Audit `src/cohezion/**` for SurrealQL queries referencing `provider = 'ollama'`.
2. Determine if existing time-series records need a migration (backfill `provider = 'lemonade'`
   for records from the migration date forward) or if they can coexist.
3. If a migration is needed, provide a migration script alongside the Phase 3 PR.

**Phase 3 test gate:**
- `uv run pytest tests/gateway/ tests/skills/ -q` (if tests exist; otherwise: smoke import test).
- MCP integration test: `scripts/ci/mcp_integration_smoke_test.py` passes.
- SurrealDB: token accounting records show `provider = 'lemonade'` after Phase 3.

---

### Phase 4 — retire OllamaProvider shell + stop Class C spawns (all relevant specialists, ~2 days)

**Pre-condition:** Phases 1, 2, 3 all merged. Phase 0c catalog map confirmed complete.

#### 4a. Retire OllamaProvider + healing/ + platform/ + substrate/ (swarm-orchestration-specialist)

**Actions:**
- `swarm/providers/ollama_provider.py`: OllamaProvider `generate()` already delegates to router
  (Phase 1). Add module-level `__deprecated__ = True` marker; add a FIXME comment with target
  removal date. Do NOT delete the class — it stays as an empty integration husk per non-destructive-wiring.
- `reliability/monitor.py`: Replace `:11434` Ollama health probe with `:13305` liveness probe.
- `healing/__init__.py` line 290: `:11434/api/tags` health probe → `GET :13305/v1/models`.
- `healing/platform_audit.py` line 153: same.
- `platform/resource_manager.py` lines 152/341: `_OLLAMA_PS_URL` → `_ROUTER_MODELS_URL = "http://localhost:13305/v1/models"`.
- `substrate/overload_coordinator.py` lines 391-441: Ollama health probes + offload calls → router.
- `flume/embedding_provider.py` lines 41/204: `:11434` default → `:13305`. If the embedding
  endpoint differs on lemonade vs Ollama, provide the correct lemonade embedding path.
- `integrations/telegram_bot.py` line 335: remove `:11434` from the unreachable message (only
  router should be listed as a fallback).

**Dead code (per audit — do NOT migrate, add to CI allow-list with reason):**
- `competition/orchestrator/benchmark_ollama_phi4.py` — benchmark/archive, allow-list marker: `# allow-direct-port: benchmark archive, not import-reachable`
- `swarm/providers/tip_spear_provider.py` — likely dead per audit, allow-list marker: `# allow-direct-port: dead provider, no live callers confirmed`
- `swarm/providers/multi_model_orchestrator.py` — same

#### 4b. Stop Class C server spawns (compound-engineering-specialist)

| File | Change |
|---|---|
| `~/.claude/hooks/lemonade-warmup.sh` | Replace `lemond --port 13306` spawn with a warmup POST to `:13305/api/v1/load` for `llama3.2-1b-FLM`. |
| `~/.claude/hooks/post-compact-context.sh` | Line 94: `NPU:13306` liveness check → `:13305` check. Line 95: NPU restore instruction → router warmup. |
| `compound/cron_manager.py` | Line 124-126: `lemond --port 13306` action → router warmup action. |
| `skills/LOCAL_INFERENCE_ROUTING.md` | Update topology diagram and startup commands to reflect router-centric model. |

**Phase 4 test gate:**
- CI on `healing/` and `platform/` modules passes.
- OllamaProvider: `uv run pytest tests/swarm/providers/ -q` — tests that previously mocked
  `:11434` now mock `:13305`.
- Warmup hook: `bash ~/.claude/hooks/lemonade-warmup.sh --dry-run` (if dry-run exists) or
  smoke test against a running `:13305`.

---

### Phase 5 — verify, activate guard, persist decision (autoharness-specialist + vault-keeper, ~1 day)

**Pre-condition:** Phases 1-4 all merged.

#### 5a. Activate CI guard (autoharness-specialist)

1. Remove `# guard-inactive` comment from `scripts/ci/check_inference_port_bypass.sh`.
2. Add guard to the project's CI pipeline (reference `scripts/ci/` invocations in Makefile or `.github/`).
3. Run guard against the current codebase — must exit 0.
4. Add `N4` invariant to `~/.claude/rules/harness.md` (text in Phase 0b above).
5. Verify CL1/CL2/CL3 invariants still pass (classifier routing).
6. Run full harness check: `python3 .claude/rules/harness_check.py`.

#### 5b. Invariants-preservation final check

| Invariant | Check |
|---|---|
| N1 (NPU startup, llama3.2-1b-FLM) | Router now serves FLM on demand; N1 warmup path updated in Phase 4b. Verify `llama3.2-1b-FLM` loads via `:13305`. |
| N2 (triune NPU = llama3.2-1b-FLM) | `grep "llama3.2-1b-FLM" src/cohezion/inference/triune_orchestrator.py` still returns result. |
| N3 (ctx_size ≤16384 on heavy models) | `LemonadeRouterClient.__init__` clamps `ctx_size = min(max(1, ctx_size), 16384)`. Verify no caller passes 0. |
| CL1 (task_classifier routes all 8 types) | `python3 -c "from cohezion.inference.task_classifier import classify; ..."` |
| CL2 (no false GPU escalation on short categorical) | Full CL2 test. |
| CL3 (what-is/describe → NPU) | Full CL3 test. |
| CC2 (Feynman local beats cloud at $0.01) | `feynman_path_weight(0.5, 0.0) > feynman_path_weight(1.0, 0.01)` |
| ResourceGuard OOM gate | `build_triune_orchestrator()` with RAM < 16 GB mock → cloud-only. |

#### 5c. Persist decision (vault-keeper)

1. Write vault decision: `~/vaults/cohezion-vault/decisions/2026-06-09-lemonade-13305-consolidation.md`
   with `decision_reasoning` (one canonical endpoint), `reasoning_chain` (audit findings, OOM history,
   protocol migration rationale), and `outcome` (files changed, guard activated, invariants preserved).
2. Update `~/.claude/rules/local-inference-default.md`: replace per-port topology with
   router-centric topology; remove `:13306`-`:13309` from startup checklist.
3. Update harness.md invariant N1 to reflect router-based warmup.

---

## Dependency Ordering (directed acyclic graph)

```
Phase 0a (canonical client)
    ├─► Phase 1 (swarm/)
    ├─► Phase 2 (inference/)
    └─► Phase 3 (gateway/skills/)

Phase 0b (CI guard skeleton)
    └─► Phase 5a (activate guard)  [guard committed but inactive until Phase 5]

Phase 0c (model catalog map)
    └─► Phase 4a (retire OllamaProvider)  [decision gate]

CPU-lane agent PR (hard pre-condition)
    └─► Phase 0a (worktree creation)

Phase 1 + Phase 2 + Phase 3
    └─► Phase 4a (retire OllamaProvider + healing/platform/substrate)
    └─► Phase 4b (stop Class C spawns)

Phase 4a + Phase 4b
    └─► Phase 5a (activate guard)
    └─► Phase 5b (invariants check)
    └─► Phase 5c (persist decision)
```

---

## Per-Phase Test Gates Summary

| Phase | Gate | Owner |
|---|---|---|
| 0a | `tests/unit/inference/test_router_client.py` (new); cycle import test | compound-engineering |
| 0b | `bash scripts/ci/check_inference_port_bypass.sh` exits 0 locally | autoharness |
| 1 | `uv run pytest tests/swarm/ -q`; router mock receives OpenAI-shaped request | swarm-orchestration |
| 2 | `uv run pytest tests/inference/ -q`; CL1-3 pass; N2 preserved | compound-engineering |
| 3 | `scripts/ci/mcp_integration_smoke_test.py`; SurrealDB provider field check | mcp-specialist + surreal-dba |
| 4 | `uv run pytest tests/swarm/providers/ tests/healing/ -q`; warmup hook smoke test | swarm-orchestration |
| 5 | Guard exits 0; full harness check passes; all N1-N3/CL1-3/CC2 invariants pass | autoharness |

---

## Invariants-Preservation Checklist

- [ ] N1: NPU startup switches from `lemond --port 13306` to router warmup POST; `llama3.2-1b-FLM` still the NPU model
- [ ] N2: `grep "llama3.2-1b-FLM"` still in triune_orchestrator.py NPU tier
- [ ] N3: No `ctx_size=0` passed to heavy models; `LemonadeRouterClient` clamps to ≤16384
- [ ] CL1: task_classifier routes all 8 test cases; overhead < 500µs
- [ ] CL2: short categorical outputs use `quality_gate_chars=0` (no false GPU escalation)
- [ ] CL3: what-is/describe → NPU with confidence 0.65-0.70
- [ ] CC2: `feynman_path_weight(0.5, 0.0) > feynman_path_weight(1.0, 0.01)` (local beats cloud)
- [ ] ResourceGuard OOM gate: RAM < 16 GB → cloud-only orchestration, no local tier load attempts
- [ ] N4 (new): CI guard installed, activated, exits 0 on merged codebase

---

## Risks and Mitigations

### Risk 1: Protocol shape mismatch (HIGH)
**What:** Ollama callers use `/api/generate` with a flat `prompt` string and Ollama-specific
options. The router speaks OpenAI `/v1/chat/completions` with `messages` list. Silent
translation bugs will produce empty responses or garbled completions.

**Mitigation:** The canonical client is the ONLY place where Ollama→OpenAI translation occurs.
The Phase 1 shim wraps `OllamaProvider.generate()` to call the canonical client. Phase 1 test
gate explicitly checks "same prompt → equivalent completion via OpenAI shape" using a router mock,
not just endpoint reachability.

### Risk 2: Model-catalog capability loss (HIGH)
**What:** Ollama serves `phi3:mini`, `qwen3-coder:30b`, `deepseek-r1:70b`. The lemonade router
catalog is `Gemma-4-*-GGUF` + `llama3.2-1b-FLM`. There is no confirmed router equivalent for
the task-specialist models in `inference/registry.py:430-446`.

**Mitigation:** Phase 0c is a mandatory decision gate before Phase 4. If no equivalent exists,
per-caller Ollama shims can be retained selectively. The non-destructive-wiring rule prevents
silent capability loss.

### Risk 3: CLaSp dual-port speculative decoding (MEDIUM)
**What:** `clasp_tier.py` runs E2B draft on `:13308` + E4B verify on `:13307`. This cannot
be expressed as a single router request.

**Mitigation:** CLaSp is added to the CI guard allow-list with an inline `# allow-direct-port: CLaSp speculative decoding — dual-port by design` marker. The Phase 2 CLaSp exception ruling is a formal decision gate (retain vs retire). Default: retain.

### Risk 4: Import cycle hazard (MEDIUM)
**What:** `inference/__init__.py` documents that `swarm/` imports create circular dependencies.
If `LemonadeRouterClient` is placed inside `inference/` and imports anything from `inference/`
that `swarm/` also imports, the cycle re-appears.

**Mitigation:** `LemonadeRouterClient` is a LEAF module (`httpx` + stdlib only). Enforced by
the Phase 0a cycle test: import the module in a minimal venv without swarm/.

### Risk 5: Concurrent edit on direct_tier.py + triune_orchestrator.py (HIGH)
**What:** The CPU-lane agent and this consolidation plan both modify the same two files. If the
CPU-lane work is not merged before this worktree is created, Phase 2 will have a conflict.

**Mitigation:** Hard pre-condition at top of plan: worktree creation is blocked until CPU-lane
PR merges. Enforced by grep check before Phase 0 begins.

### Risk 6: agents/base.py blast radius (MEDIUM)
**What:** `agents/base.py` holds a live circuit breaker (`get_circuit("ollama").record_failure()`)
and uses `_call_ollama()` / `self.config.ollama_base_url`. These are exercised in every agent
call. Migrating this incorrectly will break the entire swarm agent layer.

**Mitigation:** The `_call_ollama` method routes through `SwarmConfig.ollama_base_url`, which
is updated to default to the router in Phase 1 (`swarm_types.py`). The circuit breaker key
`"ollama"` can remain as-is (it tracks the local inference circuit, not the protocol). The
circuit is renamed to `"lemonade"` only if it has externally visible effects; otherwise rename
is cosmetic and deferred.

### Risk 7: healing/ + substrate/ use Ollama /api/ps (no router equivalent) (LOW-MEDIUM)
**What:** `platform/resource_manager.py` and `substrate/overload_coordinator.py` use
`/api/ps` to query which Ollama models are loaded. The lemonade router's equivalent is
`GET /v1/models`. The response shapes are different (Ollama returns loaded model details
with expiry; lemonade returns available models).

**Mitigation:** These callers use the data only for health/offload decisions. The Phase 4a
migration replaces the health probe with `GET :13305/v1/models` and adjusts response parsing.
The offload path in `overload_coordinator.py` (lines 408/441) calls `/api/generate` — this
must use the canonical client, not the Ollama payload shape.

### Risk 8: Backend string unconfirmed for NPU/iGPU (MEDIUM)
**What:** Only `llamacpp_backend=cpu` and `llamacpp_backend=rocm` are confirmed in source.
The NPU backend identifier (`npu`, `xdna2`, `flm`, something else) for the lemonade load API
is not confirmed. If the NPU/iGPU migration uses the wrong string, models silently fail to load.

**Mitigation:** Phase 0c discovery item: confirm backend strings against a live router before
Phase 2 NPU/iGPU work begins. NPU/iGPU migration gates on this confirmation.

---

## Approximate Timeline

| Phase | Estimate | Owner(s) |
|---|---|---|
| 0a (canonical client) | 1 day | compound-engineering |
| 0b (CI guard skeleton) | 0.5 day | autoharness |
| 0c (catalog discovery) | 0.5 day | compound-engineering |
| 1 (swarm/) | 2-3 days | swarm-orchestration |
| 2 (inference/ Class B) | 1-2 days | compound-engineering |
| 3 (gateway/skills/) | 1-2 days | mcp-specialist + surreal-dba |
| 4a+4b (retire + stop C) | 1-2 days | swarm-orchestration + compound-engineering |
| 5 (verify + activate) | 0.5-1 day | autoharness + vault-keeper |
| **Total** | **~7-11 days** | |

---

## Out of Scope

- Lemonade router configuration changes (max_loaded_models tuning) — tracked separately.
- Removing Ollama from the system entirely (Ollama may still serve non-inference use cases).
- ARC-Prize or Kaggle worktrees — do not modify `.worktrees/` content.
- Any `tests/` or `docs/` file that happens to reference `:11434` as example text only.
