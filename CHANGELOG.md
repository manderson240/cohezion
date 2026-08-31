# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Train-3 ports: event priority threading + real audit instruments (1.16.0)
- `src/cohezion/data_mesh/event_consumer.py`: threads the event `priority` (a live producer
  in `event_bridge.py` whose value was silently discarded) into filed work items, with
  signature-aware dispatch so legacy 3-arg `file_work_item_fn` injections keep working
  (the `executor._call_execute_fn` house pattern). Discriminating tests in
  `tests/data_mesh/test_event_consumer_land_ready.py` (priority=3 must land as 3; garbage
  coerces to default; legacy filer must not raise).
- `scripts/ci/graph_cardinality_audit.py` + `scripts/ci/systemd_unit_audit.py`: the CI-guard
  STUBS that printed unconditional success are replaced with the real instruments from the
  Train-3 branch (declared-but-empty relation tables; ExecStart targets that don't resolve).
  Both report-only. First live run of the graph audit found 12 declared-but-empty relation
  tables; the systemd audit's target class was independently confirmed by today's crash-log
  triage (stale `~/ods` units failing every minute — kanban `stale-ods-systemd-units`).
- `scripts/producer_consumer_audit.py`: lemonade_classify budget raised 180 tok/30s →
  1500 tok/300s (env-overridable) — the 5th recorded frugal-budget truncation defect.
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md`: L254 (Quadrature) annotated as
  FABRICATED CAPABILITY (UI-only, no backend — consumption-is-not-completion class);
  Session-104's duplicate L396/L397 renumbered 396b/397b. The 08-21 adjudication's
  "phantom L402-411" verdict is now stale — the vss reconcile landed their referent modules
  (`deep_cooking.py`, `speculative_engine.py`, `delegation_logger.py`), so those entries stay.

### Added — reconcile worktree-virtual-soaring-shamir into main (1.15.0)
- Landing-time merge notes (2026-08-31): merged post-1.14.0 main back in (7 conflicts). CI gate
  unions: the branch's phantom-attr scan AND main's gate self-test coverage both kept in
  `ci.yml`/`automerge_guard.sh`; `mycelium/registry.py` keeps the branch's proper L359 exception
  narrowing over main's still-wide tuple; router policy follows main (1.13.0 verified policy).
  `ruff_ratchet` baseline re-measured with provenance (483; the committed 475 carried no stamp —
  the ratchet itself flagged it as typed-not-measured). Mypy: the reconcile's new subsystems
  brought +93 errors over the 1727 baseline; fixed at landing rather than baselined (the ratchet
  refuses to move up). Residual debt burn-down is tracked on the agentic kanban
  (`mypy-debt-1727-baseline`, `ruff-debt-483-baseline`).
- Test↔src pairs re-matched where the reconcile split them: `model_card_defaults` gains the
  branch's gemma-3/deepseek-r1/nemotron/bonsai entries (nemotron WITHOUT the branch's
  invented `min_p` — its own discriminating test forbids it; ordering constraints preserved,
  main's `qwen3.6-moe` kept); `prewarm_harness` replaced with the branch's REAL probe
  (main's was `time.sleep(0.1)` + unconditional success — a fake; Train-3 adjudication
  applied); `load_safety` follows MAIN (empirically calibrated floor 16 / factor 1.7 over
  the branch's speculative 20/2.1 — src+test restored as a matched pair; the branch's
  unconsumed `compute_kv_cache_gb` stays on the branch ref). The new
  `model_sprint_orchestrator`'s 3 gate tests are xfail'd pending a pre_load_gate design
  decision (kanban `sprint-orchestrator-gate-divergence`).
- Lands the Kaggle/competition branch (286 commits, 2026-07-13 → 2026-08-26) merged onto main with
  85 conflicts resolved non-destructively: `main` is the prior-revision oracle for every content
  conflict and for `add/add` modules with no branch-only consumers; three modules keep the branch's
  implementation with main's `VerificationResult` / `ZKFVProof` / `RoutingResult`+`TIER_*` appended
  so main-side importers keep working. Every side not taken is preserved under `docs/reconcile/`.
  Resolution table: `docs/reconcile/2026-08-26-merge-resolution.md`.
- New subsystems: `competitions/` (arc, arc_prize, biohub_cell, pokemon_tcg, rsna_knee, swarms,
  world_models), `adapters/`, `evaluation/`, `evo/`, `infrastructure/`, `ops/`, `pipelines/`,
  `policies/`, `review/`, `training/`; Kaggle auto-submission + leaderboard-climb daemons.
- Hygiene: 4,769 tracked `.pyc` and raw LoRA weights untracked; `*.safetensors` now LFS.
- Deps: `marimo`, `peft`, `trl` declared; `uv.lock` regenerated.
- Follow-ups (preserved, not landed): branch versions of `surreal_client` (SurrealDB 3.0 syntax),
  `land_runner` (verdict-first parser), `prewarm_harness` (false pre-warm fix), `model_card_defaults`
  (5 new cards), `event_bus` (model lifecycle events) — see the resolution table's "why" column.

### Added — harvest landing: output-quality wiring, categorical routing, durable writes (1.14.0)
- Worktree-harvest merge train (8 branches from the 2026-08-30 agent cluster, landed via
  plumbing merges — real merge parents, no squash). Highlights beyond the mypy/pricing
  section below:
- `src/cohezion/compound/executor.py` + `executor_factory.py`: BOTH quality wirings landed
  and are complementary — `dqa_gate` publishes `quality_score` into the degradation fold
  (the DegradationDetector branch that could never fire), while `quality_evaluator`
  publishes `output_quality_*` telemetry; `SkillRefiner._extract_metrics` still derives its
  `quality_score` from `anomaly_score`, so the AQ6 scale guard holds. Discriminating probe:
  on the `make_executor` production path, `quality_score` now varies 1.0 vs 0.0 with output
  content (was a constant 0.5 below its own 0.6 floor).
- `src/cohezion/inference/quality_eval.py`: strict/weak uncertainty markers selected by
  NAME (`_STRONG_UNCERTAINTY_MARKERS`), not a `[:4]` positional slice — two independent
  agent fixes of the same defect unified on one naming scheme, both regression-test files
  kept.
- `src/cohezion/inference/task_classifier.py`: every yes/no instruction verb routes to the
  categorical gate.
- `src/cohezion/compound/autodqa.py` + `src/cohezion/inference/gemini_cli_tier.py`: async
  SurrealDB writes were built-and-discarded coroutines; now driven via `run_sync` (audit in
  `docs/audits/UNAWAITED_SURREAL_WRITES_2026-08-28.md`).
- `scripts/ci/verification_exec.py`: executes harness.md's inline `**Verification**:`
  commands and classifies failures (SYNTAX/PROSE/STALE_REF/ASSERT/TIMEOUT/EXTERNAL).
  Deliberately report-only until proven on real drift.

### Fixed — `verify_router.py --preflight-only` claimed more than it checked (1.13.1)
- With `--preflight-only` (no generation), the tool printed
  *"PASS: registered, every candidate present, downloaded, and answering coherently"* — while
  having probed no content at all. That is this tool committing the exact error it exists to
  catch: a verdict asserting more than was verified. Found by running the tool during an
  end-of-session sweep and reading its own output.
- Preflight now prints a distinct verdict naming what was skipped, and says plainly that a
  degenerate model passes every check above it.
- Also: `# noqa: S310` on the two localhost `urlopen` sites to match the convention in
  `scripts/ops/silicon_supervisor_daemon.py`, and dropped a dead `BLE001` directive that
  `RUF100` flagged (that rule is not enabled here).
- Re-confirmed discriminating after the edits: PASS on the current policy, FAIL on the previous
  one naming `qwen3.6-moe-35b-a3b-FLM`.

### Added — router policy on main + `verify_router.py` (1.13.0)
- `config/router/cohezion-router.json` was tracked on three feature branches and landed on
  none of them. Not gitignored — never landed. That is why finding it needed a human's memory:
  a `src/`-scoped grep concluded we did not use lemonade's built-in router at all.
  Config-as-data does not live in the source tree.
- `scripts/ops/verify_router.py` checks a `collection.router` policy **by content**: is it
  registered (an upgrade drops this silently), is every candidate in the catalog and downloaded,
  and does every candidate answer a known-answer probe with something that is not garbage.
- **Discriminating**: PASSES on the fixed policy, FAILS on the previous one naming
  `qwen3.6-moe-35b-a3b-FLM`. In that failing run the model's *preflight* line reads `[OK ]`
  while its *content* line reads `[DEGEN]` — a degenerate model returns HTTP 200 with a
  well-formed OpenAI envelope, so no structural check can see it.
- Policy repointed away from that model, which was the target of three rules including the
  `default-npu` catch-all (`min_chars: 0`), so most general traffic returned `////////`. Its
  GGUF siblings are healthy, so the fault is the FLM conversion, not the weights. Now:
  `default-npu`/`default_model` → `qwen3-4b-FLM`, `long-context` → `deepseek-r1-0528-8b-FLM`;
  removed from components and candidates. Unloading it also returned 24.3 GB of NPU residency
  (headroom 0 GB → 7.06 GB).
- Run after every lemonade upgrade: `python scripts/ops/verify_router.py`

### Fixed — a permanently dead census warned forever and never escalated (1.12.3)
- Making `router_unreachable` require the cheap `/api/v1/system-info` endpoint to fail (1.12.0)
  removed a real false alarm — `/health` and `/models` block 20s+ under load, so polling them
  paged on every busy fleet. But it left nothing that could escalate: with `/system-info` alive
  and the census endpoints permanently dead, the supervisor emitted one warning and then warned
  forever.
- `stall_events(consecutive_polls)` escalates on DURATION, the same measurement that motivated
  the original change (`/health` blocked on 2 of 3 probe rounds and answered on the third).
  Edge-triggered at both boundaries, silent between: poll 1 → `census_stalled` (warning),
  poll 10 → `census_stalled_persistent` (**critical**). A stall lasting hours pages twice.
- Threshold is in polls, not seconds — the diff layer has no clock. At the 30s default that is
  5 minutes.
- `tests/scripts/test_silicon_supervisor_daemon.py` (new) tests the COMPOSITION: it drives the
  real `cycle()` for 12 polls with the cheap endpoint alive and the census dead, and asserts the
  daemon actually threads the counter. Its discriminating partner asserts a 2-poll stall never
  escalates and resets the clock.

### Fixed — `uv sync` installed ~4.6 GB of CUDA libraries on an AMD-only box (1.12.2)
- `pyproject.toml`: added a `pytorch-cpu` index and mapped `torch` + `torchvision` to it. The
  previous comment asserted "torch and torchvision resolve from PyPI (CPU wheels) by default for
  CI" — false. PyPI's default Linux torch wheel is the **CUDA** build; CPU wheels come from
  `download.pytorch.org/whl/cpu`.
- torch stays at **2.13.0** — the CPU index carries the same version the lock already resolved,
  so this removes the CUDA payload without a version change.
- Measured with CI's exact command in a clean clone of main: `uv sync --frozen` rc=0, disk
  consumed **1093 MB (was ~4600 MB)**, zero CUDA libraries in the built venv,
  `torch 2.13.0+cpu` with `cuda.is_available()=False`, CUDA packages in `uv.lock` **6 → 0**,
  `tests/unit` **2122 passed / 0 failed**.
- This cost was paid on every self-hosted CI run and every new worktree. On 2026-08-30 it took
  the pool to 0 bytes and the filesystem read-only; a `git push` to this repo is a multi-GB
  local write.
- Regression origin: commit `32c242386` removed a working `torch==2.8.0+rocm6.3` pin and the
  index mappings as collateral in a CI-alignment PR. The ROCm pin is deliberately NOT restored —
  CI wants CPU wheels, and local AMD dev installs ROCm torch explicitly, which overrides.

### Fixed — store guard stayed silent on the first reading after a blind interval (1.12.1)
- `inference/silicon_supervisor.py`: `critical -> blind -> blind -> STILL critical` emitted
  `['store_critical', 'store_unmeasured']` and then **nothing** on the return to measured, which
  an operator cannot distinguish from the store having recovered. The first measured reading
  after a blind gap now always re-announces a non-ok level.
- The code comment justifying the old silence claimed *"resumption is directly observable because
  capacity events start flowing again"*. That is false in exactly this sequence — the level is
  unchanged, so no capacity event fires. Silence is only safe when the reader's picture is
  continuous, and a blind gap breaks continuity.
- Same defect CLASS as the stranded-incident bug fixed in 1.12.0: reasoning about state
  TRANSITIONS while the operator reasons about INCIDENTS. That fix addressed the reported
  instance (`critical -> blind -> ok`); this one addresses the sibling instance. Found by an
  adversarial review lane and confirmed by executing the sequence, not by argument.
- A healthy store after a blind gap is still not news — re-announcing "everything is fine" on
  every recovery from blindness is the flooding the function exists to prevent. Edge-triggering
  is unchanged wherever the picture is continuous (`was_blind` False).
- `store_low` after `store_critical` is now documented as LEVEL semantics, not a paired
  incident: the level dropped to warning, `store_low` supersedes, and `store_recovered` means
  exactly one thing — the level reached none. Stated explicitly and pinned by a test because a
  reviewer read the stream as paired open/close events and concluded the critical leaks forever;
  a downstream consumer that pairs them WOULD leak, so any such consumer must key on the latest
  level.
- `tests/inference/test_silicon_supervisor.py`: the test that asserted the old silence was
  correct is replaced. It had frozen the bug in place, exactly as the 1.12.0 test did.

### Fixed — dark mypy gate, stale Anthropic pricing, phantom model id (1.14.0)
- `pyproject.toml` + `scripts/ci/mypy_ratchet.py`: the CI `typecheck` job has run `mypy` for
  months while checking **nothing**, in three independent ways. `python_version = "3.11"` vs a
  3.13 project floor made numpy's 3.12+ `type` stubs abort the run *before any project file was
  read*; two skill asset directories with hyphens in their names (not legal Python identifiers)
  made mypy refuse the run outright; and the step was `continue-on-error`. Fixing the first two
  reveals **1826 errors across 572 of 1583 files**. A ratchet mirroring `ruff_ratchet.py` now
  gates on a committed baseline (`scripts/ci/mypy_baseline.txt`, `1826 1583`) so no PR can add
  new type debt without demanding an 1826-error cleanup first.
- The ratchet stores errors **and** files-checked: widening `exclude` also lowers the error
  count, so a count-only ratchet would report "debt reduced" and bake the blindness into the
  baseline via `--update`. It also refuses an *aborted* mypy run rather than counting it — a
  crash prints `Found 1 error`, which would have ratcheted 1826 → 1 and retired the gate.
- `integrations/agentverse/api_llm_executor.py` + `cost_optimization/cost_tracker.py`: two
  hand-maintained Anthropic price tables, different packages, different units, both on live
  paths, had drifted in **opposite** directions. `COSTS` priced `claude-opus-4-6` at 15/75 (3×
  the real 5/25) and had no entry at all for Opus 5, Opus 4.8, Sonnet 5 or Haiku 4.5 — so those
  reported `cost_usd = $0.00`, real spend read as free. `model_costs` knew only retired
  `claude-3-*` models, so every current model hit the `0.015` default ($15/MTok), a 3×–15×
  overestimate biasing cost-aware routing against the cloud.
- `track_usage_fast` now prices output tokens at the output rate via an optional `output_tokens`
  argument; omitting it reproduces the previous behaviour exactly. Previously one input-derived
  rate was applied to input+output combined, under-counting output-heavy requests by up to 5×.
- `research/cost_optimization.py`: **1000x unit error** in `DEFAULT_COSTS`. `calculate_cost`
  computes `(tokens / 1000) * cost_per_1k`, so the dict is dollars per 1K tokens — but every
  entry held the per-MILLION-token list price, while the inline comments claimed per-1K. The
  comments agreeing with the code's unit is what hid it; only the numbers were wrong. Measured:
  one 1M-token `claude-3-sonnet` experiment reported **$3,000.00** against a $10 budget (true
  cost $3.00), so any non-trivial run blew its budget on the first call and forced a downgrade.
  Live path — `research_squad.py` and `orborous.py` import it, and `CostAwareRouter` uses it for
  downgrade decisions. Current models added; unknown models still price at $0.00 but now warn.
- `scripts/ollama-proxy.py`, `scripts/ollama-anthropic-proxy.py`: `claude-haiku-4-5-20251213`
  does not exist. Replaced with the canonical undated `claude-haiku-4-5`, matching the
  neighbouring opus/sonnet entries and the ids used in both pricing tables.

### Added — model-store capacity guard + router liveness split (1.12.0)
- `inference/silicon_residency.py`: `ModelStorage` + `parse_storage()` read `model_storage` from
  `:13305/api/v1/system-info`. Measured on the live router: 764 GiB used of 769, **5.57 GiB free**
  — less than a single mid-size GGUF. No existing probe could see it: every fleet probe reads
  *memory* residency, and the store is mode `0750` under `User=lemonade`, so
  `du -sh /var/lib/* 2>/dev/null` reports ~15 GB for all of `/var/lib` because the
  `Permission denied` goes to stderr.
- Alerts gate on **absolute free bytes**, not the used fraction. On ZFS statvfs `total` is
  `used + pool-wide available` minus withheld slop, so the denominator moves for reasons unrelated
  to this store; a 100 GiB store at 88% used looks unremarkable and still cannot accept the 17 GB
  model the fleet runs. The fraction is retained as a secondary dashboard signal.
- An unmeasured store is a third state, never "healthy": `headroom_for_gb()` returns
  `bool | None`, because reading unmeasured as `False` blocks legitimate work and as `True` walks
  into a mid-download ENOSPC.
- `inference/silicon_supervisor.py`: `diff_storage()` + `next_storage_baseline()` and the event
  kinds `store_critical` / `store_low` / `store_recovered` / `store_unmeasured`, all
  edge-triggered — level-triggered, one unchanging condition emits 2880 identical CRITICALs a day
  at a 30s poll.

### Fixed — `/api/v1/health` was being used as a liveness oracle
- Measured: `/health` and `/models` blocked for 20s+ on two of three probe rounds while
  `/system-info` answered in ~3ms throughout. Both blocking endpoints enumerate loaded models and
  contend with a lock a busy backend holds. A supervisor polling `/health` with a 10s timeout
  emitted `router_unreachable` (CRITICAL) every time the fleet got busy.
- `scripts/ops/silicon_supervisor_daemon.py` now probes `system-info` for liveness. A `/health`
  stall emits `census_stalled` (warning) / `census_resumed` (notice); `router_unreachable` requires
  the cheap endpoint to fail too. Storage monitoring continues through a census stall, since it
  reads the endpoint that does not block.

### Fixed — stranded capacity incident across a blind cycle
- Found by two independent review lanes before landing. With `unmeasured` as a fourth *capacity*
  state, `critical -> blind -> ok` compared `ok` against a prior of `unmeasured`, matched no
  recovery branch, and emitted nothing — leaving a critical incident open for the life of the
  process. A test in the suite had asserted that silence was correct.
- Capacity and measurability are now separate axes; `next_storage_baseline()` retains the last
  **measured** store so a blind cycle cannot erase an open incident. Mutation-verified: the buggy
  caller's event sequence is a strict *prefix* of the correct one, so the failure is a missing
  event and nothing in the logs looks anomalous.

### Fixed — loop_mcp datamesh bus write path (1.11.1)
- `mcp/loop_mcp.py`: `event_publish` reported `success: true` while writing zero rows. SurrealDB
  answers HTTP 200 for SurrealQL *statement* errors, placing the failure in the body as
  `{"status": "ERR", ...}`; the code checked only the HTTP status. Any non-OK statement is now
  surfaced as an error.
- `integrations/kaggle_api.py`: import no longer pulls Kaggle or writes to stdout.
- Regression cover: 5 of 16 tests in `tests/unit/test_loop_mcp.py` fail against the pre-fix source,
  so the suite discriminates rather than merely passing.


## [1.11.0] — 2026-08-20

### Added — Repository Front Page & Hygiene Campaign
- `README.md`: honest, verified front page — real Quick Start
  (`uv run python examples/quickstart.py`, `make validate`), working section
  anchors, CodeQL + Security Scan badges, Documentation and License sections
- `pyproject.toml`: `[project.optional-dependencies] rl` extra
  (`stable-baselines3`) so `make train` works out of the box via
  `uv sync --extra rl`; Homepage/Documentation/Changelog project URLs
- `docs/README.md`: curated documentation index
- `.gitattributes`: LFS patterns for `*.safetensors`, `*.mp3`, `*.mp4`, `*.wav`
  (future files only — no history migration)

### Fixed — Truth Reconciliation
- License consistently AGPL-3.0-or-later + commercial dual (README badge and
  footer said Apache 2.0; `docs/index.md` said MIT)
- Python floor consistently 3.13+ (README badge and prose said 3.11)
- Stale counts refreshed from measurement: 182 PRIME skills (was "235"),
  12,000+ collected tests (was "6,133"), 50+ validate checks (was "18"/"25")
- `CITATION.cff` version aligned with `pyproject.toml`; `SECURITY.md`
  supported-versions table updated

### Changed — Root Hygiene
- Removed tracked runtime state (`.skill_validation.json`,
  `.checkpoint_session_104_validation.json`) and 11 zero-byte accidental
  dotfiles/scripts from the repository root
- Moved one-off root scripts to `scripts/` and `scripts/archive/`, generated
  reports and internal writeups to `docs/archive/`, images to `docs/media/`,
  Kaggle artifacts to `submissions/`
- `.gitignore`: symlink-safe cache patterns and generated-artifact guards

### Fixed — Adversarial Review Hardening 2026-08-17
- `recursive_learning.py`: Added `asyncio.TimeoutError` handling + configurable
  timeout via `SURREAL_UPSERT_TIMEOUT_S` env var (default 5.0s)
- `cross_session_event_bridge.py`: Added `asyncio.TimeoutError` handling +
  configurable timeout via `EVENT_HANDLER_TIMEOUT_S` env var (default 3.0s)
- `difficulty_estimator.py`: Added `_LATENCY_MIN_SAMPLES=3` gate — empirical
  median latency is only trusted when a tier has ≥3 observations (GIC-LAT3)
- `poincare_manifold.py`: Added `DeprecationWarning` to `PoincareManifoldTracker`
- `pyproject.toml`: Bounded `torch>=2.8.0,<3.0.0` to prevent surprise breakage

### Note — v1.8.0 gap
v1.8.0 was skipped due to a version conflict between two PRs (#283 and #284)
that both attempted to bump to 1.8.0. PR #284 merged first as v1.9.0, and #283
was rebased to v1.10.0. The gap is cosmetic — no release artifact was published
at v1.8.0.

### Added — Session Registration Script 2026-08-17
- `scripts/ops/register_session.py`: Reusable script for agents to register
  their session with the EventBus and persist a kanban card to SurrealDB +
  Obsidian vault (AGENTS.md § EventBus & Agentic Kanban Bridge mandate)

### Added — Latency-Aware GIC Tier Selection 2026-08-15
- `DifficultyEstimator.predict_tier()` now picks the FASTEST tier by median
  latency among quality-adequate tiers, not the positionally-cheapest. Based
  on the 2026-08-13 GIC tier-routing soak proving MoE+MTP is faster than
  dense-8B despite higher parameter count.
- `DifficultyEstimator.record()` accepts optional `latency_s` parameter
- `_TierRecord` has `latency_s` field (default 0.0, backward compatible)
- Falls back to positional `_TIER_ORDER` when no latency data recorded

### Fixed — CI/CD Repair 2026-08-15
- Moved ROCm torch (`torch==2.8.0+rocm6.3`, `pytorch-triton-rocm==3.4.0`) from
  mandatory `[project.dependencies]` to optional `[project.optional-dependencies] rocm`
  so CI on `ubuntu-latest` installs CPU torch from PyPI instead of failing on
  missing ROCm wheels. The `[tool.uv.sources]` override was removed for
  torch/torchvision (they now resolve from PyPI by default); only
  `pytorch-triton-rocm` retains the ROCm index mapping.
- Playwright workflow (`playwright.yml`) now skips for `dependabot[bot]` actor
  to prevent npm lockfile bumps from triggering broken UI builds.

## [1.10.0] — 2026-08-17

### Added
- `scripts/ops/register_session.py`: EventBus session registration script

## [1.9.0] — 2026-08-17

### Added
- `recursive_learning.py`, `cross_session_event_bridge.py`, `ctac_engine.py`,
  `oom_guard.py`, `contracts.py` — AGENTS.md referenced modules merged to main
- `PoincareManifoldTracker` backward-compat wrapper for `PoincareManifoldND`

## [1.8.0] — 2026-08-17

### Added
- `scripts/ops/register_session.py`: EventBus session registration script

## [1.7.0] — 2026-08-15

### Added
- Latency-aware `DifficultyEstimator` tier selection (GIC-LAT1/LAT2):
  `predict_tier()` picks the fastest tier by median latency among
  quality-adequate tiers instead of the positionally-cheapest.

## [1.6.1] — 2026-08-15

### Fixed
- CI lint job: `pytorch-triton-rocm==3.4.0` had no wheel for `ubuntu-latest` —
  moved to optional `rocm` extra; CI now uses CPU torch from PyPI.
- Playwright workflow: skips Dependabot PRs to avoid broken UI builds from
  removed icon exports in npm dependency bumps.

## [1.6.0] — 2026-08-14

Elegant-simplicity execution: net −11.3k LOC with zero functionality lost.
Adversarially-verified audit + execution + pre-landing main-tree re-audit:
`~/vaults/cohezion-vault/reports/20260814-elegant-simplicity-audit.md`;
per-file rationale in `docs/simplification/RETIRED-2026-08-14.md`.

### Added
- `TieredOrchestrator(pre_dispatch_verifier=...)` — optional AutoHarness-style
  gate (ported from the retired unified_orchestrator); default `None` preserves
  O1–O9 byte-identically
- `kv_budget.kv_cache_bytes(..., mla_latent_dim=...)` — DeepSeek MLA
  latent-attention footprint axis (ported from the retired kv_cache_calculator)
- `cohezion.reliability.circuit_protected` decorator + `CircuitOpenError` —
  fail-fast variant of `get_circuit` (ported from reliability/circuit_breaker.py);
  the surviving consumer (swarm/intelligence_pipeline.py) migrated
- `SemanticTextEncoder.encode_batch()` — ported from the retired
  sentence_encoder.py for its two live ops-script consumers (found in the
  pre-landing main-tree re-audit)
- `tdd_adversarial.PIPELINE_ATTACK_VECTORS` — 9 pipeline probes as pure data
  (ported from the retired consortium_instigator)
- `flume.latent_engine.complexity_heuristic` (ported from distributed_swarm)
- Observability router MOUNTED: `/metrics/{unified,cache,efficiency,health,
  guardrails,resources,trends,dashboard}` now reachable (was dead code)

### Changed
- `cohezion.compound.CompoundSessionManager` now exports the PRODUCTION
  session_manager class (was a checkpoint-incompatible decoy)
- `swarm/__init__.py`: 28 copy-pasted guarded re-export blocks replaced by a
  `_OPTIONAL_EXPORTS` table + loader; export surface proven byte-equal (223/223)
- `eval/self_eval.py` — moved from the one-module `evaluation/` package (rename)
- `MCPInfrastructureState` gained cross-server unified-snapshot fields
- 13 wiring tests in test_new_packages_wired.py un-skipped (a phantom-module
  importorskip had silently skipped the whole file since creation)

### Removed
- 33 dormant/rival files (~11.7k LOC), each with an adversarially-verified
  preservation path and a pre-landing consumer re-audit against main:
  dynamic_compound_system trio, unified_orchestrator, distributed_swarm,
  smart_orchestrator + specialist_registry, optimized_session_manager,
  consortium_instigator, compound_unified, quantum_performance_monitor,
  core/connection_pool, shadowed core/persistence/repositories.py +
  mcp/manager.py, security/pipeline.py, reliability/circuit_breaker.py,
  cache/sentence_encoder.py, kv_cache_calculator, jepa_world_model_persistent,
  agi speculative_decoding_engine, phantom packages (pipelines/evo/policies),
  byte-identical api/services/modules.py, and their orphaned tests

## [1.4.0] — 2026-08-13

### Added — Landing train 2 (surgical harvests and cherry-picks)
- Daemon health surface (`data_mesh/daemon_health.py`): typed heartbeat events and
  stalled-daemon detection from the bus (harvested from `fix/classify-actionability-negation`)
- `classify_actionability` negation guard: per-clause negator matching — "adopt nothing"
  no longer auto-cards itself as actionable work; licence as structured fields
- Datamesh orphan types promoted onto the canonical `cohezion.data_mesh` surface
  (`FederationLayer`, `DomainEndpoint`, `UnifiedRecord`, `Physics12D` — 6 red tests green)
- `DataMeshEventBridge` loss counters — the bridge now counts what it silently loses

### Fixed
- `bonsai` added to `_THINKING_MODEL_MARKERS` (silent empty output from Bonsai models)
- Three stacked import bugs in `compound/universal/init.py`
- `uv.lock` was corrupt after a textual lockfile merge (duplicate beautifulsoup4 entries) —
  every CI job failed at dependency install; regenerated from origin's known-good lock.
  Lockfiles are generated artifacts: never text-merge them

## [1.3.0] — 2026-08-13

### Added — Landing train (10 branches reviewed and merged)
- Model residency service: `inference/residency_ledger.py` + residency-aware hotswap and
  event-consumer wiring (`feat/model-residency-service`)
- Semantic-agreement quality signal: `inference/agreement.py` (Youden-calibrated threshold
  0.40) now CONSUMED by `AutoDQA.evaluate(peer_outputs=...)` — peer disagreement lowers the
  verdict score; the producer-without-consumer gap the branch shipped is closed
- FLUME sparse-workspace readout (`flume/workspace_readout.py`) + executor/journey wiring
- Work-queue durability: file locking, atomic writes, and notes preservation for the
  actioner work queue (`fix/work-queue-silent-data-loss`)
- Runnable quickstart (`examples/quickstart.py`) + ManifoldEnv info-dict docs (GH#203/204)
- Inference gauntlet + lemonade recipe hardening (`worktree-spicy-inventing-goblet`)
- Mycelium pattern-query + SurrealDB healing-query integration in the researcher
  verification lane (`agent-1784138792`)

### Fixed
- `cohezion.api` package was UNIMPORTABLE on every lineage (local main, origin/main): the
  Wave-2B `_helpers.py` extraction renamed functions to public names while `__init__` still
  imported underscore names, and `set_token_client` lives in `routes/metrics.py`. Latent
  because no CI test imported `cohezion.api`; exposed by the new work-queue tests
- Stored XSS in the artifacts gallery (`static/artifacts/index.html`): manifest entries are
  user-appendable, but title/summary rendered via `innerHTML` and `file` accepted
  `javascript:` URLs. Now textContent rendering + relative-path-only href guard
  (found by the ollama-cloud adversarial review lane)
- `research_products._emit_data_product_event`: required `timestamp` float was omitted
  (every write rejected) and HTTP-200 was read as success while SurrealDB reported the
  statement error in the body (`fix/silent-write-defects`)
- Skill frontmatter validity across `.claude/.agents/.pi` skill trees + a rewritten
  `validate_skill_schema.py` that can actually fail

### Changed
- `.claude/rules/harness.md` corrected: Python floor is 3.13 (torch+ROCm caps at 3.13;
  the stale "3.11 required" note was wrong)
- Ruff: 13 files reformatted, 16 auto-fixes; lint debt held at baseline parity

## [1.2.1] — 2026-08-01

### Fixed — Coherence sweep + adversarial review
- `EventBus.stop()` deadlocked and silently dropped queued events; now drains before stopping,
  with a bounded `drain_timeout` so a hot producer or hung handler cannot hang shutdown
- `EventBus.stop()` clears `_running` in a `finally:` (a cancelled stop left the bus
  "running-but-dead")
- `EventBus.publish()` returns `False` when the bus is not running, instead of returning
  `True` and discarding the event
- Session liveness (`SessionRegistry.list_active`) is pid-namespace aware; rows are annotated
  `liveness=confirmed|assumed`. A future `last_seen` no longer confers permanent liveness, and
  an unreadable `boot_id` no longer yields a collidable namespace token
- `scripts/ci/doc_code_consistency.py` gained E5: a nested `CLAUDE.md` declaring a module count
  must match the package's actual module count (caught `data_mesh` declaring 12 with 13 on disk)
- Corrected phantom provenance in 5 nested `CLAUDE.md` — they credited a generator that exists
  in no commit; they are hand-maintained

### Changed — Version governance
- `src/cohezion/__init__.py.__version__` is now derived from installed package metadata instead
  of being a hand-maintained duplicate that had drifted to 1.0.2 while `pyproject.toml` was 1.2.0
- `scripts/ci/version_governance.py` now verifies the version was actually BUMPED by at least the
  bump type implied by the commits, comparing head against the PR base. It previously classified
  the bump type and then passed regardless, so a release-worthy PR could land with no bump.

## [Unreleased]

### Added — Consolidation Campaign 2026-07-09
- Reconciled local compound-loop spine (61 commits) with origin polish/CI waves (228 commits)
- Card-aware router with 14 default profiles + `extend_claude_aligned()` (Stack A1-A7)
- Four researcher lane scripts + cron entry (WS2B)
- Daily researcher wired into executor + cron + AGENTS (WS2C)
- Card-aligned execute_fn with datamesh hooks
- Card-aligned semantic cache with FLUME VAE joint key
- Token-efficient prefix with FLUME_VAE hash
- Cross-link verify_evolve with 5 datamesh surfaces
- 3 operational skills: additive-dataclass, behavior-testing, datamesh-native
- Autoresearch state migrated to SurrealDB + Obsidian vault
- Model recipes + empirical harness for local fleet
- Fleet-first inference + LearningRecorder closes BaseAgent→Mycelium loop
- Security hardening: SurrealQL parameterization, Makefile timeouts, auth
- Anthropic Universes living resume + calibration harness + PrefillActivationRouter
- Local-inference newsletter miner, RSS mining, wiring-sweep audit, quota-aware extend_claude
- Model-card-aligned sampling defaults implemented (was TDD-red stub)
- Task classifier math_reasoning routing + short_answer gate_chars=10
- Ruff excludes for worktrees, archives, .pi, .tmp_kaggle
- Gitignore for .playwright-mcp, .aider, .tmp_kaggle large artifacts

### Added — Worktree landing 2026-07-09 (imperative-wondering-kettle)
- `validate_changelog_claims()` in `scripts/ci/version_governance.py`: structural CI
  guard verifying that any backtick-quoted file/module path mentioned in a Changelog
  entry actually exists in the repo, wired into the existing governance check
- `LatentGravityNavigator` (`src/cohezion/flume/latent_gravity.py`) — SWIFT/CarbonEngine
  analog with journey-nexus route exposure
- JourneyNexus full service implementation (quadrature/narrate/omni_chat) replacing the
  consolidated stub, with real FLUME text-encode (`LemonadeEmbedBridge` via :13305,
  hash-VAE fallback), HIHO-centered coherence, and the real `TTSRequest` contract
- A2A agent-card discovery falls back to the repo common root in sparse worktrees
- SurrealDB vault watcher: dead papers/concepts filter fixed (routes
  cortex/cerebellum/patterns/decisions) + PollingObserver fallback for exhausted inotify
- `lemonade_server_status` probes `/api/v1/health` (`/api/v1/status` is 404 on Lemonade 8.x)

### Removed
- Corrected a previously-listed `Added` entry describing a `cohezion.release` module
  (semantic version detection, conventional-commit bump validation, changelog
  enforcement, 41 unit tests) — verified via `git log --all` that this module was
  never actually committed on any branch. The entry described work that was never
  done; removed rather than left standing.

### Note on release automation
- Real semver/changelog automation already exists and is more complete than the
  removed entry implied: `scripts/ci/version_governance.py` (conventional-commit
  classification, bump-type detection, changelog/version consistency) gates PRs via
  `.github/workflows/semver-check.yml` and gates releases via
  `.github/workflows/release.yml`, which runs `python-semantic-release publish` on
  push to `main`. Both workflows require `runs-on: self-hosted`. No tag has been cut
  since `v0.5.0` because that self-hosted runner is offline (a known, already-tracked
  issue) — not because the tooling is missing. Restoring the runner, not building new
  release tooling, is the actual unblock.

### Fixed
- Removed 3.5GB safetensors blob from git history (Kaggle artifact accidentally committed)
- Removed .playwright-mcp captures containing ad tracking URLs (GitHub secret scanner block)
- aiohttp async context manager mock patterns in connector tests (43 tests now passing)
- Metacognitive intent validation boundaries for confidence, z_vector, and physical state dimensions
- tests/compound/conftest.py syntax error (duplicate closing paren + double docstring)
- Live test skip logic for STT/image tiers (check model loaded, not just port reachable)
- Committed merge-conflict markers removed from `Makefile`

## [1.0.2] - 2026-05-02

### Added
- CI Pipeline stabilized: disabled auto-test generation, fixed skill name sanitization
- Star infrastructure: PR/issue templates, CODEOWNERS, CITATION.cff, Docker support

### Changed
- Root directory cleaned: 80+ cruft files relocated to archives
- Branch hygiene: 50+ stale branches deleted, 52 abandoned worktrees removed

### Fixed
- AutoHarness: verification rules and harness_check.py generated

## [1.0.0] - 2026-02-28

### Added

- Initial release of Cohezion
- Training environments for agentic AI operating in simulated universes
- Evaluation systems and ML infrastructure
- FLUME VAE (256D latent space) for universe modeling
- Compound Session Manager for agent orchestration
- Semantic cache for L1/L2/L3 caching
- PRIME skill definitions system
- FastAPI backend with 72 endpoints

### Changed

### Deprecated

### Removed

### Fixed

### Security
