---
title: "Inference Budget Monitoring — local-first ladder + usage corpus"
date: 2026-06-09
status: active
owner: inference
---

# Inference Budget Monitoring

Token-efficient ("tip of the spear") inference is **local-first**: every dispatch tries free
AMD silicon before any paid cloud model. This doc describes (1) the routing ladder, (2) the
durable usage corpus that makes spend monitorable against a limited budget, and (3) what the
monitor does and does **not** capture.

## 1. The routing ladder (cheapest-first, local-first)

| Rung | Lane | Model (example) | Cost | Reached when |
|------|------|-----------------|------|--------------|
| 0 | **NPU** (XDNA2/FLM) | `llama3.2-1b-FLM` | electricity only (~2 W) | classification, routing, short answers |
| 1 | **iGPU** (RDNA3.5/Vulkan GGUF) | `Gemma-4-E4B-it-GGUF` | electricity only (~35 W) | generation, structured output |
| 2 | **CPU** (AVX-512 GGUF) | `Gemma-4-31B-it-GGUF` | electricity only (~55 W) | multi-step reasoning |
| 3 | Cloud · **Haiku** | `claude-haiku-4-5` | API $ | local gate fails (cheap cloud) |
| 4 | Cloud · **Sonnet** | `claude-sonnet-4-6` | API $$ | Haiku gate fails (synthesis) |
| 5 | Cloud · **Opus** *(opt-in)* | `claude-opus-4-8` | API $$$ | `include_premium=True` only — see below |
| 6 | Cloud · **Fable** *(opt-in)* | `claude-fable-5` | $10/$50 per 1M | premium, after Opus — the "sparingly" rung |

The orchestrator (`TieredOrchestrator`) runs rung 0 first and escalates only when a quality
gate fails. Local silicon "always dominates on amplitude" (Feynman routing) — cloud is invoked
only on gate failure.

### Premium (Opus → Fable) is opt-in, not default-on
`build_triune_orchestrator(include_premium=False)` is the default: the cloud ladder is
**Haiku → Sonnet**. The premium rungs **Opus → Fable** are appended only with
`include_premium=True`. Rationale: auto-escalating to top-tier models is a cost-increasing,
default-on change that should be **measured before it ships** (use the monitor below to confirm
budget headroom first). The ladder lives in one place: `_CLOUD_LADDER_BASE` /
`_CLOUD_LADDER_PREMIUM` in `src/cohezion/inference/triune_orchestrator.py`.

### Fable 5 — resolved, registered, headless-verified (2026-06-09)
`claude-fable-5` (GA 2026-06-09, Anthropic's most capable GA model, above the Opus class,
$10/$50 per 1M) is the operator's top "sparingly" rung. Two distinct issues were fixed:

1. **"Unknown claude_model" in our fleet (the erroring):** Fable was missing from
   `FleetRegistry` → `fleet.route`/`extend_claude` rejected it. **Fixed** — registered as a
   `cli:claude` model in `src/cohezion/inference/registry.py`. Verified: a headless
   `claude -p --model claude-fable-5 "…"` returns cleanly (exit 0).
2. **Not in the interactive `/model` picker** (matches widespread reports): Fable is a
   **Covered Model** with mandatory 30-day data retention — **unavailable under zero data
   retention**, and requires **Claude Code ≥ 2.1.170** (we run exactly 2.1.170). The picker may
   hide it; the **headless** path with an explicit `--model claude-fable-5` works regardless.

> **Budget note:** through **June 22 2026** Fable 5 is included in Pro/Max/Team/Enterprise at no
> extra cost; from **June 23** it requires usage credits. The usage monitor prices it at $10/$50
> so its spend is visible the moment the premium rung is enabled.

`Mythos 5` (same model, safeguards lifted) is **not** generally available (Project Glasswing
only) — intentionally **not** wired.

## 2. Are we using port 13305 for all local inference?

**Mostly — :13305 is the unified Lemonade router and the default path, but not yet exclusively.**

