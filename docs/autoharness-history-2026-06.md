# AutoHarness Session History — June 2026

Moved verbatim from `.claude/rules/harness.md` on 2026-07-17 (doctor context-trim: these dated
session narratives loaded into every main-checkout session at ~3k tokens). The active invariants
remain in the rule file.

## GAIA-SDK 4-Lens Adversarial Review (2026-06-30) — what we built this session

FIXED (committed, verified by me):
- **SECURITY H5 (CRITICAL)** — `exec(llm_code, {"np": np})` RCE across 4 sinks (agi_reasoning,
  aimo_reasoning, symbolic_executor, competition/llm_fallback). New `safe_exec.py::safe_exec_globals`
  = restricted `__builtins__` allow-list. Stop-gap; DURABLE fix = out-of-process sandbox.
- **CORRECTNESS HIGH** — Lever 1 UNDER-routed: `quality_gate_chars`≈0 for long_generation/code too, so
  the blanket override let essays pass at the 1B NPU. Now overrides only for short_categorical/short_answer.
- **FAILURE #1** — regression gate `evaluate_regression` fail-closed hole (a CRITICAL fixture erroring
  while another passes still promoted). Now any critical-unevaluable → fail-CLOSED.
- **FAILURE #2** — SurrealDB returns SQL errors as HTTP 200 + status='ERR' (string result); loaders
  iterated it as fixtures → regression_check inverted → FROZE the loop on a fresh/missing-table deploy.
  `_surreal_rows` treats ERR as no-rows.
- **FAILURE #4** — `_safe_ident` now SLUGIFIES (was: RAISE on spaces → skills silently un-gated).

RESOLVED 2026-06-30 (follow-up GAIA-SDK orchestration round — 3 agents, disjoint files, 2004 green):
- **H1 FIXED** — `refine()._ensure_golden_fixtures` lazily bootstraps fixtures from the CURRENT
  pre-edit prime (non-circular) when a skill has none; anti-poisoning (force critical=False, reject
  <3-char expected); `get_singleton` delegates to `create()`. Discrimination PROVEN (neutralize → gate
  promotes a regressing candidate; restore → blocks + records pending_review). The gate now FIRES.
- **H2 FIXED** — `jepa_coherence` is a tracked `DegradationDetector` MetricBaseline (low → WARNING).
- **JEPA task-blindness FIXED** — `set_task` threads task_description into the world model; verdict now
  task-dependent. `_parse_coherence` returns first in-range float.
- **Dormancy cluster** — concurrency probe → :13305; first-call predicted_tier uses lazy property;
  CR1 honestly documented as intentional caller-supplied (no fake caller); overnight coverage n>0.
- STILL OPEN: H5 durable out-of-process sandbox (the allow-list is a stop-gap); `inference_provider`
  built-but-unread (decide consume-or-delete); `get_pending_approvals` operator surface; auto-fixture
  critical-promotion is an intended HITL step.

CORRECTION 2026-06-30 (re-evaluation adversarial review — 3 lenses; the prior "RESOLVED" overclaimed):
- **H1 is NOT actually fixed for its stated purpose (CONFIRMED HIGH).** The two H1 sub-fixes are
  mutually self-defeating: anti-poisoning forces every auto-fixture `critical=False`, but
  `evaluate_regression` only BLOCKS on `critical=True`. So NO production path can block a behavioral
  regression — the gate's `return False` is reachable only via the inference-OUTAGE clause
  (`evaluated==0`). The keystone "discrimination" test drove `run_fn` to RAISE (outage), so it proved
  the wrong claim. H1 makes the gate RUN, not BITE. Real fix: GROUND `expected_output` by running the
  CURRENT skill (via `_regression_run_fn`) so a divergence is a real regression → safe to mark critical.
  → RESOLVED 2026-06-30 (falsification-first): `_ground_fixture` keeps a fixture only if the current
  skill's output contains the keyword → `critical=True` → the gate BITES a real regression (inference
  UP), proven discriminating (neutralize `critical=True` → keystone+bootstrap tests RED). Guarded in
  dormancy_scan (`ground_fn=ground`). The keystone test was rewritten to the regression claim, not outage.
