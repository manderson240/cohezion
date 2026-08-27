# Merge resolution: origin/main -> worktree-virtual-soaring-shamir (2026-08-26)

Policy: main = prior-revision oracle for content conflicts and safe add/add files; HEAD kept only where
branch-only code imports HEAD-only symbols (depcheck). Every side not taken is preserved under docs/reconcile/.

| file | resolution | why |
|---|---|---|
| `src/cohezion/agi/autoharness_policy.py` | HEAD (main preserved in docs/reconcile/vss-main-versions) | ActionPolicyResult used by 4 branch modules; main's VerificationResult preserved — MERGE-REQUIRED follow-up if main consumers exist |
| `src/cohezion/agi/zkfv_compiler.py` | HEAD (main preserved in docs/reconcile/vss-main-versions) | ZKProof/PlonkConstraintGate used by 7 branch modules; main's ZKFVProof preserved — MERGE-REQUIRED follow-up |
| `src/cohezion/inference/unified_hybrid_router.py` | HEAD (main preserved in docs/reconcile/vss-main-versions) | TaskClass used by 12 branch scripts; main's RoutingResult/TIER_* preserved — MERGE-REQUIRED follow-up |
| `tests/unit/test_unified_hybrid_router.py` | HEAD (main preserved in docs/reconcile/vss-main-versions) | tests HEAD's router |
| `src/cohezion/agi/__init__.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/agi/recursive_learning.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/core/cross_session_event_bridge.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/inference/delegation_logger.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/inference/prewarm_harness.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/physics/electric_dipole.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
| `src/cohezion/physics/poincare_manifold.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | depcheck: no branch consumer needs HEAD-only symbols; main is oracle (HEAD improvements -> follow-up) |
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
| `src/cohezion/core/event_bus.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/core/persistence/surreal_client.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/data_mesh/event_consumer.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/data_mesh/land_runner.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/inference/image_tier.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/inference/model_card_defaults.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/inference/tri_compute_orchestrator.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `src/cohezion/learning/shadow_scripter.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
| `tests/inference/test_registry.py` | MAIN (HEAD preserved in docs/reconcile/vss-head-versions) | content conflict; main keeps drain timeout/residency/guards; HEAD's genuine adds (surreal 3.0 syntax, land_runner verdict parser, 5 model cards, lifecycle events) -> follow-up from preserved copy |
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
