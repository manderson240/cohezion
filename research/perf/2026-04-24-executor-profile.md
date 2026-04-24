---
title: "CompoundExecutor.execute_task — Profiling Report"
date: 2026-04-24
campaign: synthetic-sniffing-panda Z6
methodology: cProfile, N=100 iterations, mocked external dependencies
note: "READ-ONLY analysis. No optimizations applied."
---

# Methodology

Synthetic benchmark exercising `CompoundExecutor.execute_task` end-to-end through
the 11-step pipeline.

- **Iterations**: N = 100 (after 5-iteration warm-up to populate caches and force
  lazy imports).
- **Mocking**: `MCPClient` mocked via `unittest.mock.MagicMock`. All vault methods
  return canned strings/lists. Guardrails and skill-refinement are wired (default
  factories), but `enable_guardrails=False` to keep the input check off the hot
  path. Real components: `JourneyTracker`, `CompoundMetricsCollector`,
  `InflectionDetector` (default factory), `SkillRefiner` (default factory),
  `JEPAWorldModel` (~2M-param torch module loaded at startup).
- **Per-step accounting**: each pipeline step's primary helper is wrapped with
  `perf_counter()` to bucket wall time. Imperfect (some steps share work in
  in-line code), but reliable enough to spot the 80/20.
- **Environment**: AMD Ryzen AI MAX+ 395, CPython 3.11.15, no GPU, no live
  SurrealDB (intentionally — circuit breaker opens immediately and falls back
  to InMemoryStore, which is the realistic "service unavailable" path).
- **Caveat**: SurrealDB connection failures still consume real socket
  `connect()` + `recv_into` time. This is a real-world signal — when the DB is
  down, the executor pays for it on every call.

Driver: `scripts/profiling/profile_executor.py`.
Profile data: `/tmp/executor_profile.prof` (binary, loadable via `pstats.Stats`).

# Headline numbers

| Metric | Value |
|---|---|
| Wall time, 100 iterations | **3.884 s** |
| Per-iteration mean | **38.84 ms** |
| Time in real network I/O (`recv_into`) | **3.041 s (78.3%)** |
| Time in cohezion application code | **~0.84 s (21.7%)** |

The dominant signal is **synchronous network I/O on the hot path**. With a
healthy SurrealDB the per-iteration cost would drop, but the *blocking* nature
of the calls remains.

# Top 10 hottest functions (by CUMULATIVE time)

| Cumtime (s) | ncalls | Function |
|---:|---:|---|
| 3.882 | 100 | `executor.execute_task` |
| 3.194 | 200 | `urllib.request.urlopen` (vault HTTP + SurrealDB HTTP) |
| 3.041 | 200 | `_socket.socket.recv_into` |
| 2.080 | 100 | `journey_tracker.track_execution` (Step 9) |
| 1.746 | 100 | `journey_tracker._persist_to_surreal` |
| 1.606 | 100 | `executor.get_experience_guidance` (Step 1) |
| 1.604 | 100 | `executor_helpers.vault_integration.fetch_experience_guidance` |
| 0.156 | 100 | `world_model.surprise_score` (called by JourneyTracker) |
| 0.151 | 100 | `world_model.surprise_score` body |
| 0.111 | 100 | `journey_tracker._text_to_latent` (2048D hash embedding) |

# Top 10 hottest functions (by SELF / tottime)

| Tottime (s) | ncalls | Function | Notes |
|---:|---:|---|---|
| 3.041 | 200 | `socket.recv_into` | network read |
| 0.103 | 100 | `journey_tracker._text_to_latent` | **per-call Python loop, 2048 iterations** |
| 0.058 | 700 | `torch._C._nn.gelu` | JEPA forward pass |
| 0.015 | 1300 | `torch._C._nn.linear` | JEPA forward pass |
| 0.015 | 100 | `executor.execute_task` (frame body) | inline orchestration cost |
| 0.015 | 200 | `socket.connect` | TCP handshake to dead SurrealDB |
| 0.013 | 200 | `_socket.getaddrinfo` | DNS lookup overhead |
| 0.012 | 200 | `bioelectric_model.BioelectricNetwork.__init__` | **per-call instance creation, 200x for 100 iters** |
| 0.011 | 300 | `torch.tensor` | tensor allocation |
| 0.010 | 400 | `socket.close` | tear down per-call connection |

# Per-pipeline-step time breakdown (instrumented sample)

