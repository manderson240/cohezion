# Primitive Forge Phase 4 Tick Cap Fix

## Date: 2026-06-02
## Issue: Phase-4 tick cap not enforced (pitfall #0 in cohezion-autoresearch)

## Problem
Phase 4 had `MAX_TICKS_PER_PHASE = {4: 2000}` defined but no handler checked it.
The daemon ran indefinitely past 2000 ticks with exclusively failed outcomes,
stalling all 1500+ pending hypotheses indefinitely.

### Confirmed State Before Fix
- Phase 4, ticks_used=2100 (exceeded cap)
- total_ticks: 36,863 across epoch progression
- Queue: 2028 no_program + 72 partial + 1500 pending = 3600 hypotheses
- new_solves: 0 (zero across all epochs up to that point)

## Fix Applied
Added bounds check in phase4_synthesize() at line ~274:
```python
max_ticks = MAX_TICKS_PER_PHASE.get(state.get("phase", 4), 99999)
if state["phase_ticks_used"] >= max_ticks:
    # force-complete remaining as no_program, transition to Phase 5
```

## Post-Fix State (2026-06-02 17:58 UTC)
- Epoch 12 completed cleanly via Phases 5→6
- Report written: 400 tasks signed, 3600 hypotheses tested, 0 solves
- State auto-resets to Phase 3 on next tick (warm-start via Phase 6 handler)

## Next Steps Required
Per pitfall #72/#73, zero-solve rate is confirmed genuine solver deficiency:
1. Expand ALL_TRANSFORMS to >=60 ops (currently ~46-176 depending on build)
2. Improve hypothesis quality (larger synthesis model or better prompt)
3. Add warm-start task scaffolding from known-solvable tasks
