---
title: "Wiring-sweep ledger — file-level reachability remediation"
created: 2026-06-06
owner: "wiring-sweep loop (session cron 9aa80dae, every :19/:49)"
policy: "NON-DESTRUCTIVE — orphans are WIRED, never deleted. Static import edge only."
baseline: "top-level package orphans = 0 (audit, 2026-06-06). Deepening to FILE level."
termination: "two consecutive full-package passes with 0 unwired → notify + stop."
---

# Wiring-sweep ledger

The package-level V-model audit (`scripts/audits/vmodel_module_audit.py`) reports **0
top-level orphans** — every `src/cohezion/<pkg>` is reachable. This loop deepens to
**file-level**: every `.py` reachable by a static intra-repo `import` edge.

## Classification (each candidate must be sorted before wiring)

A file with zero static `import cohezion…<mod>` edges from *production* code is a
**candidate**, not automatically an orphan. Sort it first:

| Class | Meaning | Action |
|---|---|---|
| **A · genuinely orphaned** | no prod importer, no test, no registry/entry-point use | WIRE to natural consumer or guarded sub-bridge + discriminating test |
| **B · tests-only** | imported by `tests/` but no `src/` module | wire a production consumer OR record as test-covered-only (judgment) |
| **C · `__init__` re-export** | reached via `from .<mod> import X` in a package `__init__` | already wired — verify the re-export uses `X as X` (ruff-safe), record |
| **D · registry / entry-point live** | reached by `skill_registry.json`, filesystem path, CLI entry-point, hook | functionally live — record as wired-by-non-import; do NOT force a fake edge |

The crude grep (`grep compound.<mod>`) over-reports B/C/D as orphans. Per-tick the loop
must classify with `findReferences` / import-grep across BOTH `src/` and `tests/`, and check
`skill_registry.json` + entry-points, before wiring.

**Methodology note (retro 2026-06-06): compiles ≠ reachable.** A `.py` module shadowed by a
same-named PACKAGE (`foo.py` + `foo/`) is dead-on-arrival — Python's finder always picks the
package `__init__`, so the file is reachable by no import even though it compiles cleanly. The
audit's compile check cannot see this. The discriminating probe is `import X; print(X.__file__)`
— if it resolves to `…/X/__init__.py`, the sibling `X.py` is a shadowed husk (human-decision
removal, NOT a wire). This caught the untracked `recursive_trace.py` husk this session (the
tracked `recursive_trace/` package wins; its `resolution_log` is load-bearing). Also: a grep hit
that is a METHOD NAME (`def analyze_audio_telemetry`) is NOT an import edge — verify the hit is a
real `import`, not a substring, before classifying a module reachable.

## Baseline scan — `compound/` (first package, 2026-06-06)

