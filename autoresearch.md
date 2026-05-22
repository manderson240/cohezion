# Autoresearch: Skill Context Density Optimization

## Objective
Reduce per-turn Claude Code context overhead from skill descriptions while preserving
compound engineering routing quality. Experiments vary which skills get `name-only` or
`user-invocable-only` overrides, measure token savings, and validate no routing loss.

## Metrics
- **Primary**: tokens_saved_per_turn (integer, higher is better)
- **Secondary**: routing_coverage_score (fraction of CORE_ROUTING skills at full context)
- **Guard**: compound_skills_preserved (autoresearch + cohezion-dynamic-modularity must stay)

## Compound Cycle Baseline (exp_I, 2026-05-08)
- Coherence: 0.760 | phi_score: 0.630 | compound_score: 0.750
- All 7 phases pass (dry-run, mocked services)
- Status: healthy baseline

## Results Summary (2026-05-08 session)

| Experiment | Type | Tokens Saved | Status |
|---|---|---|---|
| exp_A: 13 situational skills → name-only | skillOverrides | 13,160t | WIN |
| exp_B: 9 reference skills → user-invocable-only | skillOverrides | 3,539t | WIN |
| exp_C: kaggle → name-only | skillOverrides | 2,892t | WIN |
| exp_D: polish-campaign + dynamic-template → name-only | skillOverrides | 6,602t | WIN |
| exp_E: claude-code-token-optimization → name-only | skillOverrides | 1,129t | WIN |
| exp_F: multi-agent-isolated-worktree-pattern → name-only | skillOverrides | 1,286t | WIN |
| exp_H: autoCompactPrompt + compound state | settings | 0t (state preserved) | WIN |
| exp_I: compound cycle baseline | measurement | — | WIN (baseline) |
| exp_J: rules files overlap audit | analysis | 0t (user review needed) | INFO |

**Total tokens saved: ~130,471t/turn (90% skill description reduction)**

## Current State (2026-05-08)
- Skills: 65/73 overridden. 8 at full context (3 protected + 5 core utility)
- Full-context skills: autoresearch, autoresearch-team, cohezion-dynamic-modularity,
  claude-code-agent-teams, find-skills, autoharness-skill, autoharness-init, autoharness-update
- Estimated per-turn skill tokens: ~14,841t (was ~145,312t)

## Frontier (requires user decision or external unblock)
1. **Rules files** (~14,608t): 15 files, high keyword overlap with CLAUDE.md.
   Keyword overlap alone isn't sufficient — need human review to identify true redundancy.
   Top candidates: anthropic-intel-scan.md (1,581t), workflow-enforcement.md (1,518t),
   cz-cli.md (775t), context-continuation.md (758t)
2. **NPU activation (3rd node)**: Blocked on Qwen3-0.6B-FLM model download.
   Current: 2/3 nodes at 1.75 lift. Target: 1.80+ with 3/3.
3. **Real compound performance**: Dry-run baseline is healthy but uses mocked services.
   True compound lift measurement needs Lemonade real runs (not blocked, just OOM caution).

## Constraints
- Never override: autoresearch, autoresearch-team, cohezion-dynamic-modularity
- Never remove existing overrides (additive only)
- OOM-safe: no large model loading in experiments
- Winner = highest token savings with routing_coverage ≥ 0.85

## Round 3: NPU Activation + Compound Lift (2026-05-10)

| Experiment | Type | Result | Key Metric |
|---|---|---|---|
| exp_K_npu_activation | NPU startup | WIN | 3/3 nodes live, 393ms TTFT, 42 TPS |
| exp_L_triple_node_lift_v2 | Compound lift measurement | WIN | **6.354x lift** vs GPU-only |

### Key Finding: Thinking Model vs NPU Routing

Gemma-4-E4B (GPU, thinking mode) uses **364–500 tokens** for 1-2 word answers.
llama3.2-1b-FLM (NPU) uses **7–31 tokens** for the same tasks.

Routing short-answer tasks (classification, routing, simple QA) to NPU:
- 3.075x token efficiency
- 13.1x latency improvement
- 60% of compound loop tasks are NPU-suitable

