# Worklog: Overnight Local Inference Autoresearch (2026-08-13)

Session: s-77b9f9d6a892, branch `autoresearch/local-inference-20260813`
(cut from `feat/compound-session-20260812`, which is based on the STALE
`feat/knowledge-corpus-retrieval` tip — pre-dates the EventBus stop() fix on main).

## Setup
- Suite: 24 tasks, 6 categories, deterministic validators (`experiments/overnight/tasks.py`)
- Harness: policy-driven cascade using `build_gaia_llm_tier` + `task_classifier.classify`
  with validator-gated escalation (`experiments/overnight/harness.py`)
- Baseline policy: Qwen3-0.6B-GGUF (T0, 1024tok) → Gemma-4-E4B-it-GGUF (T1, 2048tok)
  → Qwen3.6-35B-A3B-GGUF (T2, 2048tok, TRUST); classifier entry npu→T0/gpu→T1;
  concurrency 3; 240s per-tier timeout
- Noise rule: :13305 non-reproducible ⇒ keep needs ≥2-task improvement (or ≥5% duration
  at equal-or-better passed in a duration segment)

## Runs

### Run 1: baseline — pass_rate=0.7083 (17/24) (KEEP)
- Timestamp: 2026-08-13 01:29
- What changed: nothing (baseline policy)
- Result: passed=17, duration=2395.5s (~40min), escalations=23, timeouts=13, tier_calls T0=18/T1=22/T2=7
- Insight: **T2 (Qwen3.6-35B-A3B-GGUF) NEVER loaded** — every call 500 "llama-server failed
  to start". All 7 T2 attempts burned 240s timeouts or errors; ~5-6 task failures
  (math-chain, math-pct, code-dedup, json-color, json-count, ext-email) are APPARATUS
  failures, not model-quality failures (config-before-capability). Also T0 (0.6B!) ran
  155-240s/call — model-thrash from 3 concurrent tasks forcing competing loads on the router.
  Category profile: categorical 4/4, factual 4/4, extraction 3/4, code 3/4, reasoning 2/4, json 1/4.
- Next: swap T2 to a model that verifiably loads (probed: Qwen3-Coder-30B-A3B OK "OK",
  Gemma-4-26B-A4B loads but thinking-mode, Qwen3-8B load-timeout at 180s)

### Run 2: T2 → Qwen3-Coder-30B-A3B — pass_rate=0.9583 (23/24) (KEEP)
- Timestamp: 2026-08-13 02:10
- What changed: tiers[2].model Qwen3.6-35B-A3B (never loads) → Qwen3-Coder-30B-A3B (probe-verified)
- Result: passed 17→23 (+6), duration 2395→1120s, timeouts 13→1, escalations 23→14
- Insight: ALL apparatus failures flipped. Only json-count fails (vowel counting — letter-level
  task, all 3 tiers miss it; keeps instrument off ceiling). Code category now 4/4 at T1 in
  9-42s/call. T0 still erratic (8-236s for a 0.6B) — contention, not capability.
- Next: pass_rate 0.958 > 0.85 ceiling → SEGMENT 1: primary=duration_s (lower), HARD FLOOR
  passed>=23 (any drop ⇒ discard). Anchor: Run 2's 1120.4s @ concurrency=3.

### Run 3: concurrency 3→2 — duration_s=2937.6 (DISCARD, segment 1)
- Timestamp: 2026-08-13 02:47
- What changed: concurrency 3→2
- Result: duration 2938s vs 1120s anchor (+162%) — DISCARD. But passed=24/24 (first
  perfect run; even json-count passed via T2 122.9s). timeouts 1→8.
- Insight: T0 hit 240s timeouts on the first three tasks — at RUN START, which points to
  external fleet load (overnight daemons share :13305), not the concurrency setting.
  n=1 per config cannot separate policy effect from ambient load. ALSO: 24/24 proves the
  suite is fully solvable — the pass floor (>=23) is realistic.
- Next: Run 4 = VARIANCE CONTROL — identical config to Run 2 (conc 3). Measures the
  anchor's own run-to-run spread; all future duration deltas judged against that spread.
  Ambient at launch: load avg 3.82/5.45/5.66.

### Run 4: variance control, config == Run 2 — duration_s=2039.4 (DISCARD/control, segment 1)
- Timestamp: 2026-08-13 03:30
- What changed: NOTHING (identical config to Run 2)
- Result: 24/24 passed again; duration 2039s vs Run 2's 1120s (+82% on the SAME config);
  escalations 21, timeouts 7
- Insight: **duration_s at n=1 is an unusable primary here** — ambient daemon load and
  model residency dominate. BUT escalations−timeouts is tight across runs 2/3/4
  (~13/15/14): validator outcomes are load-robust. Queue time can cause a timeout;
  it cannot make a returned answer wrong.
- Next: SEGMENT 2 — primary=routing_misses (validation-failed responses, timeouts
  excluded), lower is better, floor passed>=23. Harness now emits METRIC routing_misses.