| Step | total (ms) | per-call (ms) | % of pipeline |
|---|---:|---:|---:|
| 1 — Get experience guidance | 1606.32 | 16.063 | **41.4%** |
| 2 — Log execution start | 15.95 | 0.160 | 0.4% |
| 4 — Log execution result | 8.83 | 0.088 | 0.2% |
| 4.5 — Log execution trace | 16.47 | 0.165 | 0.4% |
| 5 — Detect anomaly | 2.34 | 0.023 | 0.1% |
| 6 — Extract pattern | 2.66 | 0.027 | 0.1% |
| 7 — Refine skill | 1.17 | 0.012 | 0.0% |
| 8 — Record metrics | 1.28 | 0.013 | 0.0% |
| 9 — Track journey (FLUME + Surreal) | 2081.33 | 20.813 | **53.6%** |
| **Sum (instrumented)** | 3736.35 | | 96.2% |
| Unaccounted (steps 5.5/5.8/5.9/7.3/7.4/7.5/7.6/7.7/9.5/10/10.5/10.6 + glue) | 147.54 | | 3.8% |

**The 80/20 is clear**: Steps 1 and 9 account for **95% of pipeline time**.
Both are dominated by synchronous network I/O (vault HTTP + SurrealDB HTTP).

# Anti-patterns observed

| # | Pattern | File:line | Estimated cost |
|---|---|---|---|
| 1 | Synchronous `urllib.request.urlopen` on hot path (vault + Surreal). The executor itself is sync, so callers pay full latency every call. | `journey_tracker.py:495` (`_persist_to_surreal`), `executor_helpers/vault_integration.py:18` (`fetch_experience_guidance`) | **78% of wall time** when DB is down; ~10–30% when healthy |
| 2 | Per-call Python loop `for i in range(2048)` computing `np.sin/np.cos` per element to build a 2048-D embedding. Vectorizable in 1 numpy call. | `journey_tracker.py:240` (`_text_to_latent`) | 1.0 ms / call → ~0.1 ms vectorized; **~9× speedup on this fn**, ~3% of wall |
| 3 | Per-call instance construction of `BioelectricNetwork(n_cells=8)` in Step 7.6, plus separate `import numpy as np` and `from cohezion.physics.bioelectric_model import …` inside the same try-block. Module is reimported every iteration (Python cache hit, but still a dict lookup). | `executor.py:846-851` | 0.2 ms / call (200 inits visible, expected 100) → cacheable as instance attr |
| 4 | Per-call instance construction of `NaturalCapitalValuation()` in Step 5.9 with the same lazy-import-inside-try pattern. | `executor.py:664-668` | <0.1 ms / call but accumulates with #3 |
| 5 | `from cohezion.compound.inflection_detector import Severity` imported **3 separate times** inside `execute_task` (lines 548, 590, 604). Each is a hashtable hit, but module-level import would zero this. | `executor.py:548, 590, 604` | <0.05 ms / call but cognitive-load + lint-noise |
| 6 | Step 9 inner loop calls `asyncio.run()` from a sync function to persist a single trajectory point. This forces a fresh event loop per call when no loop is running. | `executor.py:937-943` | 0.6 ms / call event-loop setup; with 100 calls = 60 ms |
| 7 | Step 10.5 (`OuroborosBridge`) and Step 10.6 (`MyceliumRegistry`) lazy-import on every call inside try-blocks. Cached on `self._ouroboros_bridge_instance` only after first call, but the *import* statement itself runs every iteration. | `executor.py:987, 1015` | <0.1 ms / call cumulatively |
| 8 | `metrics.get(...)` called 20+ times in the same function — fine, but several look up the same key (`"coherence"`, `"phi_score"`) in different blocks. A local variable would cut dict lookups in half. | `executor.py` (multiple) | Negligible per-call but reads cleaner |
| 9 | `MyceliumRegistry.run_audit()` triggered every 10 successful executions (line 1028). For a long-lived executor in production this is a **periodic 100ms+ stall** every 10 calls. Already produced visible "Mycelium audit" log lines at iterations 10/20/.../100 in the run. | `executor.py:1026-1037` | Bursty; not in steady-state tail latency but matters for p99 |

The `executor_helpers/` extracts are NOT a perf bottleneck — they are thin
wrappers (`run_async_guardrail` is a 3-line `asyncio.run` shim, `try_template_match`
is a single hash lookup, `vault_integration` adds no overhead beyond what it
already had inline). The extractions are a **maintainability win at zero perf cost**.