- **The dormancy scanner itself shipped 2 false-GREEN guards (CONFIRMED HIGH) — NOW FIXED.** M1/Lever1
  were declaration-counters (floor met by a `=None` decl + a comment); stayed green with all consumers
  deleted. Re-pinned to the consumption read + comment-skip; falsification-proven (neutralize→RED).
- **H5 has an untested AVAILABILITY regression (CONFIRMED MED).** The allow-list denies `__import__`, so
  LLM solvers that `import numpy`/`import math` now fail → fallback success rate silently drops. Plus
  the gadget escape (`().__class__.__bases__[0].__subclasses__()`→real builtins) is open (security lens
  concurs). "H5 closed" overstates — only the trivial `import os` path is closed. Fix: out-of-process
  sandbox + a curated safe-import allow-list for the solver sinks.
- **JEPA task-awareness FIRES but on a garbage signal (CONFIRMED MED).** Coherence tracks PROMPT LENGTH,
  not tractability (trivial→0.20, verbose-impossible→0.97). H2 plumbing + parse fix are sound; the
  estimate is noise → would REROUTE most real tasks if it drove routing.
- LOW: `_safe_ident` slugify collisions (distinct skills → shared fixtures); `journey_tracker.py:566`
  `operation_type` raw interpolation; `auth=("root","root")`×4 (localhost-bound); integration smoke is
  green-by-skip when :13305 is down (no surfaced SKIP signal); `recommended_tier` metric key dead
  (but the `_resolve_tier` VALUE path IS consumed — routing is live).
- VERIFIED SOUND by the re-eval: Lever1 under-routing fix; registry #1/#2 fail-policy; H2/parse plumbing;
  the scanner's H1/H2/ME1 guards + self-test + cron robustness.

(Original deferred list, now mostly resolved above:)
DEFERRED (architectural / dormancy backlog — NOT quick fixes):
- **WIRING H1 (the big one)** — the golden-fixture → regression-gate → HITL-approval chain is wired
  component-by-component but DORMANT end-to-end: `bootstrap_fixtures` has NO production caller, so the
  `golden_fixture` table is empty → both gates fail-open → `_record_blocked_promotion` never fires. The
  overnight loop (`overnight_improve.py`) IS the intended population path but isn't the live loop. The
  M1 "FIXED"/"live" claim is true at the wiring layer, false end-to-end. Fix = populate fixtures (run the
  overnight bootstrap, or wire a guarded population step) — until then the regression gate is a no-op.
- **WIRING H2** — `jepa_coherence` is written into `degradation_metrics` but `DegradationDetector.
  check_degradation` reads a fixed key set that omits it → silently dropped (JW1 promise unfulfilled).
- **CORRECTNESS MED** — the JEPA gate is now a constant-PROCEED no-op: `predict_next_state` never reads
  `task_description` and `check()` gets no `current_state` → task-blind, identical verdict every call.
  Benign (safe no-op) but spends an NPU call for no signal. Fix = feed task_description + live state.
- **DORMANT capabilities** (confirmed across bug-hunt + review): `inference_provider` built-but-unread;
  `SkillRefinerFactory.get_singleton()` doesn't wire `_regression_run_fn`; `_recompute_tier_at_compaction`
  (CR1) orphaned; `get_pending_approvals` has no operator-facing consumer; `get_recommended_concurrency`
  probes dead :13306; first-call predicted_tier gap; `_parse_coherence` first-token; overnight coverage
  overstated (marks done at 0 fixtures), deadline checked only between cycles.
- VERIFIED SOUND (no real bug): Wilson-LCB math, `_resolve_tier` direction, `_engine_for` relative
  mapping, SurrealQL injection guards (json.dumps + slugified _safe_ident), asyncio.run fail-open.

## GAIA-SDK Bug Hunt (2026-06-30) — latent bugs the green suite missed

