---
paths:
  - "src/**"
  - "tests/**"
  - "scripts/**"
  - "cloud-vault-mcp/**"
  - ".claude/**"
  - ".github/**"
  - "docs/**"
  - "CLAUDE.md"
  - "pyproject.toml"
  - "uv.lock"
  - "Makefile"
  - ".pre-commit-config.yaml"
---

# AutoHarness Rules — Cohezion

Generated: 2026-05-02. Updated via `/autoharness-update`. Scoped by `paths:` on 2026-09-18
(`/doctor` + Ollama Cloud council 3/3, re-applying the 2026-09-01 council's set plus `docs/**`
and root `CLAUDE.md`): this ledger loads when working under code, tests, scripts, the MCP
server, rules, CI config, docs, or build files — everything its invariants govern — so pure
research/vault/Kaggle-labs sessions don't pay ~26k tokens for it. Split 2026-09-18 (both
councils' follow-on): this file is the short core; the full invariant ledger is
`docs/harness-invariants-catalogue.md` (index below).

> Session-by-session build narratives (GAIA-SDK 4-lens review, bug hunt, House-in-Order keystone
> fixes — all 2026-06-30) were moved verbatim to `docs/autoharness-history-2026-06.md` on 2026-07-17
> to cut ~3k always-loaded tokens. Active invariants remain below.

## Adversarial-Review Corrections (2026-06-29) — supersedes earlier routing invariants

A 3-reviewer adversarial review + 5 SOTA research agents found the prior session's GIC routing code
was green only because tests exercised the easy paths. Corrections (all committed, tested):
- **H1/H2 (supersedes ME1 telemetry assumption):** `orchestrator.run` returns `escalation_count =
  idx - start_tier` (RELATIVE escalations), not absolute idx. `_engine_for(entry + relative)` = the
  absolute final tier; `predict_tier`'s `escalation_count==0` clean-success test stays valid when
  entering above NPU. Cascade credit-assignment convention (final-tier identity + relative count).
- **H3 (SUPERSEDES GIC-CAL1):** the `_MIN_TIER_FREQUENCY=0.34` guard is REPLACED by a **Wilson lower
  confidence bound** — `predict_tier` returns the cheapest tier whose `_wilson_lcb(clean, n) >=
  _LCB_ADEQUATE (0.35)`; dominant-by-(count, mean-quality) fallback. Fixes BOTH lucky-cheap
  miscalibration AND the balanced-3-way default-to-worst bug. Validated across 400 seeds (mean 98.9%,
  91% perfect, max drift 12%). `test_wilson_lcb_*` + `test_balanced_3way_*`. The GIC-CAL1 entry below
  is HISTORICAL — `_MIN_TIER_FREQUENCY` no longer exists.
- **H4 (corrects RS1):** `_resolve_tier` fuses by MAX-CAPABILITY (health may only escalate a hard
  task, never cheapen it) and a JEPA REROUTE escalates ONE step toward capability (not cheaper). The
  fused value now DRIVES cascade entry (`_call_execute_fn(execute_fn, guidance, _recommended or ...)`)
  — previously it was metric-only/dead. RS1's "cheaper-of-two + REROUTE-downgrades" is REVERSED.
- **M3:** `build_live_jepa_gate` probes `lemonade_available(npu_port=13305)` (was default :13306,
  offline per N1 → the JEPA gate silently never ran). **M5:** `_safe_ident` validates skill_name
  before SurrealQL interpolation (injection guard).
- **M1 (FIXED 2026-06-29):** the FAPO R3 regression gate is now LIVE. `_regression_run_fn` had TWO
  bugs — never wired AND added to the wrong class (`EnvironmentResponsePredictor`, not `SkillRefiner`),
  so `refine()` would AttributeError if reached (dormancy masked it). Fix: moved onto `SkillRefiner`;
  `SkillRefinerFactory.create` wires a local-inference runner; `regression_check` is fail-CLOSED when
  fixtures exist but eval can't complete (infra errors still fail-open). Verified:
  `SkillRefinerFactory.create()._regression_run_fn is not None`. No-op until golden fixtures populated
  (bootstrap from JourneyTracker traces = follow-on).
