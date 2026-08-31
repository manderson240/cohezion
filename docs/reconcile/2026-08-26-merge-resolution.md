# Merge resolution: origin/main -> worktree-virtual-soaring-shamir (2026-08-26)

Policy: main = prior-revision oracle for content conflicts and safe add/add files; HEAD kept only where
branch-only code imports HEAD-only symbols (depcheck). Every side not taken is preserved under docs/reconcile/.

| file | resolution | why |
|---|---|---|
| `src/cohezion/agi/autoharness_policy.py` | MERGE (method-level, both sides preserved in docs/reconcile/) | MAIN base + branch methods appended (evaluate_policy/register_policy/_register_default_policies, ActionPolicyResult); constructor initialises both registries; evaluate_policy uses main verify_code |
| `src/cohezion/agi/zkfv_compiler.py` | MERGE (method-level, both sides preserved in docs/reconcile/) | MAIN base + branch methods appended (compile_ast_to_gates/generate_proof, PlonkConstraintGate, ZKProof) — 7 branch consumers + main importers both satisfied |
| `src/cohezion/inference/unified_hybrid_router.py` | MERGE (method-level, both sides preserved in docs/reconcile/) | MAIN base (EVI router: __init__(logger_instance, evi_threshold), route(), compute_evi) + branch methods appended (route_by_capability, route_query, aquery_*, _publish_routing_event) + branch keyword-only constructor params (npu_model, cloud_model, prefer_local, lemonade_port) + TaskClass/HybridRouteResponse/_TIER*_PINS placed after imports; 7/7 tests both sides |
| `tests/unit/test_unified_hybrid_router.py` | HEAD (main preserved in docs/reconcile/vss-main-versions) | tests HEAD's router |
| `src/cohezion/agi/__init__.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/agi/recursive_learning.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/core/cross_session_event_bridge.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/inference/delegation_logger.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/inference/prewarm_harness.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/physics/electric_dipole.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/physics/poincare_manifold.py` | MERGE (method-level, both sides preserved in docs/reconcile/) | MAIN base + branch methods appended (origin, to_lorentz) — HUD service test passes |
| `src/cohezion/proactive/__init__.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/reliability/oom_guard.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/contracts.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `tests/compound/test_harness_output_cap.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `tests/compound/test_metric_baseline_bounds.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `tests/unit/test_delegation_logger.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `tests/unit/test_kv_cache_calculator.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `tests/unit/test_proactive_agent.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/api/services/forge.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/arc/transforms.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/compound/degradation_detector.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/compound/harness.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/core/event_bus.py` | MERGE (method-level, both sides preserved in docs/reconcile/) | MAIN base + branch methods appended (publish_sync, Event.model_lifecycle/roster_changed) — 27/27 across both sides tests |
| `src/cohezion/core/persistence/surreal_client.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/data_mesh/event_consumer.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/data_mesh/land_runner.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/inference/image_tier.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/inference/model_card_defaults.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/inference/tri_compute_orchestrator.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/learning/shadow_scripter.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `tests/inference/test_registry.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | main's registry test pins the current roster (claude-sonnet-4-6 heavy fallback); the branch's edit (deepseek-v3.2:cloud, qwen3-coder:30b removed) tracks a registry change that did not land — re-apply with that change |
| `.claude/rules/harness.md` | UNION | both sides append; no deletion |
| `.gitattributes` | UNION | both sides append; no deletion |
| `.githooks/post-commit` | UNION | both sides append; no deletion |
| `.gitignore` | UNION | both sides append; no deletion |
| `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | UNION | both sides append; no deletion |
| `src/cohezion/physics/CLAUDE.md` | UNION | both sides append; no deletion |
| `src/cohezion/skills/HARNESS_BENEFIT_ALIGNMENT_PRIME.md` | UNION | both sides append; no deletion |
| `src/cohezion/skills/ROUTING_ACCURACY_CALIBRATION_PRIME.md` | UNION | both sides append; no deletion |
| `src/cohezion/skills/SURREALDB_MOCK_PERSISTENCE_PRIME.md` | UNION | both sides append; no deletion |
| `src/cohezion/skills/compound_engineering.md` | UNION | both sides append; no deletion |
| `examples/quickstart.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +0/-0 preserved |
| `scripts/_report_untested.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +10/-17 preserved |
| `scripts/_untested_modules.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +19/-19 preserved |
| `scripts/_validate_status_html.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +3/-19 preserved |
| `scripts/adversarial_review_oscillation.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +13/-4 preserved |
| `scripts/agent_task_dispatcher.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +17/-46 preserved |
| `scripts/build_dgm_corpus.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +4/-2 preserved |
| `scripts/calibration/surrealdb_vault_sync.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +1/-3 preserved |
| `scripts/capella_probe.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +7/-5 preserved |
| `scripts/ci/dormancy_scan.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +40/-122 preserved |
| `scripts/ci/graph_cardinality_audit.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +119/-5 preserved |
| `scripts/ci/lint_baseline.txt` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +1/-1 preserved |
| `scripts/ci/narrow_guard_scan.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +1/-1 preserved |
| `scripts/ci/pass_count_check.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +1/-0 preserved |
| `scripts/ci/prompt_reliability.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +8/-22 preserved |
| `scripts/ci/systemd_unit_audit.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +157/-6 preserved |
| `scripts/ci/validate_skill_schema.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +57/-182 preserved |
| `scripts/cloud/audit_lemonade_recipes.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +31/-84 preserved |
| `scripts/datamesh_land_scanner.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +1/-1 preserved |
| `scripts/drivers/routine_flume_variate.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +22/-26 preserved |
| `scripts/drivers/routine_skill_geometry.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +23/-59 preserved |
| `scripts/e80_reflective_autoresearch.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +3/-3 preserved |
| `scripts/eval/held_out_fitness.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +16/-46 preserved |
| `scripts/experiments/watch_mellum2_gguf.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +3/-1 preserved |
| `scripts/maintenance/env_preflight.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +25/-72 preserved |
| `scripts/ops/consult_cloud_defect_class.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +4/-2 preserved |
| `scripts/ops/dogfood_hybrid_silicon_cloud.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +199/-134 preserved |
| `scripts/ops/lemonade_paper_triage.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +4/-2 preserved |
| `scripts/ops/lemonade_physics_of_agents.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +4/-2 preserved |
| `scripts/ops/lemonade_quipu_research.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +4/-2 preserved |
| `scripts/ops/merge_train.sh` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +0/-0 preserved |
| `scripts/ops/multiperspective_diff_review.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +38/-3 preserved |
| `scripts/preflight.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +2/-7 preserved |
| `scripts/producer_consumer_audit.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +36/-45 preserved |
| `scripts/quick_preflight.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +7/-17 preserved |
| `scripts/register_lemonade_models.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +2/-12 preserved |
| `scripts/report_untested_modules.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +19/-19 preserved |
| `scripts/research/distill_tutorials.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +8/-12 preserved |
| `scripts/review_durability_scripts.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +3/-1 preserved |
| `scripts/swarm_harness.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +5/-3 preserved |
| `scripts/sync_lemonade_kv_quant.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | ruff-format campaign on main; branch hunk +3/-1 preserved |
| `uv.lock` | MAIN | regenerate with uv lock before landing |


## Post-merge integration (2026-08-27)
- `swarm/oo_agents.py`: `reliability.circuit_breaker` was retired on main (246249f6); now uses `reliability.circuit_protected`.
- Tests where main's functions were silently dropped by a clean auto-merge (found by a def-name scan): `tests/physics/test_riemannian_glide.py` (9), `tests/integrations/test_telegram_local_inference.py` (1), `tests/unit/test_unified_hybrid_router.py` (5) — union-merged (main base + branch-only tests).
- Registry: 5 entries the branch registered for AMD plugin skills with no in-repo .md removed (local-ai-use, local-ai-app-integration, magpie-kernel-evaluator, serving-llms-on-epyc, tracelens-analysis-orchestrator).
- Local adversarial review (Qwen3.6-35B judge / Gemma-4-E4B refuter): 2 CONFIRMED — the `verifier=` constructor-kwarg claim was REFUTED by grep (no caller passes it); the resolution-row contradiction was real and is fixed above.
- Frontier council (glm-5.2 / deepseek-v4-pro / qwen3.5:397b, 2026-08-27 00:23): 2 BLOCKERs were artefacts of a stale FILE D (pre-fix ratchet log; unit failures without the main baseline) — refuted by re-running the gate (475 < 478) and the baseline (same 5 fail on main). Confirmed and fixed: router row mislabelled its base; test_registry row was a copy-paste. Confirmed by construction (follow-up, not breakage): duplicate routing tables (_TIER*_PINS vs TIER_*_ROSTER) and two proof classes (ZKFVProof / ZKProof) coexist; telegram `_classify_delegation_intent` is appended but no longer called from `_handle_chat` (branch feature dormant — wiring TODO). Refuted by grep: positional UnifiedHybridRouter callers (none exist).