FIXED (committed, verified live):
- **#1 HIGH** `build_live_jepa_gate` lookahead 3→1: with k>1 the gate takes the trajectory MIN but
  the LemonadeWorldModel degrades coherence over zero-action steps → constant ~0.15 → task-blind
  constant REROUTE → systematic over-routing. Now single-step PROCEED (0.85). (Follow-on: feed
  task_description into the world model + a non-degrading rollout so k-step is meaningful.)
- **#8 MED** `evaluate_regression` fail-CLOSED hole: swallowed ALL per-fixture errors → returned True
  (promotion allowed) when inference down. Now: per-fixture error fail-open, but well-formed-fixtures-
  but-none-evaluable → fail-CLOSED (matches the M1 contract).
- **#4 MED** `make_executor` probed dead :13306 in `lemonade_available()` → exec_provider always None.
  Now probes :13305 (matches M3).

DEFERRED (documented backlog, lower value / architectural):
- **#2** `self._inference_provider` is built (post-#4) but UNREAD by `execute_task` (uses the caller's
  `execute_fn`); same for RetrospectionEngine. Vestigial plumbing — decide: consume it as a default
  execute_fn, or delete the parameter + document execute_fn-required. (The LIVE local-inference path
  is `make_local_execute_fn → _get_orchestrator → :13305`, which works.)
- **#3** REROUTE direction: `_resolve_tier` escalates UP (H4, correct per research) but jepa_gate.py
  docstrings still say "cheaper" (stale) — reconcile the comments.
- **#5** `SkillRefinerFactory.get_singleton()` doesn't wire `_regression_run_fn` (only `create()` does)
  — latent (no prod callers). **#6** W4 predicted_tier hint dropped on the FIRST task (lazy
  skill_refiner built after execute_fn). **#7** deprecated `asyncio.get_event_loop()` patterns
  (executor.py:1022 dead branch, :1456 the "Event loop is closed" source). **#9** `_parse_coherence`
  can latch a stray integer (mitigated by temp=0).
- VERIFIED-CLEAN: no stealth bare-excepts, no bad sys.executable subprocess, Wilson-LCB math sound,
  `_safe_ident` injection guard present, gate_chars/min_tier_index threading correct.

## House-in-Order: keystone live-routing fixes (2026-06-30)

- **DEAD-PORT KEYSTONE (the empty-output root cause):** `local_inference._get_orchestrator()` built
  `build_triune_orchestrator()` — which targets the per-port `:13306/:13307/:13309` servers that are
  redundant/OFFLINE per N1. So the GIC's CORE execute path (`make_local_execute_fn`) hit dead ports →
  every tier failed → cascade escalated to the end → returned `''`. Symptoms it caused: degenerate
  all-CPU routing, the overnight loop learning all-cpu, empty generation via make_local_execute_fn.
  **Fix:** use `build_triune_omni_orchestrator()` (the :13305 OmniRouter). VERIFIED LIVE: a categorical
  task now returns `tier_used=npu, escalations=0, out='POSITIVE'` (was cpu/3/'').
- **Lever 1 (per-task quality gate):** `TieredOrchestrator.run(gate_chars=N)` overrides the fixed
  per-tier `min_chars` with `task_classifier.classify(prompt).quality_gate_chars` (0 for
  short_categorical); `make_local_execute_fn` threads it. TRUST tiers untouched. Verifier-per-task
  (arXiv 2605.17554). Discriminating: `tests/inference/test_orchestrator.py::test_lever1_task_gate_overrides_fixed_tier_gate`.
- **Pre-existing test debt (NOT this session's regressions):** ~20 failures predate the session
  (confirmed: 22 failed at the pre-session commit; this work fixed 2). Subsystems: MoESkillRouter
  (`SkillRefiner.__init__` lost its `moe_router` kwarg — MR1/MR4 drift), capability_gap_scan,
  loopception G18 (Manifold/SwarmEnv journey wiring), inference_wiring_n5. Separate cleanup pass.