- **OPEN (documented, not yet fixed):** M2 — CR1 `_recompute_tier_at_compaction` has no caller (wire to
  `vector_pruning.should_compact()`). H5 status (LANDED, see tests/compound/test_sandboxed_exec.py, tests/security/test_h5_exec_gate.py, tests/compound/test_exec_gate_sites.py):
  out-of-process `sandboxed_exec.run_untrusted` is wired at agi_reasoning / aimo_reasoning / symbolic_executor / llm_fallback / arc.local_qwen_ast_proposer (bwrap `--unshare-all` when available; else rlimit floor NOFILE=3/NPROC=0/FSIZE=0/AS/CPU — it RUNS, does not refuse, when bwrap is absent); in-process `safe_exec` gate retained as defense in depth with `gate_refusal` diagnostics; CI gate `scripts/ci/unrestricted_exec_scan.py`.
  Rlimit-only floor is availability + speed bump, NOT an FS boundary (path-based os.mkdir/rename/unlink work); bwrap is. Post-exec results are UNTRUSTED (forgeable) — consumers validate; `SandboxResult.stage` marks pre-/post-exec.
  NOT behind the out-of-process boundary today (deliberate/pending): `agent/unified_harness._python_tool` + Kaggle `arc_prize{,_2}/submission.py` (arbitrary-Python contract; branch agent-1789419784 pending user policy);
  `agents/factory` + `testing/mutation_tester` (codegen; per a80da6714 first-party stubs — mutation_tester's input provenance not re-verified), `inference/dynamic_model_evaluator.py:247` (in-process; a80da6714 records it as stricter: no `__import__` at all).

## Verification Commands

| Check | Command | Expected |
|---|---|---|
| Fast tests | `uv run pytest tests/unit --import-mode=append --tb=short -q -p no:warnings` | Exit 0 |
| Skill validate | `uv run python scripts/ci/validate_skills.py` | Exit 0 |
| Registry validate | `uv run python scripts/ci/validate_registry.py` | Exit 0 |
| Phantom-attr self-test | `uv run python scripts/ci/phantom_attr_scan.py --self-test` | Exit 0 |
| Phantom-attr scan | `uv run python scripts/ci/phantom_attr_scan.py` | Exit 0 |

## PA1: phantom-attribute scan is RUN by both gates (CONSUMPTION, 2026-08-26)

- `scripts/ci/phantom_attr_scan.py` flags `getattr(x, "<literal>", default)` where the target
  class defines no such attribute. Third sibling of `dormancy_scan` ("has a consumer?") and
  `doc_code_consistency` ("do the docs tell the truth?"): **"does the attribute exist?"**
- ORIGIN: `getattr(result, "error", "")` in `actioner/engine.py` read a field `ExecutionResult`
  does not have (9 constructions in `compound/executor.py`, **0** pass `error=`). Every failure
  logged an empty reason, so a fully-blocked compound pipeline was indistinguishable from a slow
  one for weeks. **mypy cannot catch this** — `getattr` with a literal + default is deliberate
  dynamism whose contract IS to succeed silently.
- **CONSUMPTION, not declaration**: the invariant is not "the scanner exists", it is
  "`automerge_guard.sh` AND `.github/workflows/ci.yml` both invoke it, with `--self-test` first".
  `tests/scripts/test_phantom_attr_scan.py::test_t3_scanner_is_wired_into_the_gate` FAILS if
  either gate stops calling it — neutralizing the consumer turns the test red.
- **T2 discriminating**: `--self-test` plants the historical defect and requires RED, then GREEN.
  Additionally validated against the REAL pre-fix tree from git history (`dee080d0c~1`): fires on
  `engine.py:260`, silent on the fix. The prior revision is an unbiased oracle — nobody authored
  it to test this scanner, so it cannot share the author's blind spot.
- **Deliberately out of scope**: dynamic `getattr(x, name, ...)` is never flagged (unresolvable
  statically; flagging it would be noise). Registry is curated for precision over recall — a
  scanner that cries wolf trains people to ignore it.
- **Verification**: `uv run pytest tests/scripts/test_phantom_attr_scan.py -q` → 13 passed

## Valid Code Changes (is_legal_change)

1. **All Python code must be valid Python 3.13** — use `compile()` or import
2. **Skill files (`src/cohezion/skills/*.md`) must produce valid Python stubs** — run validate_skills.py
3. **Registry entries must reference existing skill files** — no orphaned entries
4. **Generated class names must be valid Python identifiers** — `_skill_name_to_class()` strips dashes/spaces
5. **No em-dash (U+2014) in skill description fields** — replaced with `--`
6. **Import-time errors must not break fast tests** — use lazy imports for heavy deps
7. **Conventional commits required** — `feat:`, `fix:`, `chore:`, etc.

## Naming Conventions

- **Packages:** lowercase, one word (prefer `datamesh` over `data-mesh`)
- **Modules:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/methods:** `snake_case`
- **Skill files:** `UPPER_SNAKE_PRIME.md`
- **Branches:** `type/description` (e.g. `fix/ci-green-main`)
- **PR titles:** conventional commit format `type(scope): description`

## Forbidden Patterns

- `sys.path.insert(0, "/home/...")` — use relative imports or `PYTHONPATH`
- Hardcoded paths with `/home/mike-anderson/` — use `Path(__file__).parent`
- `git clean -fdx` — the `-x` flag deletes gitignored state
- `gh pr merge --admin` except in confirmed emergencies
- Em-dashes (—) in YAML front matter or code-generating templates

## Project-Specific Notes

- Python **>=3.13** required (`pyproject requires-python = ">=3.13"`; venv runs 3.13.11). torch+ROCm (`torch==2.8.0+rocm6.3`) caps Python support at 3.13 — no `cp314` wheels exist for any torch+ROCm build yet, so **3.14 is NOT usable** until AMD/PyTorch ship a cp314 ROCm wheel (or you build from source). (Corrected 2026-07-23: the prior "3.11 required" note was stale — 3.11/3.12 are now below the floor.)
- `uv sync --frozen` for reproducible builds
- Self-hosted runner `t30-runner` is bottlenecked — prefer ubuntu-latest for CI
- Pre-commit hooks: trailing-whitespace, end-of-file-fixer, no-hardcoded-home-paths
- Autogenerated test scaffold commits are DISABLED (was generating 998 files)
- The authoritative skill registry is `src/cohezion/registry/skill_registry.json`
  (NOT the one in `src/cohezion/skills/skill_registry.json`)

## Invariant catalogue (on disk)

Full invariant ledger: `docs/harness-invariants-catalogue.md` (split out of this file 2026-09-18; verbatim, original order).
Read the catalogue section before touching the named module; every entry there pairs an invariant with its verification command.
The catalogue is scanned by `scripts/ci/doc_code_consistency.py` exactly like this file.

| Section | Catalogue anchor | Invariant IDs |
|---|---|---|
| FAPO Failure Attribution Invariants (2026-06-23) | `docs/harness-invariants-catalogue.md#fapo-failure-attribution-invariants-2026-06-23` | FA1, FA2, FA3 |
| Loopception Invariants (G15/G16/G18, 2026-06-25) | `docs/harness-invariants-catalogue.md#loopception-invariants-g15g16g18-2026-06-25` | LC1, LC2, LC3 |
| MetricBaseline Invariants | `docs/harness-invariants-catalogue.md#metricbaseline-invariants` | MB1, LT1, FD1 |
| SkillRefiner Invariants | `docs/harness-invariants-catalogue.md#skillrefiner-invariants` | JI1, JG1, JG2, JG3, RS1, O9, ME1, GIC-CAL1, CR1, JW1, SG1, AD1, AD2, AD3, CB14, CB16 |
| EnvironmentResponsePredictor Invariants (#117, 2026-06-27) | `docs/harness-invariants-catalogue.md#environmentresponsepredictor-invariants-117-2026-06-27` | ERP1, ERP2, ERP3, ERP4 |
| RL Process Reward Invariants (#118, 2026-06-27) | `docs/harness-invariants-catalogue.md#rl-process-reward-invariants-118-2026-06-27` | RL1, RL2, RL3, RL4 |
| DifficultyEstimator Invariants (#93, 2026-06-27) | `docs/harness-invariants-catalogue.md#difficultyestimator-invariants-93-2026-06-27` | GIC1, GIC2, GIC3, GIC_NEW_4 |
| Skill Proximity Invariants (#102, 2026-06-27) | `docs/harness-invariants-catalogue.md#skill-proximity-invariants-102-2026-06-27` | SP1, SP2, SP3, SP4 |
| Physics Calibration Notes (#100, added 2026-06-27) | `docs/harness-invariants-catalogue.md#physics-calibration-notes-100-added-2026-06-27` | (prose notes, no ID headings) |
| Wiring Completeness Invariants (W1–W5, 2026-06-27) | `docs/harness-invariants-catalogue.md#wiring-completeness-invariants-w1w5-2026-06-27` | W1, W2, W3, W4, W5, W6 |
| RiVER Reward Normalization Invariants (#140/#141, 2026-06-27) | `docs/harness-invariants-catalogue.md#river-reward-normalization-invariants-140141-2026-06-27` | RV1, RV2 |
| TrajectoryPoint Action Field Invariants (JI1, 2026-06-27) | `docs/harness-invariants-catalogue.md#trajectorypoint-action-field-invariants-ji1-2026-06-27` | JI1 |
| MoE Skill Router Invariants (MR1–MR4, #83, 2026-06-28) | `docs/harness-invariants-catalogue.md#moe-skill-router-invariants-mr1mr4-83-2026-06-28` | MR1, MR2, MR3, MR4, MR6 |
| JepaGate Threshold Property Invariants (#156, 2026-06-28) | `docs/harness-invariants-catalogue.md#jepagate-threshold-property-invariants-156-2026-06-28` | JTP1 |
| RQGM Epoch-Boundary Utility Invariants (#155, 2026-06-28) | `docs/harness-invariants-catalogue.md#rqgm-epoch-boundary-utility-invariants-155-2026-06-28` | RQGM1, RQGM2 |
| SkillRefiner Durable Loop-State Spine (#154, 2026-06-28) | `docs/harness-invariants-catalogue.md#skillrefiner-durable-loop-state-spine-154-2026-06-28` | SRS1, SRS2, SRS3 |
| RiemannianGlideTrajectory Invariants | `docs/harness-invariants-catalogue.md#riemannianglidetrajectory-invariants` | RG1 |
| AIR Model Invariants (task_classifier output_intent, #89, 2026-06-28) | `docs/harness-invariants-catalogue.md#air-model-invariants-task_classifier-output_intent-89-2026-06-28` | AIR1, AIR2, AIR3 |
| Cross-Model Agreement Invariants (AG1–AG4, 2026-07-30) | `docs/harness-invariants-catalogue.md#cross-model-agreement-invariants-ag1ag4-2026-07-30` | AG1, AG2, AG3, AG4 |
| Model Residency Invariants (RS1–RS4, 2026-08-03) | `docs/harness-invariants-catalogue.md#model-residency-invariants-rs1rs4-2026-08-03` | RS1, RS2, RS3, RS4, RS7, RS8 |
| Stealthskater Bridge Invariants (2026-05-16) | `docs/harness-invariants-catalogue.md#stealthskater-bridge-invariants-2026-05-16` | S1, S2, S3, S4, S5, S6, S7, S8, S9 |
| Local Silicon Invariants (2026-05-20) | `docs/harness-invariants-catalogue.md#local-silicon-invariants-2026-05-20` | I1, I2, I3, I6, I7, I4 |
| Universal HIHO Invariants (2026-05-20) — Phase 18 | `docs/harness-invariants-catalogue.md#universal-hiho-invariants-2026-05-20--phase-18` | U1, I8, I9, I10 |
| Phase 19 Invariants (Cosmic Fire, Triune Self, R0Σ, Greek Parameters) (2026-05-20) | `docs/harness-invariants-catalogue.md#phase-19-invariants-cosmic-fire-triune-self-r0σ-greek-parameters-2026-05-20` | P1, P2, P3, P4, P5, P6 |
| HIHO-LM Invariants (2026-05-20) — Phase 20 | `docs/harness-invariants-catalogue.md#hiho-lm-invariants-2026-05-20--phase-20` | LM1, LM2, LM3, LM4, LM5, LM6, LM7 |
| Coherence Invariants (2026-07-31) | `docs/harness-invariants-catalogue.md#coherence-invariants-2026-07-31` | EB1, SCP2b, DOC-E5 |
| Adversarial Guardrail Ratchet Invariants (AG1–AG3, 2026-08-09) | `docs/harness-invariants-catalogue.md#adversarial-guardrail-ratchet-invariants-ag1ag3-2026-08-09` | AG1, AG4, AG5, AG2, AG3 |
| Git Hook Gate Invariants (GH1–GH3, 2026-10-22) | `docs/harness-invariants-catalogue.md#git-hook-gate-invariants-gh1gh3-2026-10-22` | GH1, GH2, GH3 |

## TieredOrchestrator Temperature Invariants

### Removed phantom invariants — TR1, MB1 (the 2026-08-14 entry), RTG1, RGA1/RGA2
Each described code that never existed. The class is now caught MECHANICALLY by
`scripts/ci/doc_code_consistency.py` (E6 cited-test check + W4 symbol check), a blocking
gate in `automerge_guard.sh` and CI; the full post-mortems were moved verbatim to
`docs/autoharness-history-2026-06.md` (2026-09-18). Two things survive here: TR1's
motivation is real as the model-card mechanism (`src/cohezion/inference/CLAUDE.md`
"TR (Triune Recipe) Invariants", `tests/inference/test_triune_orchestrator.py::
test_tr1_omni_orchestrator_tiers_use_model_card_temperature_not_zero`); and **before
trusting ANY "Verification" line in this file, grep the field in `src/` and the assertion
in `tests/`** — a command that runs green and proves nothing is the hardest false
verification to catch by reading. Do NOT re-add `_TIER_TEMPERATURE`, `rtg_floor`,
`curvature_coupling`, or a second MB1 without implementing them.

## Lessons Captured (2026-05-02)

- **Em-dash bug:** Skill names with `—` generated invalid Python class names
  in `_skill_name_to_class()`. Fix: sanitize non-alphanumeric chars before title-casing.
- **Registry split:** Two registry files existed; only `src/cohezion/registry/skill_registry.json`
  is authoritative. The skills dir copy is stale/dead.
- **Auto-test pollution:** `auto-generate-tests` CI job committed 998 scaffold files
  to main on every push. Disabled permanently.

## Harness Bash Unification Invariants (2026-06-03)

### H1: Every harness must be able to use Bash (deployment invariant)
- All three harnesses (Claude Code, Pi, Hermes) must be able to run shell
  commands via the deploy script. This is a deployment invariant, not a
  feature: any agent verifying the cohezion repo must be able to invoke
  `python3 .claude/rules/harness_check.py`.
- Captured retro: `docs/ops/learnings/RETRO-2026-06-03-harness-bash-unification.md`
- SurrealDB: `learnings:bash_unification_2026_06_03`

### H2: Claude Code Bash must be guarded by safe-env.sh
- `~/.config/cohezion/safe-env.sh` strips invalid PATH-like env vars
  (`LD_LIBRARY_PATH`, `PATH`, `PYTHONPATH`, `ROCM_PATH`, `HIP_PATH`,
  `CUDA_PATH`) before Claude Code spawns subprocesses. Prevents
  `bwrap: Can't create file at <PATH>` total Bash outage.
- Skill: `claude-code-bwrap-sandbox-missing-bind` (refined v1.1.0,
  2026-06-03; canonical copy in `~/.claude/skills/`, mirrored to
  `.claude/skills/`, `.pi/skills/`, `.agents/skills/`).
- **Verification**: `source ~/.config/cohezion/safe-env.sh && claude --print
  "bash -c 'cd /home/mike-anderson/dev/cohezion && python3
  .claude/rules/harness_check.py --fast'"` exits with the harness check
  output (not a bwrap error).

### H3: Deploy script must source safe-env.sh before launching claude
- `scripts/ci/deploy_harness_agents.sh` must `source
  ~/.config/cohezion/safe-env.sh` before `tmux new-session -d ...` for
  the harness-claude session. Without this, every Claude deploy silently
  fails with bwrap error and the agent reports "Bash blocked" instead of
  real findings.
- **Verification**: `grep "safe-env.sh" scripts/ci/deploy_harness_agents.sh`
  returns a non-empty result.

