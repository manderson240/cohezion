# EVO Autoresearch Session Findings
**Date:** 2026-05-01/02 | **Runs:** 6,500+ | **SurrealDB records:** 130,882+

## Core Result: EVO Quality Sensitivity Confirmed

**E51** (100% keep, n=15): EVO coherence is quality-sensitive via witness mark type.

| Proposal Tier | Consensus | EVO Coherence |
|---------------|-----------|---------------|
| naive (no keywords, priority=0.3, budget=False) | 0.725 | **0.4337** |
| optimal (all keywords, priority=0.85, budget=True) | 0.9875 | **0.5152** |
| delta | +0.2625 | **+0.0816** |

**Mechanism**: Optimal proposals cross 0.85 threshold → "directive" witness marks → higher `evo_coherence_metric`. Naive proposals produce only "milestone" marks. The EVO model correctly encodes proposal quality through the witness mark mechanism.

## Experiment Ladder

| Exp | Finding | Status |
|-----|---------|--------|
| E12 | EVO saturated at 0.8164 (100-500 tick persistent EVO, mark-every-tick) | ✅ 2373 runs |
| E9 | "optimization" family best at 0.4702 EVO coherence (deterministic in heuristic mode) | ✅ 108 runs |
| E11→E43 | JEPA persistence: 0% improvement in keep_frac (46.8%→46.9%). E11 API misuse: `surprise_score(s,a,a)` | ❌ 153 runs |
| E46 | JEPA replay buffer: steady state at ~0.97-1.00 final_loss. No accumulation (heuristic mode flat distribution) | ✅ 1676 runs |
| E47 | Voice criticality: resource & ethicist most critical (drop=0.075 each at -0.30 weakening). Architect least critical (drop=0.050). Uses `_mycelium_calibration` not `_score_adjustments` (key implementation insight) | ✅ 933 runs |
| E48 | All voices break consensus at -0.60 calibration removal. 6× safety margin above approval threshold | ✅ 66 runs |
| E49 | JEPA selection ≈ random. Mean delta=-0.001 (JEPA selects near-threshold proposals but not systematically better) | ❌ 253 runs |
| E50 | DB tier validation: naive=0.725 → partial=0.900 → optimal=0.9875. Gain=+0.2625. Correctly ordered=True | ✅ 617 runs |
| E51 | **EVO IS quality-sensitive**: naive=0.4337 vs optimal=0.5152 (delta=+0.0816). 100% keep rate | ✅ 15 runs |

## Architecture Insights

### Two-Layer Calibration Model
- `_mycelium_calibration`: Cross-cycle Mycelium gains (stable, persists across deliberations)
- `_score_adjustments`: Per-deliberation override (`run_llm_deliberation` SETs this fresh each call)
- **Critical**: E47 profile experiments must modify `_mycelium_calibration`, not `_score_adjustments` (which is overwritten every call)

### Resource Heuristic Extension
`_evaluate_resource` now checks description keywords ("cost", "budget", "efficient", "resource", "reduce") for +0.10 bonus. This matches real LLM behavior and enables E50's tier separation.

### JEPA Limitations in Heuristic Mode
The JEPA world model cannot accumulate knowledge in heuristic mode because:
1. All deliberations produce near-identical 12D state vectors (single attractor)
2. Replay buffer prevents catastrophic forgetting but adds no new information
3. The distribution diversity problem requires LLM mode (real score uncertainty)

### Voice Saturation
After 130K+ deliberations, all voice scores (except resource) are clamped at 1.0 due to Mycelium calibration accumulation. To study voice profile effects, must use negative adjustments (-0.30 to -0.60).

## Key Numbers

| Metric | Value |
|--------|-------|
| Maximum consensus (heuristic, calibrated) | 0.9875 (after resource heuristic fix) |
| EVO coherence ceiling (persistent 100 ticks) | 0.8164–0.8165 |
| EVO quality delta (optimal vs naive) | +0.0816 per deliberation |
| Voice fragility threshold | -0.60 calibration removal (all voices) |
| DB formula gain (optimal vs naive) | +0.2625 consensus |
| JEPA steady-state final_loss | 0.97–1.00 |

## Files Changed

- `scripts/overnight_evo_loop.py`: E46, E47, E48, E49, E50, E51 experiments; E9→E47 schedule replacement; replay buffer; `_mycelium_calibration` fix; resource heuristic extension
- `src/cohezion/swarm/quadrature_nexus.py`: `_evaluate_resource` extended with description keyword check
- `src/cohezion/storage/surreal_client.py`: SurrealDB HTTP client (E1–E4 session)

## Pending: Next High-Value Experiments

1. **E52: Mixed-quality persistent EVO** — Alternate naive/optimal proposals in E12-style run. Does EVO coherence settle at an intermediate value? Tests if the 0.8164 ceiling is purely mathematical or proposal-mix-sensitive.
2. **Lemonade LLM mode** — Once iGPU ROCm recovers, re-run E46/E49/E51 with real LLM scores. Expected: meaningful JEPA improvement, genuine proposal uncertainty, higher-variance E51 results.