### Run 5: segment 2 baseline — routing_misses=18 (KEEP as baseline)
- Timestamp: 2026-08-13 04:30
- What changed: nothing (instrument added)
- Result: routing_misses=18, passed=23 (floor exactly), duration 1741s, timeouts 7
- Insight: miss decomposition — T0 ≈ 13 (fluent-but-wrong on factual/reasoning/json),
  T1 ≈ 4 (json/code), T2 = 1 (cat-vowel WRONG ANSWER from Qwen3-Coder on letter
  membership — first genuine terminal-tier quality failure; floor caught it).
  Estimate-vs-measurement gap (13-15 est vs 18): final-attempt validation failures
  count as misses too — always prefer the instrumented number.
- Next: Run 6 — entry_by_node npu→1 (bypass T0). Prediction: misses 18 → ~5.

### Run 6: bypass T0 (npu→1) — routing_misses=4 (KEEP)
- Timestamp: 2026-08-13 05:40
- What changed: entry_by_node npu 0→1 (T0 never entered)
- Result: misses 18→4 (predicted ~5 ✓), passed=24/24, duration 1078.6s (fastest yet,
  noisy metric), escalations 5, timeouts 1. T1 solved 19/24 solo.
- Insight: T0 (Qwen3-0.6B) is a THINKING model — rambles 2500-4000c on yes/no prompts;
  even its categorical record was spotty (~50-75%). Under validator gating it saved
  nothing and taxed everything. Category-conditional T0 re-entry: NOT worth a run.
  Remaining 4 misses (code-rev/fib T1, json-color/count T1) look STOCHASTIC — same
  tasks passed T1 in other runs. Segment-2 noise rule: keep needs ≥3 miss reduction.
- Next: Run 7 — structurally remove T0 from tiers (simpler-is-better; also frees the
  router from ever loading the 0.6B → residency relief). Prediction: misses ≈4 (equal).

### Run 7: 2-tier cascade, T0 deleted — routing_misses=3, passed=22 (KEEP w/ triage)
- Timestamp: 2026-08-13 06:40
- What changed: tiers[0] (Qwen3-0.6B) deleted; entry npu/gpu→0 (E4B). Behaviorally
  IDENTICAL to run 6 (removed tier was unreachable).
- Result: misses=3 (prediction ~4 ✓), passed=22 — BUT both failures were
  TERMINAL-TIER TIMEOUTS (json-color/count T1 240s), not wrong answers.
- Insight: identical execution graphs measured 24/24 (run 6) and 22/24 (run 7) ⇒
  **the pass floor itself is ±2 noisy under ambient load.** Floor-violation triage rule
  added to autoresearch.md: timeout-caused failures = apparatus noise; only miss-caused
  failures discard. Also: terminal-tier timeouts are the direct task-failure channel.
- Next: Run 8 — per-tier timeouts (harness change committed): terminal tier 360s.
  Prediction: timeout-caused task failures →0-1, misses unchanged ~3-4.

### Run 8: terminal tier timeout 240→360s (in flight, segment 2)

## Key Insights
- Probe EVERY tier model with a 1-token chat call BEFORE a suite run — catalog presence
  ≠ loadability (Qwen3.6-35B-A3B advertised but llama-server won't start; possibly the
  FLM-pin / footprint issue class).
- The 240s per-tier timeout × dead tier = worst-case 12min per affected task; a dead
  terminal tier poisons duration far more than quality.
- classifier entry sent 18/24 tasks to T0 — the 0.6B passes categorical cleanly but
  fails validators on extraction/reasoning → escalation churn. Entry policy is a rich axis.

## Next Ideas
- validator_gate on/off A-B (does semantic gating beat char-count gating?)
- entry policy: all-T0 entry (maximize cheap-first) vs classifier entry vs all-T1
- token budgets: 512 vs 1024 vs 2048 on T0 (truncation vs latency)
- swap T0: Qwen3-0.6B vs gemma3-1b-FLM vs qwen3-4b-FLM (NPU lanes; FLM load race — probe first)
- swap T2: Qwen3.6-35B-A3B vs Gemma-4-26B-A4B vs Qwen3-Coder-30B (code-heavy suite half)
- concurrency 1 vs 3 vs 6 (contention curve on unified memory)
- category-conditional entry (code→T1+, categorical→T0)

### Run 8: terminal timeout 360s — routing_misses=5, passed=22 (DISCARD)
- No effect on misses; found the ROOT CAUSE of run-start timeout clusters: tasks queue
  behind model load/swap at suite start. fact-planet = genuine knowledge miss
  (Coder-30B answers Jupiter; correct is Saturn).

### Run 9: warm-up before suite clock — routing_misses=4, passed=24, timeouts=0 (KEEP, final)
- Timestamp: 2026-08-13 08:30
- What changed: harness warms each tier (untimed probe) before measurement starts.
- Result: FIRST ZERO-TIMEOUT RUN. 24/24, misses stable 4, escalations 4, suite 1093s.
  Warm-up itself proved the diagnosis: E4B 117s, Coder-30B 272s to become ready.
- NIGHT CLOSED. Final policy: 2-tier validator-gated E4B→Coder-30B + warm-up.
  Resume points in autoresearch.ideas.md. Production transfer list in vault memory
  overnight-cascade-experiment-20260813 + skill falsifiable-eval-harness v1.4.0 rule 12.