## Round 4: Task Classifier + Tests + Coverage (2026-05-11)

| Experiment | Type | Result | Key Metric |
|---|---|---|---|
| exp_O_task_classifier | New module | WIN | 28µs avg, 8-task 100% accuracy |
| exp_P_dogfood_classifier | Integration test | WIN | 4/4 live API tasks complete |
| exp_Q_max_tokens_600 | Config fix | WIN | Silences GPU truncation |
| exp_R_model_card_harness | New module | WIN | Routes code → Granite coding model |
| exp_S_harness_init_name_only | Skill override | SKIP | routing_coverage=0.667 < 0.85 gate |
| exp_T_unit_tests | Test coverage | WIN | 63 tests, task_classifier + model_card_harness |
| exp_U_compound_loop_health | Health check | WIN | 7/7 phases pass post-session |
| exp_V_rules_overlap_quantify | Audit | INFO | 2 candidates (python-rules, memory) for human review |
| exp_W_orchestrator_predispatch_tests | Test coverage | WIN | 4 pre_dispatch integration tests |
| exp_X_triune_tests_fix | Test fix + coverage | WIN | Fixed stale NPU model assertion, N2 invariant test |
| exp_Y_100pct_coverage | Test coverage | WIN | 100% on both new modules |
| exp_Z_classifier_benchmark | Performance | WIN | 1–88µs range, all < 500µs budget |

### Key Findings: Classifier Performance

```
Pattern match         Overhead
──────────────────────────────
GPU (code gen)        ~1µs   (early exit on first match)
NPU categorical       ~5µs
NPU short answer      ~7µs
Long prompt           ~88µs  (full scan before length fallback)
Design budget         500µs  ← all well below
```

### Current State (2026-05-11, Round 5 — extended loop)

