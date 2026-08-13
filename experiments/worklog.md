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

### Run 2: T2 → Qwen3-Coder-30B-A3B-Instruct-GGUF (in flight)
- Single change: policy tiers[2].model; probe-verified loadable before adopting.

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
