# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.0] — 2026-08-14

### Added
- GIC-LAT1 latency-aware tier selection: `src/cohezion/compound/difficulty_estimator.py`
  `record()` gains an optional `latency_s`; `predict_tier` ranks quality-adequate tiers by
  measured median latency instead of assuming the tier order is a cost order (the
  2026-08-13 live soak measured the ordering inverted: the 35B-A3B-MTP tier was both
  stronger and faster than the 8B dense-thinking tier). Latency never overrides quality
  adequacy; with no latency data the behavior is unchanged.
- GIC-LAT2 consumption invariant: paired-arm discriminating test through the full
  `execute_task` path proving latency-informed predictions reach the O9 cascade-entry
  binding (`tests/compound/test_tier_resolution.py`)
- `SkillRefiner` threads `duration_seconds` into the estimator as the latency producer

### Fixed
- `src/cohezion/mcp/loop_mcp.py` `event_publish` wrote ZERO rows while returning
  `success: true` — omitted the required int `priority` and wrote a datetime into the
  TYPE float `timestamp`. Now schema-conformant (priority param, epoch-float timestamp);
  first row this tool ever wrote verified live by count delta (1863 -> 1864)
- `_surreal_sql` treated HTTP 200 as success; SurrealDB reports SurrealQL failures as
  per-statement `status: ERR` inside HTTP 200 — statement errors now surface as error dicts
- stdio MCP stdout pollution: `src/cohezion/integrations/kaggle_api.py` imported
  kaggle/kagglehub at module level; the kaggle package conditionally prints a version
  warning to STDOUT, corrupting the JSON-RPC channel of any stdio MCP server importing
  the package tree. Imports are now lazy (method-level)

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