- **Experiments:** 41 total, 37 winners (90.2% win rate)
- **Tests:** 195 inference tests passing (was ~67 pre-session, +128 added)
- **Coverage:** 100% on task_classifier.py + model_card_harness.py; 97% on orchestrator.py
- **Branch:** `worktree-humming-coalescing-rose` @ 2814624f0 (PR #166 open)
- **Compound lift:** 6.354x (3-node vs GPU-only, unchanged from baseline)
- **5.10x token efficiency** on 13 compound loop prompts (exp_LL)
- **Harness:** 12 invariants (was 10), CL2+CL3 added
- **Bug fixes committed:**
  - Classifier: false GPU escalations for "import"/"class" in prose (exp_DD)
  - Orchestrator: tier1 gate not overridden on GPU routing (exp_FF, verified exp_NN)
  - Triune tests: stale qwen3.5-4b-FLM assertion (exp_X)
  - Type safety: _TYPE_CONFIG narrowed to Literal (exp_CC)
- **New classifier patterns:** code-context context guard, what-is/describe, code gen adjective (exp_DD, exp_HH)
- **New test files:** test_gaia_adapter.py (16 tests), test_task_classifier.py (41), test_model_card_harness.py (31), test_orchestrator.py extended (+12 tests)
- **Runtime finding:** NPU port 13306 now running DeepSeek-Qwen3-8B instead of llama3.2-1b-FLM
- **P0 bug fixed:** asyncio.Coroutine → collections.abc.Coroutine (Python 3.11 compat, exp_OO)
- **Final test count:** 205 inference tests passing (was ~67 pre-session, +138 added)

### Updated Frontier

Skill density and compound routing optimizations are **converged**. The routing_coverage gate
prevents further core skill overrides. Remaining opportunities require human decisions:

1. **Rules files** (~15,552t): 2 high-overlap candidates (python-rules.md 61%, memory.md 61%)
   Need human review to confirm redundancy vs CLAUDE.md before any trimming.
2. **Real session routing accuracy**: Task classifier tested on 8 synthetic tasks.
   Need to extract real compound loop task prompts to measure production accuracy.

## Round 7: HIHO Gate Training — Corpus Optimization (2026-05-22)

| Experiment | Type | Result | Key Metric |
|---|---|---|---|
| exp_PPPP2 | Weighted pool sampling | **WIN** | 65% regression rescue; NL within noise of baseline |
| exp_QQQQ2 | Weight tuning sweep (0.25, 0.33) | FAIL | Rounding cliff — code_mult < 5 under-suppresses |
| exp_RRRR2 | seq_len sweep (128/192/256) | FAIL | Longer seq hurts NL, weakens P5 gate |
| exp_SSSS2 | d_model=512 at 320 steps | FAIL | Underfits at 320 steps; P5 improves but NL +32% |
| exp_TTTT2 | 40 distinct snippets + weight=0.5 | FAIL | Domain relevance > diversity; general Python hurts |

### Key Findings: Code Corpus Limits

- **Weighted sampling mechanism validated** (exp_PPPP2): weight=0.5 with n_code=40 achieves ~7.3% effective code fraction in batches, within noise of 20-snippet baseline. Infrastructure now supports `code_sample_weight` param.
- **Domain relevance > diversity**: New Python snippets (async, pathlib, pydantic) WORSE than duplicated ML training snippets. Byte-level model relies on byte n-gram overlap with domain text. Future code additions must come from cohesion ML/training files.
- **Architecture ceiling**: seq_len=128 and d_model=256 are both confirmed optimal. No further gains from scaling either dimension with current dataset.
- **Weight=0.5 is optimal for n_code=40**: lower weights hit rounding cliff (effective fraction drops below 7%).

### Current State (2026-05-22, Round 7)
- **v5 gate remains optimal**: 320+SGDR+smart_seed+lr=5e-4+20 domain-specific snippets → NL=15.43
- **New infrastructure**: `n_code` and `code_sample_weight` params in `from_autoresearch()` and `build_balanced_training_dataset()`
- **_CODE_EXAMPLES expanded**: 40 entries (20 original ML + 20 new general Python — default n_code=20 uses only original 20)
- **Autoresearch commits**: 3 Anthropic API cost-saving commits cherry-picked to main (ceabbb325..de0d5d0ac)

### Updated Frontier
1. **Domain-relevant code expansion**: Add 20 more snippets from `src/cohezion/inference/*.py` or `src/cohezion/compound/*.py` — should match byte statistics of domain text better than general Python
2. **Sycophancy v5 calibration** (exp_UUUU2, running): Docstring marks v3 threshold as uncalibrated for v5 — measure PPL separation between substantive and sycophantic text
3. **eval_text diversity for smart_seed**: Currently uses 1 eval phrase — 3-phrase average might select a more generalizable seed

## Round 6: 100% Module Coverage (2026-05-11)

| Experiment | Type | Result | Key Metric |
|---|---|---|---|
| exp_XX_pr167_merged | Merge | WIN | PR #167 landed |
| exp_YY_context_engineering_tests | Tests | WIN | 21 regression tests |
| exp_ZZ_anti_sycophancy_tests | Tests | WIN | 17 tests + self-audit |
| exp_AAA_hardware_telemetry_tests | Tests | WIN | 11 tests, FLM verified |
| exp_BBB_autoharness_ce_tests | Tests | WIN | 8 tests, session validation |
| exp_CCC_orchestrator_autoharness_tests | Tests | WIN | 15 tests |
| exp_DDD_tri_compute_100pct_coverage | Tests | **WIN** | **100% coverage!** |

### MILESTONE: 100% Inference Module Coverage
- Started: ~67 tests, 49% module coverage
- Ended: 295 tests, 100% module coverage
- Modules: 10 → 19 with test files (+9 new)
- Tests added: +228

### Final Session State (2026-05-11)
- **Experiments:** 57 total, 53 winners (93.0% win rate)
- **Tests:** 295 inference tests passing
- **Coverage:** 100% of 19 inference modules
- **Harness:** 12 invariants (C1-C4, N1-N2, A1-A2, CL1-CL3, K2)
- **PRs:** #166 ✓, #167 ✓, #169 open (CI pending)
- **Compound lift:** 6.354x maintained
- **Token efficiency:** 5.10x on compound loop prompts
