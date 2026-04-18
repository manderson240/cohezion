# V-Model Phase 2 — Benchmark Harness (Decomposition)

**Workstream:** sorted-churning-toucan — Phase 2 (D.6)
**Date:** 2026-04-18
**Pairs with:** `scripts/validation/vmodel/phase2_benchmark_harness.py` (AutoHarness), `scripts/benchmark_fleet.py` (implementation), `benchmarks/fleet_report.md` (deliverable)

## 1. Requirement

Produce a reproducible cross-backend comparison of the Cohezion inference fleet vs Claude API. This is the source of the single most-quoted number in the Universes cover letter: **"$X Claude budget + local fleet ≈ $Y Claude-only equivalent throughput, with TTFT Nx faster"**.

## 2. Descending Path (Decomposition)

### 2.1 System design
Four-config A/B/C/D matrix over a fixed prompt corpus:

| Config | Backends | Budget | Latency claim |
|--------|----------|--------|---------------|
| **A — Claude-only** | `claude-haiku-4-5` via headless CLI | unrestricted | baseline |
| **B — Local-only** | NPU / iGPU / CPU Lemonade lanes + Ollama (no cloud) | $0 cap | TTFT floor |
| **C — Hybrid budget-capped** | `route()` with `budget_usd=0.001` per call; Claude only if local exhausted | $0.001/call | balanced |
| **D — Hybrid quality-capped** | `extend_claude()` with `quality_threshold=0.85` | unrestricted but lazy | quality floor |

### 2.2 Architecture
```
prompt_corpus (N=20 short prompts — routing-style, 16-token max output)
       │
       ▼
benchmark_fleet.py  ──► health_precheck() ──► per-config runner ──► metrics collector
                                                    │
                                                    ▼
                                      {wall_time, ttft_p50, cost_usd,
                                       failure_rate, lane_dispatch_map}
                                                    │
                                                    ▼
                                          markdown formatter
                                                    │
                                                    ▼
                                    benchmarks/fleet_report.md
```

### 2.3 Module design
- `_load_corpus()` — fixed 20-prompt list, seed-stable for reproducibility
- `_run_config_A_claude_only()` — 20× `claude -p` invocations, collect TTFT via `claude --output-format json`
- `_run_config_B_local_only()` — 20× `route(stream=True, budget_usd=0)` — forces local lanes
- `_run_config_C_hybrid_budget()` — 20× `route(stream=True, budget_usd=0.001)`
- `_run_config_D_hybrid_quality()` — 20× `extend_claude(quality_threshold=0.85)`
- `_tabulate(results)` — compute p50/p95/min/max per metric per config
- `_write_markdown(table)` — render `benchmarks/fleet_report.md` with timestamp + git SHA

### 2.4 Invariants (the Immutable Laws this benchmark must obey)

| # | Invariant | Rationale |
|---|-----------|-----------|
| I1 | The corpus is **deterministic** — same 20 prompts every run, stable order | Reproducibility across sessions |
| I2 | At least 2 of 4 configs must complete (A + at least one of B/C/D) | Partial runs still produce a headline number |
| I3 | Every row in the output table must show all 4 metrics (wall_time, ttft_p50, cost, failure_rate) | No silent column drops |
| I4 | TTFT values must come from **streaming** dispatch (`stream=True`) — never estimated from total latency | Honest measurement |
| I5 | Claude-only config TTFT must be **measured**, not assumed from registry | Avoids planted-number bias |
| I6 | Report must include git SHA + timestamp + fleet health snapshot at run time | Provenance |
| I7 | Fleet health snapshot must show ≥1 local lane up before B/C/D configs run | Don't fake local results with fallback to Claude |

### 2.5 Acceptance criterion

`make benchmark-fleet` exits 0 with `benchmarks/fleet_report.md` present, the 4-row headline table filled in, and `scripts/validation/vmodel/phase2_benchmark_harness.py` passes all 7 invariants against the report.

## 3. Apex (Implementation)

- `scripts/benchmark_fleet.py` (target ≤ 300 LOC)
- New Makefile targets: `benchmark-fleet`, `vmodel-phase2`

## 4. Ascending Path (Verification)

- **Unit verification** → `phase2_benchmark_harness.py` checks I1-I7 against the generated report file
- **System validation** → manual review of `benchmarks/fleet_report.md` looking for unrealistic numbers (e.g., Claude-only at $0, or local lane TTFT > Claude API range = backend broken)
- **Acceptance** → `scripts/validation/vmodel_acceptance.py` records `{name: 'benchmark', status: 'verified'}` to SurrealDB if harness passes

## 5. Out of scope

- Training-loop throughput measurement (requires a live agent, deferred)
- Multi-day trend tracking (single-point benchmark here, repeatable)
- Quality-score rubric beyond length + non-empty gate (upgrade with JEPA scoring later)
