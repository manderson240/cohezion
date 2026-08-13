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

## Key Insights
(populated as the loop runs)

## Next Ideas
- validator_gate on/off A-B (does semantic gating beat char-count gating?)
- entry policy: all-T0 entry (maximize cheap-first) vs classifier entry vs all-T1
- token budgets: 512 vs 1024 vs 2048 on T0 (truncation vs latency)
- swap T0: Qwen3-0.6B vs gemma3-1b-FLM vs qwen3-4b-FLM (NPU lanes; FLM load race — probe first)
- swap T2: Qwen3.6-35B-A3B vs Gemma-4-26B-A4B vs Qwen3-Coder-30B (code-heavy suite half)
- concurrency 1 vs 3 vs 6 (contention curve on unified memory)
- category-conditional entry (code→T1+, categorical→T0)
