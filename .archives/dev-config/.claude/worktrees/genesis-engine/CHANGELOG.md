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

### Fixed
- aiohttp async context manager mock patterns in connector tests (43 tests now passing)
- Metacognitive intent validation boundaries for confidence, z_vector, and physical state dimensions

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