24 file-level candidates surfaced (NOT yet classified — that is the next ticks' work):

```
agi_reasoning, aimo_reasoning, behavioral_eval, chronos, consortium_instigator,
distillation_engine, dual_loop_optimizer, dynamic_compound_system,
dynamic_system_integration, eco_symphony, experiment_correlator, harness,
hiho_lm_gate, journey_to_training, optimized_session_manager, post_execution,
recursive_trace_router, retrospection_validator, self_improvement_orchestrator,
skill_mutation_queue, skill_refinement_validator, tape_logger, test_basic_import,
thermal_autoresearch_executor, workflow_manager
```

### compound/ — CLASSIFIED (2026-06-06)
- **Class A · genuine orphans: 0 remaining — `compound/` file-level sweep COMPLETE.**
  WIRED (9): hiho_lm_gate, journey_to_training, optimized_session_manager,
  thermal_autoresearch_executor, distillation_engine, dynamic_compound_system,
  dynamic_system_integration, consortium_instigator, agi_reasoning, aimo_reasoning.
- **Class B · tests-only (13)**: behavioral_eval, chronos, dual_loop_optimizer, eco_symphony,
  experiment_correlator, post_execution, recursive_trace_router, retrospection_validator,
  self_improvement_orchestrator, skill_mutation_queue, skill_refinement_validator, tape_logger,
  workflow_manager. Test-covered → not dead; production-consumer wiring is OPTIONAL/lower-priority.
  (Note: `chronos` reclassified A→B — my own `tests/compound/test_chronos.py` covers it.)
- **Class D · registry-live (1)**: harness.
- **WIRED this loop**: `hiho_lm_gate` (was Class A) → re-exported through `compound/__init__.py`
  (`check_quality`/`check_sycophancy`/`ppl_score`), guarded. Edge proven by
  `tests/wiring/test_hiho_lm_gate_wired.py` (asserts the names resolve from the package AND are
  the gate's own objects — fails if the edge is removed). Commit: see git.

### swarm/ — CLASSIFIED (2026-06-06), wiring BLOCKED on a circular import
File-level scan found 12 genuine-A candidates (agent_factory, deterministic_discovery_with_skill_fallback,
hf_modelfile_builder, intelligence_pipeline, latent_research_team, lemonade_model_enhancer,
model_capability_registry, model_capability_registry_resource_safe, ollama_context_manager,
parser_v3_validation_oracle, plasma_swarm_router, triune_integration).

**BLOCKED — circular import surfaced (the wiring did its job).** Attempting to wire `agent_factory`
into `swarm/__init__` + adding the required swarm-importing discriminating test changed pytest's
import order to **swarm-first**, which broke 4 already-green compound wiring tests. Root cause
(PRE-EXISTING, verified at baseline): `compound/dynamic_compound_system.py:70` and
`compound/dynamic_system_integration.py` do **module-scope** `from cohezion.swarm import …`. So
`compound/__init__`'s guarded re-exports of those two modules **silently unbind** under swarm-first
import order (the `contextlib.suppress` swallows the partial-import ImportError). Compound-first
import works; swarm-first does not. This is a latent compound↔swarm cycle that wiring exposed.
Reverted the agent_factory edit; swarm/ deferred to the human-decision item below.

### inference/ — CLASSIFIED + DONE (2026-06-06)
14 candidates: 13 Class-B (tests-only: anti_sycophancy, autoharness, autoharness_ce,
context_engineering, distributed_swarm, evaluation_harness, gemini_cli_tier, hardware_telemetry,
headless_claude_tier, orchestrator_autoharness, p0_resilience_mixins, tri_compute_orchestrator,
turboquant_streaming) + 1 genuine-A: **lynx_gate** → WIRED via `inference/__init__` guarded re-export
(LYNXGate, EscalationProbe). Cycle-safe (lynx_gate imports no swarm/compound). Verified robust under
BOTH import orders (inference-first AND compound-first) — the discipline the swarm cycle taught.
inference/ file-level sweep COMPLETE (0 genuine-A remaining).

### physics/ — CLASSIFIED (2026-06-06), in progress
5 candidates: 2 Class-B (usd_simulator, vliw_bridge) + 3 genuine-A (flier_routing, mereon_data,
mhd_mereon), all cycle-safe. WIRED (3): **flier_routing** (FLIERRouter, QubitNode), **mhd_mereon** (MHDMereonOperator, MHDState),
**mereon_data** (get_m120p_vertices, get_m144p_vertices — function re-export) → `physics/__init__`
guarded re-exports, both-order robust. physics/ file-level sweep COMPLETE (0 genuine-A remaining).

### world_model/ — CLASSIFIED (2026-06-06), IN PROGRESS (3 genuine-A, 1 wired/tick)
4 modules, `__init__` re-exported nothing. Classification:
- **Reachable (static src edge)**: jepa_world_model (← world_model/jepa_world_model_persistent + tests).
- **Class A · genuine orphans (3)** — all documented World Model components, 0 src importers,
  cycle-safe; same guarded `world_model/__init__` re-export pattern, one per tick:
  - **surprise_explorer** (SurpriseExplorer, SurpriseRegion) → WIRED d0e8b3b1b
    (`tests/wiring/test_surprise_explorer_wired.py`, both-order robust).
  - **sigreg** (SIGReg) → WIRED 089b9a362 (`tests/wiring/test_sigreg_wired.py`, torch-guarded,
    separate block so torch-absent can't take down surprise_explorer; both-order robust).
  - **jepa_world_model_persistent** (JEPAWorldModelPersistent) → WIRED 4de0b6b88
    (`tests/wiring/test_jepa_persistent_wired.py`, torch-guarded; both-order robust).
world_model/ file-level sweep COMPLETE (3/3 wired, 0 genuine-A remaining).

### governance/ — CLASSIFIED + DONE (2026-06-06), 1 A wired
7 modules, `__init__` re-exported nothing. Classification:
- **Reachable (static src edge)**: autonomy_engine (← mcp/agentskills_bridge), fleet_monitor (←
  swarm/agents/eigent_agent), flume_bridge (← compound/journey_tracker), guardian (←
  governance/scripts/async_guard_v2), knowledge_bridge (← models/routing_log), quadrature_nexus
  (← compound/aimo_reasoning).
- **Class A · genuine orphan (1)**: **concierge** — `ConciergeAgent` (documented Governance-layer
  component) had 0 src importers (only its test); cycle-safe → WIRED via `governance/__init__`
  guarded re-export (ConciergeAgent + SessionBriefing/RoutingSuggestion/RoutingRecord). Proven by
  `tests/wiring/test_concierge_wired.py` (identity check — fails if edge removed). Both-order robust.
governance/ file-level sweep COMPLETE (0 genuine-A remaining).

### models/ — CLASSIFIED + DONE (2026-06-06), 0 genuine-A
5 modules, `__init__` re-exports none. Classification:
- **Reachable (static src edge)**: model_registry (← services/swarm_service), routing_log (←
  model_registry + rho_selector), perch_v2_adapter (← models/birdclef_baseline, intra-package edge).
- **Class B · tests-only (2)**: birdclef_baseline (BirdCLEF Kaggle baseline — no core production
  consumer, test-covered; perch_v2_adapter hangs off it); rho_selector (item-22 RHO instrument,
  test-covered — its PRODUCTION consumer is the planned item 27 SkillRefiner wiring; not forced now).
models/ file-level sweep COMPLETE (0 genuine-A; the 2 Class-B are test-covered, not dead).

### persistence/ — CLASSIFIED + DONE (2026-06-06), already fully reachable
3 modules, `__init__` re-exports none — but all 3 are production-reachable via direct static
import edges (0 orphans, nothing to wire):
- **genesis_persistence** — imported by flume/trajectory_capture, compound/post_execution,
  compound/executor, world_model/jepa_world_model_persistent, integrations/telegram_bot (5 src).
- **obsidian_mcp** — imported by universe/triune_engine, agents/evo_agent, rewards/ratchet (3 src).
- **surreal_logger** — imported by universe/triune_engine, agents/evo_agent (2 src).
persistence/ file-level sweep COMPLETE (0 candidates, 0 genuine-A — already wired by design).

### cache/ — CLASSIFIED (2026-06-06), 1 needs-human (true duplicate)
6 modules; 2 already `__init__`-re-exported (redis_cache, semantic_cache). 4 candidates classified:
- **Reachable (intra-edge present, not orphans)**: cache_warmer (imported by
  compound/executor_helpers/template_matcher), lemonade_encoder + text_encoder (both imported by
  cache/semantic_cache).
- **Class A-as-duplicate → NEEDS HUMAN (1)**: **sentence_encoder** — 0 production importers; its
  `SentenceTransformerEncoder`/`get_encoder()` is a SIMPLER re-implementation of what
  `text_encoder.SemanticTextEncoder`/`get_text_encoder()` already does (SAME model all-MiniLM-L6-v2;
  text_encoder is a strict SUPERSET: adds 256D pad/truncate, n-gram fallback, device handling, and
  is the one `semantic_cache` actually uses). NOT a clean Class-A to auto-wire: re-exporting it would
  legitimize a dead duplicate AND its `get_encoder` name collides with the FLUME `vae_encoder.get_encoder`
  already imported in semantic_cache. Per rule 3 (verify, don't merge blind) + step 5 (true duplicate →
  surface, don't guess): flagged below. NOT wired this tick (no fake edge, no deletion).
0 clean Class-A wired this tick — cache/ is production-reachable except the duplicate (human-gated).

### platform/ — CLASSIFIED + DONE (2026-06-06)
16 modules; 9 already `__init__`-re-exported. 7 remaining candidates classified:
- **Class A · genuine orphan (1)**: **agnostic_integrations** (0 static importers anywhere — src,
  tests, registry, entry-points; cycle-safe, imports nothing from cohezion) → WIRED via
  `platform/__init__` guarded re-export (IDEIntegrationAdapter, AntigravityIDEAdapter,
  ClaudeCodeAdapter, ZedCodeAdapter, AgnosticExecutionBroker), names in `__all__` (ruff-safe).
  Edge proven by `tests/wiring/test_agnostic_integrations_wired.py` (identity check + constructs
  the broker through the package surface — fails if the edge is removed). Both-order robust.
- **Class B · tests-only (3)**: oom_evictor (item-1 act-layer; `tests/platform/test_oom_evictor.py`),
  session_tracker, tier_optimizer (`tests/platform/test_tier_optimizer.py`). Test-covered → not
  dead; production-consumer wiring OPTIONAL/lower-priority.
- **Class D · registry-live (1)**: mcp_server (referenced in `registry/skill_registry.json`).
- **Reachable (intra-edge present, not candidates)**: memory_pressure (imported by oom_evictor +
  resource_manager + compound/chronos), resource_manager (imported by memory_pressure + agentjet/trainer).
platform/ file-level sweep COMPLETE (0 genuine-A remaining).

### environments/ — CLASSIFIED + DONE (2026-06-06), 1 A wired
4 modules; `__init__` re-exported manifold_env + swarm_env. Classification:
- **Reachable**: manifold_env (`__init__` re-export + src/tests + gym-registered), swarm_env
  (`__init__` re-export, Class C).
- **Class B · tests-only (1)**: arc_env (`tests/` covers it; no core production consumer).
- **Class A · genuine orphan (1)**: **auto_generator** — EnvironmentGenerator / EnvironmentSpec /
  GeneratedEnvironment / GeneratedCodeValidator (specification-driven environment synthesis) had
  ZERO importers anywhere (src, tests, registry, entry-points); cycle-safe (imports no cohezion
  module at scope, only torch + transformers) → WIRED via `environments/__init__` guarded re-export
  in a SEPARATE suppress block (transformers/torch are heavy module-scope deps — isolating them so
  their absence can't unbind the load-bearing ManifoldEnv/SwarmEnv imports). Proven by
  `tests/wiring/test_auto_generator_wired.py` (identity check on all 4 names + `__all__` membership;
  importorskip transformers/torch). Both-order robust (env-first + compound-first).
environments/ file-level sweep COMPLETE (0 genuine-A remaining).

### data_mesh/ — CLASSIFIED + DONE (2026-06-06), 1 A wired
4 modules; `__init__` re-exported nothing. Classification:
- **Reachable (static src edge)**: data_product (src_ext=2), journey_telemetry (src_ext=7),
  universe_telemetry (src_ext=3).
- **Class A · genuine orphan (1)**: **audio_telemetry** — the BirdCLEF-2026 bioacoustic schema
  (TaxonomyLevel / BirdSpeciesNode / AudioSegmentMetadata / SpectrogramConfig /
  AudioTelemetryEvent) had ZERO importers anywhere; the lone "audio_telemetry" grep hit in
  `learning/ouroboros.py:83` is a METHOD NAME (`analyze_audio_telemetry`), not an import.
  Cycle-safe (imports only stdlib + pydantic) → WIRED via `data_mesh/__init__` guarded re-export.
  Proven by `tests/wiring/test_audio_telemetry_wired.py` (identity on all 5 names + `__all__`).
  Both-order robust (data_mesh-first + compound-first).
data_mesh/ file-level sweep COMPLETE (0 genuine-A remaining).

### pipeline/ — CLASSIFIED + DONE (2026-06-06), 1 A wired
4 modules; `__init__` re-exported nothing. Classification:
- **Reachable**: weight_bridge (intra-package edge + tests).
- **Class B · tests-only (2)**: hyperparameter_debate, trained_navigator (test-covered).
- **Class A · genuine orphan (1)**: **incremental_trainer** — IncrementalResult /
  IncrementalVAETrainer / IncrementalRLTrainer (online/incremental VAE+RL training) had ZERO
  importers anywhere; cycle-safe (numpy only, no cohezion module-scope import) → WIRED via
  `pipeline/__init__` guarded re-export. Proven by
  `tests/wiring/test_incremental_trainer_wired.py` (identity on all 3 names + `__all__`).
  Both-order robust (pipeline-first + compound-first).
pipeline/ file-level sweep COMPLETE (0 genuine-A remaining).

### substrate/ — CLASSIFIED + DONE (2026-06-06), 1 A wired
4 modules; `__init__` re-exported kv_cache_tracker + overload_coordinator. Classification:
- **Reachable**: kv_cache_tracker (`__init__` + intra), overload_coordinator (`__init__` + intra).
- **Class B · tests-only (1)**: hardware_monitor (test-covered).
- **Class A · genuine orphan (1)**: **popcorn** — Popcorn-CLI kernel submission API
  (submit / SubmitResult) had ZERO importers anywhere; the lone "Popcorn" hit in
  `scripts/compound_kernel_cycle.py` is a LOG STRING, not an import. Cycle-safe (subprocess/stdlib
  only) → WIRED via `substrate/__init__` guarded re-export. Proven by
  `tests/wiring/test_popcorn_wired.py` (identity on submit + SubmitResult + `__all__`).
  Both-order robust (substrate-first + compound-first).
substrate/ file-level sweep COMPLETE (0 genuine-A remaining).

### gateway/ — CLASSIFIED + DONE (2026-06-06), 0 genuine-A (1 entry-point recorded)
4 modules; `__init__` re-exported ngrok_adapter. Classification:
- **Reachable**: demo_gateway (intra-edge), mcp_server (intra-edge — imported by mcp_http_server),
  ngrok_adapter (`__init__` re-export + tests).
- **Class D · entry-point (1)**: **mcp_http_server** — the pre-scout flagged it as a zero-static-edge
  candidate, but a deeper look shows it is a runnable SERVER entry-point (`def main()` +
  `if __name__ == "__main__"`, the HTTP MCP server for Claude.ai connectors). Reachability is its
  runnability (`python -m cohezion.gateway.mcp_http_server`), NOT an import edge. Per the rule,
  entry-point files are functionally live → recorded wired-by-entry-point; re-exporting its `main()`
  would be a consumer-less FAKE edge (forbidden). Imports cleanly (no latent import bug). NOTE: no
  TRACKED launcher references it (no pyproject `[project.scripts]`, systemd unit, or shell script) —
  a deployment-wiring TODO for a human, NOT a fake import edge the loop should force.
gateway/ file-level sweep COMPLETE (0 genuine-A; 1 Class-D entry-point recorded).

### rl/ — CLASSIFIED (2026-06-06), IN PROGRESS (1 of 4 genuine-A wired)
10 modules. Classification:
- **Reachable**: environment (src_ext=3), evo (intra+tests), reward_shaping (intra+tests),
  task_generator (src_ext+intra), trainer (src_ext=6).
- **Class B · tests-only (1)**: ppo_trainer.
- **Class A · genuine orphans (4)** — all 0 importers anywhere:
  - **causal_interpreter** (ActivationPatcher / CausalInterventionTester / InterventionResult /
    InterpretabilityReport — causal-intervention interpretability) → **WIRED** via `rl/__init__`
    guarded (torch) re-export. `tests/wiring/test_causal_interpreter_wired.py` (identity + `__all__`,
    importorskip torch). Both-order robust. Imports cleanly (test RUNS, not skipped).
  - **distributed_trainer** (DistributedConfig / ScalingMetrics / DistributedPPOTrainer /
    DistributedLauncher / ScalingBenchmark — DDP/FSDP distributed PPO) → **WIRED** via a SECOND
    guarded `rl/__init__` block (torch). `tests/wiring/test_distributed_trainer_wired.py` (identity
    + `__all__` + a coexistence pin that the causal_interpreter edge stays intact). Both-order robust.
  - **grpo_trainer** (AsyncGRPOTrainer / GRPOConfig) — imports cleanly; remaining genuine-A → next tick.
  - **lora_trainer** — **BLOCKED: broken import** (the wiring discipline surfaced it). `import
    cohezion.rl.lora_trainer` raises `ImportError: cannot import name 'PreTrainedModel' from
    'transformers'` (a transformers-internal `integration_utils` failure in this env). It sat as an
    orphan so its broken import was invisible. NOT wireable with a runnable test until the
    transformers import is resolved — surfaced under "## Needs human decision".
rl/ NOT complete — 2 of 4 genuine-A WIRED (causal_interpreter, distributed_trainer); 1 clean genuine-A
remains (grpo_trainer → next tick) + 1 blocked (lora_trainer, transformers import).

## Swept packages
| Package | Swept | Candidates | A wired | A remaining | B/C/D recorded | Needs-human |
|---|---|---|---|---|---|---|
| compound | **DONE** | 24 | 9 (+aimo_reasoning) | 0 | 13 B + 1 D | 3 (below) |
| swarm | classified | 24 | 0 (BLOCKED) | 12 | — | circular import (below) |
| inference | **DONE** | 14 | 1 (lynx_gate) | 0 | 13 B | 0 |
| physics | **DONE** | 5 | 3 (+mereon_data) | 0 | 2 B | 0 |
| platform | **DONE** | 7 | 1 (agnostic_integrations) | 0 | 3 B + 1 D | 0 |
| cache | classified | 4 | 0 | 1 (dup) | 3 reachable | 1 (sentence_encoder dup) |
| persistence | **DONE** | 3 | 0 | 0 | 3 reachable | 0 |
| models | **DONE** | 5 | 0 | 0 | 2 B + 3 reachable | 0 |
| governance | **DONE** | 7 | 1 (concierge) | 0 | 6 reachable | 0 |
| world_model | **DONE** | 4 | 3 (surprise_explorer, sigreg, jepa_persistent) | 0 | 1 reachable | 0 |
| environments | **DONE** | 4 | 1 (auto_generator) | 0 | 1 B + 1 reachable | 0 |
| data_mesh | **DONE** | 4 | 1 (audio_telemetry) | 0 | 3 reachable | 0 |
| pipeline | **DONE** | 4 | 1 (incremental_trainer) | 0 | 2 B + 1 reachable | 0 |
| substrate | **DONE** | 4 | 1 (popcorn) | 0 | 1 B + 2 reachable | 0 |
| gateway | **DONE** | 4 | 0 | 0 | 1 D (entry-point) + 3 reachable | 0 |
| rl | classified | 10 | 2 (causal_interpreter, distributed_trainer) | 2 | 1 B + 5 reachable | 1 (lora_trainer import) |

## Needs human decision
- **`rl/lora_trainer` broken import (transformers).** `import cohezion.rl.lora_trainer` raises
  `ImportError: cannot import name 'PreTrainedModel' from 'transformers'` (failure inside
  `transformers/integrations/integration_utils.py: from .. import PreTrainedModel, TrainingArguments`
  — a transformers-version internal issue). The module sat as an orphan (0 importers), so this latent
  breakage was invisible; the wiring sweep surfaced it. NOT a wiring fix — needs a dependency/version
  resolution (pin/upgrade transformers, or make lora_trainer's transformers import lazy/guarded).
  Until then lora_trainer cannot be wired with a runnable discriminating test. (LoRAConfig/LoRAModel/
  SFTTrainer/RLHFTrainer remain unreachable.)
- **compound↔swarm circular import (blocks swarm/ wiring).** `compound/dynamic_compound_system.py`
  + `compound/dynamic_system_integration.py` import `cohezion.swarm` at MODULE scope, so their
  `compound/__init__` guarded re-exports silently unbind under swarm-first import order. Resolve the
  cycle (lazy-import swarm inside those modules' functions, OR make the re-exports order-robust)
  before file-level-wiring swarm/. NOT fixed by the loop (architectural / behavior-affecting).
- **`cache/sentence_encoder` vs `cache/text_encoder` — TRUE functional duplicate.**
  `sentence_encoder.SentenceTransformerEncoder`/`get_encoder()` is a simpler re-implementation of
  `text_encoder.SemanticTextEncoder`/`get_text_encoder()`: SAME model (all-MiniLM-L6-v2), but
  text_encoder is a strict superset (256D pad/truncate + n-gram fallback + device handling) and is
  the one `semantic_cache` uses. sentence_encoder has 0 production importers (test-only). Per
  non-destructive policy rule 4 (consolidation = integrate INTO the canonical sibling first, the
  empty husk is a downstream consequence — never a blind delete): the likely resolution is to fold
  any unique value of sentence_encoder INTO text_encoder, then sentence_encoder's removal is
  bookkeeping. NOT done by the loop (consolidation is permission-gated + behavior-affecting). Also
  note the `get_encoder` name collides with FLUME `vae_encoder.get_encoder` (imported in
  semantic_cache) — a re-export would be a footgun. Decision needed: consolidate vs keep-as-distinct.
- **`model_capability_registry` vs `model_capability_registry_resource_safe`** — surface-name pair
  in swarm/; verify same-concept (consolidate) vs distinct (rename) before wiring. Hazard, not merge.
- **`ReasoningModel` surface-name duplicate** — both `compound/agi_reasoning.py` and
  `compound/aimo_reasoning.py` define a class `ReasoningModel`. Per non-destructive policy rule 3
  (surface-name duplicates are hazards to VERIFY, not merge blind): confirm whether these are the
  same concept (consolidate) or legitimately distinct (rename one). NOT merged by the loop. The
  wiring re-exports agi's `ReasoningModel` + aimo's distinctive `AIMOScaler`/`ProcessRewardModel`.
- `src/cohezion/compound/test_basic_import.py` — a `test_` file living under `src/` not `tests/`.
  Moving or removing it is destructive; surfaced for a human call (the loop will not touch it).
- **hiho_lm_gate deeper integration** — its MODEL-BASED sycophancy/ppl gate overlaps
  `inference/anti_sycophancy.py` (which has its own heuristic `check_sycophancy_risk`) and AUTODQA.
  Wiring the model gate INTO either would CHANGE behavior → human decision, not an auto-wire. The
  re-export above is the non-behavior-changing edge; deeper integration is deferred to a human.

## Next tick
**13 packages fully DONE**: compound, inference, physics, platform, persistence, models, governance,
world_model, environments, data_mesh, pipeline, substrate, gateway. `cache/` classified (0 clean-A;
1 dup → human); `swarm/` BLOCKED (cycle — human decision).

**Next tick: finish `rl/`** — 1 clean genuine-A remains (`grpo_trainer`, imports cleanly), wire it
via the same guarded `rl/__init__` (torch) re-export + discriminating test; then `rl/` has only
`lora_trainer` left, BLOCKED on the transformers import (human). After grpo_trainer, mark rl/ DONE.
**Pre-scouted clean genuine-A in other unswept packages** (from the multi-package scan, all
main_guard=0 libraries): `hookify/adversarial_review`, `audio/{moshi_client, protoclr}`,
`rl/grpo_trainer`. Entry-point (main_guard=1, record Class-D not wire):
`healing/{amd_s2idle_report, deep_audit, drift_analyzer, platform_audit, utilization_audit}`,
`knowledge_graph/cli`, `simulation/{distributed, glass_box_debate}`,
`reliability/{blackwell_handshake, quantum_performance_monitor}`.

After `rl/`: pick a fresh not-yet-swept `src/cohezion/<pkg>/`
(unswept incl. `api`, `mcp`, `agents`, `core`, `flume`, `universe`, `security`, `swarm`-blocked,
`mycelium`, `simulation`, `audio`, `cost_optimization`, `knowledge_graph`, `healing`,
`reliability`, `hookify`, `dogfooding`, `worldviews`, `ouroboros`, `agents`, …) — classify
file-level, wire genuine Class-A orphans one per tick. For SERVER/CLI modules with a `__main__`
guard and no static importer, classify Class-D entry-point (record, do NOT force a fake `main()`
re-export). ALWAYS cycle-check + full `tests/wiring/` suite + both-import-order check after.
(Single-module packages already confirmed reachable, NOT orphans — skip: knowledge/llm_wiki,
storage/surreal_client, tools/test_generator [C], reporting/nightly [B], optimization/r_zero,
patterns/hermetic_design_patterns [B], sandboxing/executor [C], evaluation/self_eval,
deployment/feature_flags.)

Advance to the next not-yet-swept `src/cohezion/<pkg>/`: classify file-level, wire genuine Class-A
orphans one per tick. ALWAYS cycle-check before wiring + run the FULL `tests/wiring/` suite +
both-import-order check after (the swarm lesson). For an entry-point-only module (e.g. an HTTP
server `main()` run as a script) confirm it is Class-D registry/entry-point-live before forcing an
import edge. Do NOT re-attempt swarm/ or cache/sentence_encoder until the human decisions resolve.
