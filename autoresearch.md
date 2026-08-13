# Autoresearch: Overnight Local Inference — Quality-Gated Cascade Optimization

## Objective
Maximize the quality-gated performance of the Cohezion triune cascade (OmniRouter :13305,
Strix Halo: XDNA2 NPU / RDNA3.5 iGPU / AVX-512 CPU, 128GB unified) on a fixed 24-task
suite (categorical, factual, extraction, reasoning, code, JSON — 4 each) with
deterministic validators. Experiments mutate `experiments/overnight/policy.json`
(tier models, token budgets, entry mapping, gates, concurrency) and the harness itself —
NOT `src/`. Findings transfer to the production routing table afterward.

## Metrics
- **Primary**: pass_rate (fraction of 24 tasks passing their validator, higher is better)
  — IF baseline is at ceiling (>0.85), re-init segment with primary=duration_s (lower is
  better) under the constraint pass_rate must not drop below baseline (drop ⇒ discard).
- **Secondary**: duration_s (wall-clock for full suite), escalations, timeouts, tier_calls.

## How to Run
`./autoresearch.sh` — outputs `METRIC name=value` lines. Per-task PASS/FAIL lines with
tier paths precede the metrics for diagnosis.

## Files in Scope
- `experiments/overnight/policy.json` — the mutable experiment policy (primary lever)
- `experiments/overnight/harness.py` — cascade loop, gating, concurrency
- `experiments/overnight/tasks.py` — task suite (validators FROZEN; adding tasks allowed
  only as a new segment since it changes the metric denominator)
- `autoresearch.sh` — runner

## Off Limits
- `src/cohezion/**` — production code shared with live daemons; read-only reference
- `scripts/ops/consult_ollama_cloud.py`, `src/cohezion/inference/dynamic_hotswapper.py` —
  uncommitted prior-session work riding on this branch; NEVER stage them
- The 4 untracked `scripts/ops/*.py` from the prior session — never stage
- `stash@{0}` — do not pop

## Constraints
- $0 — all inference via :13305; no cloud calls
- Commit with EXPLICIT paths only (`git add autoresearch.* experiments/`) — never `git add -A`
- :13305 is NOT bit-reproducible even at fixed sampling (memory: A/B needs n≥5) —
  KEEP requires passed to improve by ≥2 tasks; in a duration segment, ≥5% faster at
  equal-or-better passed. Smaller deltas = discard as noise.
- Concurrency ≤3 (iGPU aux-call contention; `-np` divides ctx_size)
- Models must exist in the live catalog (`curl :13305/v1/models`) — roster drifts;
  Bonsai-8B-gguf has known "No model loaded" 500 races; Gemma-4-31B blocks Vulkan >236s/call
- Thinking-model output handled by `build_gaia_llm_tier` (reasoning_format=none) — never
  hand-roll HTTP chat calls

## What's Been Tried
(updated as experiments accumulate)
- Run 1: baseline policy — Qwen3-0.6B (T0) / Gemma-4-E4B (T1) / Qwen3.6-35B-A3B (T2),
  classifier entry npu→T0 gpu→T1, validator-gated escalation.
