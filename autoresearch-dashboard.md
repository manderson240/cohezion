# Autoresearch Dashboard: overnight-local-inference

**Runs:** 2 | **Kept:** 2 | **Discarded:** 0 | **Crashed:** 0

## Segment 0 — primary: pass_rate (higher)
**Baseline:** pass_rate: 0.7083 (#1) | **Best:** 0.9583 (#2, +35.3%)

| # | commit | pass_rate | duration_s | timeouts | status | description |
|---|--------|-----------|------------|----------|--------|-------------|
| 1 | ab2d60b | 0.7083 | 2395.5 | 13 | keep | baseline: Qwen3-0.6B/Gemma-4-E4B/Qwen3.6-35B, classifier entry, validator gate |
| 2 | 7b5a626 | 0.9583 (+35.3%) | 1120.4 (-53.2%) | 1 | keep | T2 swap: Qwen3.6-35B (never loads) → Qwen3-Coder-30B (probe-verified) |

## Segment 1 — primary: duration_s (lower), hard floor passed ≥ 23
Anchor: 1120.4s (#2). Run 3 in flight: concurrency 3→2 (anti-thrash).
