# Compound Module — Local Context

This file loads in addition to the root `CLAUDE.md`. Anything in the root applies here too.
Omitted: Kaggle/portfolio work, web UI, physics engine, SurrealDB schema.

## Entry Points

| Symbol | File | Role |
|--------|------|------|
| `CompoundExecutor` | `executor.py` (1,690 lines) | 11-step execution pipeline |
| `SkillRefiner` | `skill_refiner.py` | PRIME skill updates; seesaw gate; durable spine |
| `ExecutorFactory` | `executor_factory.py` | Preferred constructor — wires all sub-systems |
| `make_executor()` | `__init__.py` | One-liner factory via `from cohezion.compound import make_executor` |
| `DegradationDetector` | `degradation_detector.py` | EMA thresholds, alert history, tier suggestions |
| `JourneyTracker` | `journey_tracker.py` | 12D trajectory; FLUME encoder; cross-session identity |
| `JepaGate` | `jepa_gate.py` | Pre-execution PROCEED/REROUTE/SKIP verdict |
| `DifficultyEstimator` | `difficulty_estimator.py` | GIC tier prediction; prompt complexity features |
| `MoESkillRouter` | `moe_skill_router.py` | Expert weight learning; perspective diversity |
| `FailureAttributor` | `failure_attributor.py` | FAPO: format/cascading/retrieval/reasoning |
| `CompoundHealthOracle` | `compound_health_oracle.py` | FD regime synthesis; cross-session persistent; 4th routing signal |

## Quick Test Commands

```bash
uv run pytest tests/compound/ -v          # full compound suite
uv run pytest tests/compound/ -q -x       # fail-fast
uv run pytest tests/test_journey_tracker.py -q
uv run pytest tests/compound/test_loopception.py -q  # LC1-LC3
```

## Invariant Quick Reference (by series)

**CB** (Compound Behavior) — executor + detector + refiner contracts
- CB4: `_populate_semantic_cache` uses `self._semantic_cache`, not `SemanticCache.get_instance()`
- CB5: `ExecutorFactory.create()` auto-creates `DegradationDetector` and wires `set_routing_callback`
- CB6: `CompoundExecutor.get_health()` delegates to `_degradation_detector.get_health_summary()`
- CB7: `DegradationDetector.to_dict()/from_dict()` round-trips baselines + call_count
- CB11: `snapshot()` returns exactly 6 keys; `diff_snapshots` is a static method
- CB12: `suggest_routing_tier()` always returns `"npu"/"igpu"/"cpu"`, never raises, never None
- CB13: DegradationDetector and task_classifier must agree ≥90% on the 8-test fixture
- CB14: `_lm_signal_cites_metrics()` gate — LM deviation claims must cite observed metric values
- CB15: `_seesaw_check()` blocks PRIME invariant negation — deterministic, no LM calls
- CB16: `ExecutionMetrics` has `tier_used/tool_call_count/escalation_count` safe-default fields

**FA** (Failure Attributor) — FA1-FA3: signature, kwarg, category enforcement

**LC** (Loopception) — LC1: `run_batch` in-process; LC2: `LemonadeEmbedBridge` as FLUME encoder; LC3: gym envs wire `step()` into JourneyTracker

**RL** (Process Reward) — RL1-RL4: `prediction_error` stored back, `process_reward_mean()` non-None, confidence boosted, `mgpo_weight` biased

**RV** (RiVER) — RV1: NIG normalization from n=1 (Gelman BDA §2.6; replaced z-score warm-up); RV2: `1/(1+wins)` frequency penalty in `_autodata_select()`

**AD** (Autodata) — AD1: `_autodata_candidates()` always ≥1; AD2: highest keyword overlap wins; AD3: delegates to both

**W** (Wiring) — W1-W5: JepaGate injected; identity lifecycle wired; suggested_tier in metrics; predicted_tier in metrics; skill_proximity consumed by `_generate_recommendation()`

**GIC** (Difficulty Estimator) — GIC1: `unknown` before records; GIC2: cheapest successful tier; GIC3: wired via SkillRefiner

**SRS** (Durable Spine) — SRS1-SRS3: `to_dict/from_dict/save_state/restore_state` round-trips; CB16 safe defaults

**RQGM** (Red Queen) — epoch rotation via `_goal_epoch`; 3-cycle goal targets

**HO** (Health Oracle) — HO1-HO4: `to_dict/from_dict/save_state/restore_state`; `to_health_dict()` API; cross-session persistence via `~/.cohezion/oracle_state.json`

**OC** (Oracle Consumption) — OC1-OC5: `oracle_tier` 4th signal in `_resolve_tier()`; STUCK→floor escalation; CHAOTIC→cpu; MAX-CAPABILITY (oracle never lowers a confident prediction); backward-compatible default None

## Wiring Discipline (non-destructive)

A method that ACCEPTS a value is not wired. Wiring = a production (non-test, non-def) consumer reads it and acts.
Before marking anything wired: `grep -n "that_method\|that_field" src/cohezion/compound/*.py | grep -v test | grep -v def`.

