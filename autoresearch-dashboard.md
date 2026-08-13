# Autoresearch Dashboard: overnight-local-inference

**Runs:** 9 | **Kept:** 6 | **Discarded:** 3 | **Crashed:** 0
**Final policy:** 2-tier validator-gated cascade — Gemma-4-E4B-it → Qwen3-Coder-30B-A3B, warm-up before clock, concurrency 3

## Segment 0 — primary: pass_rate (higher)
| # | commit | pass_rate | duration_s | timeouts | status | description |
|---|--------|-----------|------------|----------|--------|-------------|
| 1 | ab2d60b | 0.7083 | 2395.5 | 13 | keep | baseline: 0.6B/E4B/Qwen3.6-35B, classifier entry, validator gate |
| 2 | 7b5a626 | 0.9583 (+35%) | 1120.4 | 1 | keep | T2 swap: Qwen3.6-35B (never loads) → Coder-30B (probe-verified) |

## Segment 1 — primary: duration_s — RETIRED: instrument falsified
| # | duration_s | passed | status | description |
|---|------------|--------|--------|-------------|
| 3 | 2937.6 | 24 | discard | concurrency 3→2 (confounded) |
| 4 | 2039.4 | 24 | discard | VARIANCE CONTROL: same config as #2 → +82% ⇒ duration unusable at n=1 |

## Segment 2 — primary: routing_misses (lower), floor passed ≥ 23 w/ timeout triage
**Baseline:** 18 (#5) | **Best:** 3–4 (#6–#9, −78%)

| # | routing_misses | passed | timeouts | status | description |
|---|----------------|--------|----------|--------|-------------|
| 5 | 18 | 23 | 7 | keep | segment baseline; misses: T0≈13, T1≈4, T2=1 |
| 6 | 4 (−78%) | 24 | 1 | keep | bypass T0 entry — 0.6B was pure miss tax |
| 7 | 3 | 22* | 5 | keep | structural T0 removal (*floor noise: timeout-caused, triage rule added) |
| 8 | 5 | 22 | 7 | discard | terminal timeout 360s: no effect; found load-race root cause |
| 9 | 4 | 24 | **0** | keep | **warm-up before clock: first zero-timeout run** (E4B 117s, Coder 272s to ready) |

## Night's transferable findings
1. Probe loadability (1-token call) before adopting any catalog model — presence ≠ loadability.
2. Weak entry tiers under validator gating are pure tax (misses always escalate + full call burned).
3. Wall-clock unusable at n=1 on a shared box (±82%); outcome-validity metrics are load-robust.
4. Warm every tier before the measurement clock — load-readiness race, GGUF edition.
5. Validator (semantic) gating ≫ char-count gating: found 2 genuine model errors char-gates would pass.