- **NPU** and **iGPU** tiers route through **:13305** (`build_router_npu_tier`,
  `build_router_igpu_tier`).
- **CPU** tier defaults to **direct :13309** (harness invariant N2), with **:13305** as the
  router fallback when :13309 is unreachable.
- **CLaSp** speculative decoding uses **:13307 + :13308** directly (dual-port by design — no
  router equivalent), and only when both ports are live (usually the draft port is down → falls
  back to router :13305).

The full consolidation onto :13305 is **backlog item 147** (in progress): the CI guard
`scripts/ci/check_inference_port_bypass.sh` tracks remaining direct-port references (report
mode; ~73 at last count). Phases 4–5 are paused pending a descope decision. So: **:13305 is the
target and the default for NPU/iGPU today; CPU and CLaSp retain documented direct-port
exceptions.**

## 3. The usage corpus + monitor

Local silicon was previously logged as "free" and only in-memory (`TokenUsageRecord`), so spend
evaporated on process exit. The durable sink fixes both:

- **Write:** `cohezion.inference.usage_log.record_usage` / `record_dispatch` append one JSON
  line per dispatch to `~/.cohezion-research/logs/usage_log.jsonl` (fail-soft, pytest-skipped).
- **Chokepoints (where logging happens):**
  - `TieredOrchestrator.run` → covers the whole orchestrator family **and** `run_batch`
    (which calls `self.run` per item), one record per logical dispatch with the dispatch's
    **total** cost.
  - `fleet.extend_claude` → the separate direct paid-escalation path.
- **Read / monitor:** `scripts/usage_monitor.py`

```bash
uv run python scripts/usage_monitor.py                  # all-time
uv run python scripts/usage_monitor.py --budget 20      # against a $20 cloud cap
uv run python scripts/usage_monitor.py --since 2026-06-09 --json
```

The headline KPI is **`local share`** — the token-weighted fraction served by free silicon.
Higher = cheaper.

### Local costs include electricity
Local dispatches are **not** zero-cost: they draw watts. Each record carries `energy_usd`
(NPU ~2 W, iGPU ~35 W, CPU ~55 W × latency × `$/kWh`). The report shows a **TOTAL cost = cloud
API $ + local electricity $**. Override the rate with `COHEZION_ELECTRICITY_USD_PER_KWH`
(default 0.17). Cloud dispatches draw ~0 **local** watts (you don't pay Anthropic's power), so
their `energy_usd` is 0; their cost is API dollars. The `--budget` gate is against **cloud API
$** (the limited budget); electricity is reported as a true-cost line, not a budget cap.

> Cost precision: cloud $ is an **estimate** (pricing table × ~4-char/token estimate, since the
> direct tiers don't surface billed usage); electricity is an estimate (nominal lane watts ×
> measured latency). Both track the right direction and magnitude — treat as budget signals,
> not invoices.

## 4. Scope — what the monitor does NOT capture (be honest about coverage)

The corpus captures **in-process** dispatches through the orchestrator and `extend_claude`. It
does **not** see other harnesses' spend, because those run outside this repo's process:

| Lane | In-repo monitor? | Where its budget lives |
|------|------------------|------------------------|
| Local via lemonade/GAIA (Claude Code, this process) | ✅ yes | `usage_log.jsonl` |
| Claude **headless** ladder (Sonnet→Haiku→Opus→Fable) driving the `claude` CLI | ❌ no | Claude Code's own session billing |
| **Ollama** via hermes / opencode / pi CLIs | ❌ no | those CLIs' own logs |

For a single fleet-wide budget across all three lanes, those external harnesses would each need
to append to a shared corpus (e.g. the same JSONL schema). That is a **cross-harness** effort,
intentionally out of scope for this repo — documented here so the monitor's local number is not
mistaken for total coverage. `extend_claude`'s free local *attempts* (before escalation) are
also not separately metered (they cost $0; only the paid escalation is recorded).
