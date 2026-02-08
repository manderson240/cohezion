# Contributing to Cohezion

Thank you for your interest in contributing to Cohezion! This project is an agentic AI framework for 12D universe simulation, FLUME manifold encoding, and multi-agent swarm orchestration.

## Development Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) for package management

### Initial Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up pre-commit hooks (optional but recommended):
   ```bash
   make dev-setup
   # or manually:
   pre-commit install
   ```

## Code Quality Tools

This project uses modern Python tooling for code quality:

- **Ruff** - Fast linter and formatter (replaces Black, isort, flake8)
- **mypy** - Static type checking
- **pytest** - Testing framework

### Using Make (Recommended)

```bash
make format      # Format code with ruff
make lint        # Lint and auto-fix issues
make lint-check  # Check linting without fixing
make type-check  # Run mypy type checking
make test        # Run test suite
make all         # Run format, lint, type-check, and test
make ci          # Run all CI checks locally
make clean       # Clean up cache files
```

### Manual Commands

```bash
# Format code
ruff format .

# Lint and auto-fix
ruff check --fix .

# Check linting without fixing
ruff check .

# Type checking
mypy --ignore-missing-imports src/cohezion/

# Run tests
pytest tests/
```

## Code Style

- Line length: 88 characters
- Quote style: Double quotes
- Python version: 3.13+
- Type hints encouraged but not required

The project configuration in `pyproject.toml` enforces:
- PEP 8 compliance
- Import sorting
- Security best practices (Bandit rules)
- Common bug patterns (Bugbear rules)
- Code simplifications
- Modern Python syntax (pyupgrade)

## Pull Requests

When submitting a pull request, please ensure your changes are consistent with the project's architecture and include tests for new functionality.

## Issues

When submitting an issue, please provide as much detail as possible including reproduction steps and environment information.
