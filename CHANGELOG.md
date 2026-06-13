# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Semantic version detection module (`cohezion.release`) with git tag parsing and pyproject.toml integration
- Conventional commit bump validation (major/minor/patch classification)
- Changelog section enforcement by bump type (Keep a Changelog format)
- 41 unit tests for release module (version detection, bump validation, changelog validation)
- Autoresearch FLUME VAE optimization (2026-05-15 sessions 1-4): 195+ total experiments; **definitive optimal config**: hd=4096, 2-layer decoder, latent_dim=768, cyclic β amp=0.005, AdamW wd=1e-4; 4-seed mean **0.8815 ± 0.006** (+13.2% vs baseline); architecture law peaks at hd=4096 (hd=6144→0.8881 worse, hd=8192→0.9016 much worse); period 100-300 gives identical multi-seed means; `build_optimal_vae()` factory function added to `vae.py`; 3-layer decoder consistently worse than 2-layer (kl=0.30 vs 0.79)
- `routing_head` auxiliary layer on `FlumeVAE` latent space (optional, not in public `forward()` return)
- `FlumeVAETrainer` docstring with empirically-validated hyperparameter recommendations
- `IncrementalVAETrainer` safety clamp: auto-corrects inherited `kl_weight≥0.1` with a warning

### Fixed
- **Critical**: `kl_weight` default 0.1→0.01 across 11 training surfaces — β≥0.1 causes posterior collapse (phase transition confirmed by autoresearch 2026-05-15)
- `batch_size` default 64→128 across 9 training surfaces; bs=160 is optimal for 160-sample corpora (+0.8-1.5% improvement over bs=64)
- `FlumeVAE.forward()` return signature restored to 4-tuple `(recon, mu, log_var, z)` — regression from autoresearch hooks
- Pre-existing `NameError` in `tests/flume/test_evaluate_vae.py` (missing `import pytest`)
- aiohttp async context manager mock patterns in connector tests (43 tests now passing)
- Metacognitive intent validation boundaries for confidence, z_vector, and physical state dimensions

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
