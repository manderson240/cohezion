---
type: autoresearch
run_id: tcrao_postmortem_1952
target: arc_solver
status: regression
metric_value: 0.4462
hypothesis: add_line_detection_h_v_diag
compute_tier: cpu
wall_time_s: 0.0
timestamp: 2026-06-03T19:52:10Z
---

# TCRAO Postmortem Recovery — Cycle Interrupted by Outer Timeout

## Context
This vault entry was manually written to recover from a SIGKILL that occurred
when the outer cron wrapper (300s timeout) killed the process mid-cycle.
The orchestrator's K-Search tree _was_ updated via _save_tree() inside the
loop, but persist_to_vault() and state file append were lost because they
run after run_autoresearch() returns.

## Results Recovered from K-Search Tree (Iteration [1/2] of this cycle)
- Hypothesis: add_line_detection_h_v_diag
- solve_rate: 0.4462 (regression — below current best ~0.4804)
- This is the same score as the prior flood_fill_expansion result from
  the first killed cycle

## Known Issues Identified
1. **300s outer timeout is too tight** for --iterations 2: each iteration takes
   ~180s synthesis (Lemonade/Gemma-4) + ~15s eval = ~195s/synthesis. Two iterations
   need ~390s but second synthesis may take longer as the model generates code variant
2. **Vault entries lost on kill**: Only K-Search tree updates survive because they're
   written inside the loop (_save_tree at line 438), while vault/state are deferred
3. **Pitfall #88 confirmed**: Post-mortem must read K-Search JSON (not state file or
   dangling NDJSON) for reliable result detection

---
