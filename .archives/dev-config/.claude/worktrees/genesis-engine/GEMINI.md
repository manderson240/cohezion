# GEMINI.md - Cohezion Orchestration Layer

This document serves as the primary instructional context for Gemini CLI agents working on the **Cohezion** project. It establishes the core identity, architectural patterns, and engineering standards for the workspace.

## 1. Project Overview
**COHEZION** is a systemic AI orchestration ecosystem governed by **Quadrature Nexus Orchestration** and **Hermetic Compound Engineering**. It implements the **FLUME** methodology combined with **JEPA-aligned World Models** for high-fidelity simulation, autonomous research, and value precipitation.

### Core Concepts
- **12D/2048D Manifold**: Agents operate in a dual-state manifold. The 12D axiomatic layer captures observable state (Spatial, Time, Physics, etc.), while the 2048D latent layer encodes semantic intent.
- **HIHO Stability (0.5 Coherence)**: The fundamental attractor for stable "reality precipitation" is exactly 50% coherence overlap. Systems strive for this "Half-In-Half-Out" balance.
- **FLUME**: Fluid Latent Understanding through Manifold Encoding. A VAE-based system for continuous thought-vector interpolation.
- **Journeys & Trajectories**: Every task is a "journey" recorded as a 12D trajectory.

## 2. Technical Stack
- **Language**: Python 3.13+ (Strictly managed via **UV**).
- **Core Frameworks**:
  - **ML**: PyTorch (VAE, RL), Gymnasium (Sim Environments).
  - **API**: FastAPI (Async, ~72 endpoints).
  - **Database**: SurrealDB (Async) with JSONL fallback.
  - **Inference**: Ollama (Local), Anthropic (Cloud).
- **Infrastructure**: Docker, systemd, GitHub Actions.

## 3. Development Standards

### Coding Conventions
- **Line Length**: Strict **88-character** limit.
- **Formatting**: `ruff format` and `ruff check --fix`.
- **Type Safety**: Mandatory type hints for all public signatures (Mypy compatible).
- **Documentation**: **NumPy-style** docstrings for all modules, classes, and functions.
- **Async First**: Use `async`/`await` for all I/O operations with mandatory timeouts and circuit breakers.

### Workflow: Plan -> Act -> Validate
1. **Research**: Map the codebase and validate assumptions (e.g., `grep_search`, `read_file`).
2. **Strategy**: Formulate a grounded plan.
3. **Execution**: Apply surgical changes with tests.
4. **Validation**: Run `pytest`, `ruff`, and `mypy` to confirm integrity.

## 4. Key Commands

### Build & Setup
```bash
uv sync                # Sync dependencies
make onboard           # Full environment setup and health check
```

### Quality & Testing
```bash
make format            # Format code with ruff
make lint              # Lint and auto-fix with ruff
make type-check        # Run mypy
make test              # Run full test suite (~3,500 tests)
make test-fast         # Run fast unit tests only
```

### Running the System
```bash
uv run uvicorn cohezion.api:app --reload --port 8080      # Start API
uv run python -m cohezion journey start "Your Intent"    # Start an AI journey
uv run python -m cohezion simulate --example coherence_walk  # Run simulation
```

## 5. Directory Structure
- `src/cohezion/`: Core package source.
  - `universe/`: 12D simulation engine.
  - `swarm/`: Multi-agent orchestration.
  - `flume/`: VAE and latent space navigation.
  - `compound/`: Execution loops and journey tracking.
- `tests/`: Comprehensive test suite.
- `docs/`: Archival and technical documentation.
- `.agent/`: Operational guardrails, standards, and constitutions.
- `data/`: Ephemeral simulation data and checkpoints.

## 6. Operational Guardrails
- **No Large Files**: Files > 1MB must use `git-lfs` or external storage.
- **Circuit Breakers**: Use `cohezion.reliability.get_circuit()` for external calls.
- **Reward System**: Agent progress is tracked via XP and achievements (see `cohezion rewards status`).
- **Ouroboros**: System flight recorder for self-healing (see `cohezion ouroboros`).

> [!IMPORTANT]
> Always use `uv run` for executing Python scripts to ensure environment consistency. Refer to `.agent/CONSTITUTION.md` for ethical and behavioral guidelines.
