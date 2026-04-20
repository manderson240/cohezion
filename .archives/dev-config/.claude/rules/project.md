---
paths:
  - "/"
  - "pyproject.toml"
  - "Makefile"
---

# Cohezion Project Overview

**Last Updated:** 2026-02-14

## Description

Compound Engineering Framework for Agentic AI with multi-agent coordination, 12D FLUME trajectory tracking, intelligent skill selection, and automatic error recovery.

## Technology Stack

- **Language:** Python 3.13+
- **Package Manager:** uv (never bare python/pip)
- **Web Framework:** FastAPI + Uvicorn
- **Database:** SurrealDB (ws://localhost:8001)
- **AI/ML:** Anthropic API, sentence-transformers, torch (optional)
- **Testing:** pytest, pytest-asyncio (2,854 tests, 99.3% pass rate)
- **Linting:** ruff (format + lint), mypy (type checking)

## Directory Structure

```
src/cohezion/          # Main framework code
├── compound/          # Compound engineering loop (executor, skill refiner)
├── swarm/             # Multi-agent coordination and routing
├── flume/             # 12D FLUME trajectory encoding
├── agents/            # General-purpose agent implementations
├── core/              # Core services (MCP client, persistence)
├── reliability/       # Circuit breakers, error handling
├── knowledge_graph/   # Vault integration and patterns
└── skills/            # PRIME skill definitions (*.md + *.py)

tests/                 # Test suite (organized by module)
scripts/               # Utility scripts and drivers
cloud-vault-mcp/       # MCP vault server (separate project)
```

## Development Commands

```bash
# Setup
uv sync                              # Install dependencies

# Code quality
make format                          # Format code with ruff
make lint                            # Lint and auto-fix
make lint-check                      # Check without fixing
make type-check                      # Run mypy

# Testing
uv run pytest tests/ -q              # Full suite (~5 min)
uv run pytest tests/compound/ -v     # Module tests
make test-fast                       # Fast unit tests only

# CI workflow
make all                             # format + lint + type-check + test

# Health checks
make vault-status                    # Check MCP vault connectivity
make health-check                    # Run project health checks

# Clean
make clean                           # Remove cache files
```

## Key Entry Points

- **CLI:** `src/cohezion/__main__.py` (entry point: `cohezion`)
- **API:** `src/cohezion/api.py` (FastAPI app, port 8080)
- **Compound Loop:** `src/cohezion/compound/executor.py` (CompoundExecutor)

## Architecture Notes

- All agents inherit from `BaseAgent` (`cohezion.agents.base`)
- Circuit breakers required for external calls (`cohezion.reliability.get_circuit()`)
- SurrealDB connection via `cohezion.core.persistence.surreal_client`
- Global Ollama concurrency limit: 4 simultaneous requests
- HIHO stability target: 0.5 coherence overlap
