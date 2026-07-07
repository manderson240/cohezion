# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