**TL** (Token Ledger) — TL1-TL3: Quarter-on-a-String audit; wired 2026-07-05
- TL1: `execute_task()` calls `_token_ledger.record_local()` for npu/igpu/cpu tiers; `record_cloud` NOT called
- TL2: `execute_task()` calls `_token_ledger.record_cloud()` for cloud tier; `record_local` NOT called
- TL3: `make_executor()` auto-creates and injects `TokenLedger()` as `token_ledger=`

**AO** (AOEP-v0 Governance Scorecard) — arXiv:2606.30306; wired 2026-07-06
- AO1: `AOEPScore` is a dataclass with exactly 8 fields: `{authority, scope, mutability, provenance, recoverability, actionability, overall, gaps}`
  - **Verification**: `{f.name for f in dataclasses.fields(AOEPScore)} == {"authority","scope","mutability","provenance","recoverability","actionability","overall","gaps"}`
- AO2 (discriminating): `score_authority(has_authority_gate=True) == 1.0`; `score_authority(has_authority_gate=False) == 0.0` — a wrong impl ignoring the probe fails the `> without_gate` assertion
  - **Verification**: `uv run pytest tests/compound/test_aoep_scorecard.py::TestAOEPAuthority -q` → 4 passed
- AO3 (discriminating): `score_scope(has_scope_filter=True) > 0.0`; `score_scope(has_scope_filter=False) == 0.0`
  - **Verification**: `uv run pytest tests/compound/test_aoep_scorecard.py::TestAOEPScope -q` → 4 passed
- AO4 (discriminating): `score_mutability(has_seesaw=True) > 0.0`; `score_mutability(has_seesaw=False) == 0.0`
  - **Verification**: `uv run pytest tests/compound/test_aoep_scorecard.py::TestAOEPMutability -q` → 4 passed
- AO5: `run().overall == mean(6 axes)`; `run().gaps` lists every axis < 0.5
  - **Verification**: `uv run pytest tests/compound/test_aoep_scorecard.py::TestAOEPRun -q` → 4 passed
- AO6 (live baseline): `AOEPScorecard().run().overall >= 0.5` with current harness (confirmed 0.67 on 2026-07-06, no gaps)
  - Authority=1.0, Scope=0.5, Mutability=0.5, Provenance=0.5, Recoverability=1.0, Actionability=0.5
  - Full suite: `uv run pytest tests/compound/test_aoep_scorecard.py -q` → 28 passed

Known dormant (do not re-close without discriminating test):
- `SkillConsensusVoter._inference_provider` — accepted/stored (N5), deliberately NOT wired to a
  consumer (2026-07-06). Vote aggregation (`_vote_majority`/`_vote_weighted`/`_fallback_single_best`)
  is pure deterministic composite scoring over already-structured `AgentVote` objects — there is no
  free-text output an LLM could ground or improve. Forcing a consumption point here would be
  manufactured complexity, not genuine wiring (see `_llm_reason` in `retrospection.py` for the
  contrasting case where a real free-text output existed). Re-evaluate only if a genuine tie-breaking
  or free-text-rationale need appears in this class.

Closed dormancy gaps:
- `inference_provider` (CompoundExecutor) — the 2026-07-04 claim below this line was WRONG: no
  `TestIPInferenceProviderConsumption` class exists anywhere in the repo, and `_call_execute_fn` never
  referenced `_inference_provider`. Actually fixed 2026-07-06: `execute_task`'s `execute_fn` param is
  now optional; when omitted, a default is built from `self._inference_provider` via
  `make_local_execute_fn(orchestrator=...)` (new override param on that helper). Raises `ValueError`
  when neither is available. Tests: test_inference_provider_default_execute_fn.py (3 discriminating
  cases: genuine invocation, explicit execute_fn takes priority, no-provider raises).
- `inference_provider` (RetrospectionEngine) — same 2026-07-06 fix. `suggest_skill_refinements()` now
  calls `self._inference_provider.run()` for a grounded rationale, gated by `_cites_a_learning()` (a
  CB14-style citation gate: ungrounded/hallucinated text is rejected, falling back to the original
  heuristic reason string). Tests: test_retrospection_inference_consumption.py (4 discriminating
  cases: grounded response used, ungrounded response rejected, no provider, provider raises).
- `_recompute_tier_at_compaction` — wired in `LongHorizonTask.execute_step()` at context-compaction boundary (CR1, 2026-07-04); tests in test_tier_resolution.py::TestCompactionReroute
- `GlobalMetricsAggregator._window_size_sec` (2026-07-06) — accepted/stored/documented since creation
  but `get_dashboard_snapshot()`'s trend-window loop hardcoded `60`/`300` literals instead of reading
  it, so a non-default `window_size_sec` was silently ignored exactly where its own docstring said it
  applied. Fixed: trend window boundaries and the overall lookback span now use `self._window_size_sec`.
  Tests: test_global_metrics_window_size_wiring.py (default-60 span unchanged at 300s; custom 10s span
  correctly totals 50s, not 300s).

## File Size Warning

`executor.py` is 1,690 lines. Follow Single Responsibility — add to `execute_task` only when it's genuinely execution. New signals (e.g. new metric type) belong in their own module wired in via constructor injection.
