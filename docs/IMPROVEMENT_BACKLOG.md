---
title: "Cohezion Self-Improvement Backlog — single-loop, multi-thread"
created: 2026-06-05
owner: "/loop (self-paced, one item per tick)"
policy:
  - "One item per tick. Pick the lowest-numbered TODO whose deps are met."
  - "Every item: TDD red→green, a FALSIFIABLE check (must be able to come back negative),"
  - "  non-destructive/additive, respect calibrated invariants (.claude/rules/harness.md:"
  - "  A3/A4/A5/CA1/CC2/LM6 + the new K1/rule-5 OOM gates). ruff + targeted tests green."
  - "Commit surgically (explicit paths, churn-guard). Mark the item DONE here with the hash."
  - "Behavior-changing items (B3/B5/B6): land behind the falsifiable check; if it can't come"
  - "  back negative, downgrade to report-only and flag for human review instead."
  - "If a tick would violate a calibrated invariant or needs a human decision, STOP + surface it."
threads:
  A: "Audit (new report-only dimensions)"
  B: "Remediations (flagged findings → committed fixes)"
  C: "Self-improvement (routing feedback → fleet tunes itself — principle #3)"
---

# Self-Improvement Backlog

Status legend: `TODO` · `DOING` · `DONE <hash>` · `BLOCKED <why>` · `RETIRED <why>`

| # | Thread | Item | Falsifiable check | Gating | Status |
|---|---|---|---|---|---|
| 1 | B | **OOM eviction subscriber + background driver** — `monitor.subscribe(evict_on_rising_critical)` unloads the lowest-priority loaded model on a CRITICAL *rising* edge; a small driver calls `monitor.evaluate()` on a cadence so transitions fire without a load attempt. | inject a CRITICAL snapshot → the evictor is called exactly once on the rising edge, NOT on sustained-critical or on WARNING; driver advances state. | additive | DONE 9c-pending |
| 2 | C | **Routing-decision log** — record every `get_best_for_task` decision `(task_class, chosen_model, lane, fell_back?, outcome?)` to `~/.cohezion-research/logs/routing_log.jsonl` (reuse the `resolution_log` pattern; fail-soft, pytest-skipped). | a logged decision round-trips; pytest run writes nothing to the real log. | additive | TODO |
| 3 | B | **Calibrate `LANE_WATTS` / `LAMBDA_ENERGY`** against `hardware_telemetry.tokens_per_watt`. Replace the placeholder watts with measured joules-per-token where available; keep quality-dominant (principle #1). | `test_quality_beats_electricity` still green after recalibration; energy ordering NPU<iGPU<CPU preserved; CC2 harness check green. | needs-experiment | TODO |
| 4 | B | **Register LFM2.5-VL-1.6B-Extract** as the `EXTRACTION`/`VISION` specialist in `FleetRegistry` + prove lemonade `--mmproj` (else `llama-mtmd` sidecar). | `for_task(EXTRACTION)` returns it; a 10-image extraction set ≥ a big-VLM baseline at lower VRAM, temp=0 — OR honest NULL → sidecar. | needs-experiment | TODO |
| 5 | A | **Test-adequacy spot-check** — sample existing `tests/<mod>/` dirs; flag hollow/smoke tests that don't discriminate (report-only, audit doc). | each flagged test, when the source is mutated, would still pass (proving it's non-discriminating). | report-only | TODO |
| 6 | B | **Continuous quality×energy in `CostAwareRouter.select_model`** — use the full `feynman_path_weight(quality, cost, joules)` amplitude (it has per-model quality scores). | argmax-amplitude prefers the NPU at equal quality; a higher-quality heavier lane still wins; CC2 green. | behavior-change | TODO |
| 7 | B | **Harness-aware routing (B1 from research)** — `pre_dispatch_classifier` emits a `harness` field: plain CoT on NPU, ReAct/tool-loop (goose) on mid-tier iGPU, minimal on strong tier (arXiv 2605.30621). | NPU never gets a ReAct scaffold; mid-tier tool tasks get the tool-loop; falsifiable on a labeled task set. | behavior-change | TODO |
| 8 | B | **Fix the 2 latent bugs** — §12.1 R-Zero unreachable `>0.8` branch; §12.2 always-pass `SelfEvaluationEngine` gate. Update each pinned test deliberately. | post-fix: R-Zero success_rate CAN exceed 0.5; SelfEval score DEPENDS on input. The §12 pin-actual tests flip and are rewritten. | behavior-change | TODO |
| 9 | C | **Routing corpus → autoresearch feedback** — feed item-2's `routing_log.jsonl` into the autoresearch loop so it tunes `LANE_WATTS`/task→specialist from real outcomes (closes the agentic self-improvement loop). | a synthetic corpus drives a measurable tuning proposal; no-corpus → honest UNPROVEN. | needs-experiment | BLOCKED (dep: #2) |
| 10 | A | **God-object analysis** — the 36 files >500 LOC: god-object vs cohesive; propose split targets (report-only, additive). | each "god-object" call backed by a cohesion metric, not just LOC. | report-only | TODO |
| 11 | C | **Chronos discovery + advisory** — unify systemd-user-timer + Hermes `jobs.json` + cohezion `CronManager` into one read-only `ChronosRegistry`; advise deferral of enabled+deferrable jobs at CRITICAL pressure. | real-source smoke unifies all 3 schedulers; advisory at CRITICAL = {deferrable∩enabled}, [] at OK; vault-backup never advised. | additive | DONE (this commit) |
| 12 | C | **Chronos auto-deconfliction subscriber** — `monitor.subscribe(chronos_advise_on_rising_critical)` LOGS the advisory (still report-only) on a CRITICAL *rising* edge, reusing item-1's evictor wiring pattern. | fires once on rising-critical, not on WARNING/sustained; emits the same set `resource_advisory()` returns; writes nothing in pytest. | additive | TODO |
| 13 | C | **Chronos control surface (permission-gated)** — `pause(job)`/`resume(job)` wrapping `systemctl --user stop/start <unit>` (systemd) + Hermes pause API; DRY-RUN by default, real action only behind an explicit `apply=True`. | dry-run emits the exact command without running it; `apply=True` round-trips on a throwaway test unit; a critical (non-deferrable) job is refused. | behavior-change | TODO |

## Notes
- Items 1–5 are additive/safe; 6–8 are behavior-changing (land behind the falsifiable check, else report-only).
- The loop self-terminates when all rows are DONE/RETIRED and notifies.
