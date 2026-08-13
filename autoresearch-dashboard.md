# Autoresearch Dashboard: overnight-local-inference

**Runs:** 5 | **Kept:** 3 | **Discarded:** 2 | **Crashed:** 0

## Segment 0 — primary: pass_rate (higher)
**Baseline:** 0.7083 (#1) | **Best:** 0.9583 (#2, +35.3%)

| # | commit | pass_rate | duration_s | timeouts | status | description |
|---|--------|-----------|------------|----------|--------|-------------|
| 1 | ab2d60b | 0.7083 | 2395.5 | 13 | keep | baseline: Qwen3-0.6B/Gemma-4-E4B/Qwen3.6-35B, classifier entry, validator gate |
| 2 | 7b5a626 | 0.9583 (+35.3%) | 1120.4 | 1 | keep | T2 swap: Qwen3.6-35B (never loads) → Qwen3-Coder-30B (probe-verified) |

## Segment 1 — primary: duration_s (lower) — RETIRED: instrument falsified
| # | commit | duration_s | passed | status | description |
|---|--------|------------|--------|--------|-------------|
| 3 | 7b5a626 | 2937.6 | 24 | discard | concurrency 3→2 (confounded by ambient load) |
| 4 | 7b5a626 | 2039.4 | 24 | discard | VARIANCE CONTROL: same config as #2 → +82% spread ⇒ duration unusable at n=1 |

## Segment 2 — primary: routing_misses (lower), floor passed ≥ 23
**Baseline:** 18 (#5)

| # | commit | routing_misses | passed | duration_s | status | description |
|---|--------|----------------|--------|------------|--------|-------------|
| 5 | 68a8386* | 18 | 23 | 1741.3 | keep | segment baseline; misses: T0≈13, T1≈4, T2=1 |

Run 6 in flight: entry npu→1 (bypass T0). Prediction: misses → ~5.
(*commit hash approximate — see autoresearch.jsonl for exact)