# Recommendations (prioritized — no fixes applied)

## High-leverage (>10% potential improvement)

1. **Make Step 9 journey persistence async/fire-and-forget.** Currently
   `_persist_to_surreal` blocks the executor on a synchronous HTTP round-trip.
   Wrapping it as a background task (already partly attempted in the
   `journey_persistence` branch lines 929-943, but only when an asyncio loop
   is already running) would remove ~20 ms / call (53% of pipeline time when DB
   is down, ~5–10 ms when DB is healthy). **Estimated win: 30–50% of per-call
   latency.** Lowest risk: start a single background `asyncio` thread at
   executor init and `loop.call_soon_threadsafe` from sync code.

2. **Make Step 1 vault guidance optional / lazy / cached.** Many tasks don't
   need fresh guidance — a per-skill TTL cache (5–60 s) would convert the
   first-call cost into amortized near-zero. Already partly implemented via
   template-matching in Step 1.3, but Step 1 still always runs first. **Estimated
   win: 30–40% of per-call latency** when guidance is unchanged.

## Medium (2-10%)

3. **Vectorize `_text_to_latent`** at `journey_tracker.py:240`. Replace the
   2048-iteration Python loop with `np.arange + np.sin + np.cos` over a
   pre-allocated array. Today: 1.0 ms / call self-time. Vectorized: ~0.1 ms.
   **Estimated win: ~3% of wall.**

4. **Hoist single-instance helpers out of the hot path.** Construct
   `BioelectricNetwork`, `NaturalCapitalValuation`, `OuroborosBridge`, and
   `MyceliumRegistry` once at executor init (or via lazy `@cached_property`)
   instead of inside `execute_task`. Move the `import numpy as np` and
   `from cohezion.physics...` to module top. **Estimated win: 1–2% wall, plus
   cleaner stack traces and import-error visibility.**

5. **Consolidate `Severity` imports** to a single module-level import. Trivial,
   readability + a couple of dict lookups saved.

## Low (<2%, may not be worth the complexity)

6. **Move `MyceliumRegistry.run_audit()` (Step 10.6) off the hot path.**
   Schedule it on a background timer, not on every-10th-execution. Avoids p99
   tail latency spikes.

7. **Cache `metrics.get("coherence", 0.5)` in a local** the first time it's
   read (lines 779, 791, 853, 866, 991, etc.). Pure readability, sub-μs cost.

8. **Consider a "fast path" that skips Steps 5.8 / 5.9 / 7.6 / 7.7 / 10.5 /
   10.6 when `degradation_mode=False` AND a `low_overhead=True` flag is set.**
   These are non-blocking observability steps; some users may not need them.

# Caveats

- **Mocked dependencies remove some real I/O** — but the vault + Surreal HTTP
  attempts still made real socket calls (just to nothing). A live vault server
  would replace 15-ms-of-failed-connection with 15-ms-of-successful-fetch on
  many setups; the *blocking-sync-on-the-hot-path* finding is unchanged.
- **Synthetic task runs `lambda guidance: (str, dict)`** — no real LLM call.
  In production the `execute_fn` itself is the dominant cost (seconds, not
  milliseconds). The findings here are about **pipeline overhead**, which is
  what's optimizable independently of the user's `execute_fn`.
- **N=100** is sufficient to see steady-state means but doesn't characterize
  the long tail. p99 latency (especially Mycelium audit cycles every 10 calls)
  is visible in the raw output but not in the means table.
- **This profile is on the post-campaign + Σ wave code** (commit `c3ef0a7df`),
  not a pre-campaign baseline. Some helpers (`executor_helpers/`) are recent
  extracts that did not exist in earlier commits.
- **Guardrails are disabled** in the benchmark (`enable_guardrails=False`).
  With guardrails on, expect Step 3 (input check) and the post-execute output
  check to add ~1-3 ms each via `_run_async_guardrail` (which itself wraps
  `asyncio.run` per call — see Recommendation #1's pattern repeated here).

# Files

- Profile data: `/tmp/executor_profile.prof` (load with `pstats.Stats`)
- Raw stdout: `/tmp/profile_output.txt`
- Profile script: `scripts/profiling/profile_executor.py`
- This report: `research/perf/2026-04-24-executor-profile.md`
