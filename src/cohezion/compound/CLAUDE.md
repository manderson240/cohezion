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

**RV** (RiVER) — RV1: z-score normalization after ≥3 samples; RV2: `1/(1+wins)` frequency penalty in `_autodata_select()`

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

Known dormant (do not re-close without discriminating test):
- `inference_provider` — accepted by `execute_task`, not read inside it
- `_recompute_tier_at_compaction` — no caller in production path (CR1)

## File Size Warning

`executor.py` is 1,690 lines. Follow Single Responsibility — add to `execute_task` only when it's genuinely execution. New signals (e.g. new metric type) belong in their own module wired in via constructor injection.
