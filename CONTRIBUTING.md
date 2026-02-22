# Contributing to Cohezion

Thank you for your interest in contributing to Cohezion! This project is an agentic AI framework for 12D universe simulation, FLUME manifold encoding, and multi-agent swarm orchestration.

## Development Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) for package management (**never** use bare `pip`)

### Initial Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Code Quality Tools

This project uses modern Python tooling for code quality:

- **Ruff** - Fast linter and formatter (replaces Black, isort, flake8)
- **mypy** - Static type checking
- **pytest** - Testing framework
- **pre-commit** - Git hook enforcement

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
uv run ruff format .

# Lint and auto-fix
uv run ruff check --fix .

# Check linting without fixing
uv run ruff check .

# Type checking
uv run mypy --ignore-missing-imports src/cohezion/

# Run tests
uv run pytest tests/ -q
```

## Code Style

- Line length: 100 characters
- Quote style: Double quotes
- Python version: 3.13+
- Type hints: mandatory for new code

The project configuration in `pyproject.toml` enforces:
- PEP 8 compliance
- Import sorting (isort via ruff)
- Security best practices (Bandit rules via ruff `S` prefix)
- Common bug patterns (Bugbear rules via ruff `B` prefix)
- Code simplifications
- Modern Python syntax (pyupgrade)

## Branch Strategy

This project uses **GitHub Flow**:

- `main` is the only long-lived branch
- All work happens on feature branches merged via pull requests
- Branch naming: `feature/*`, `fix/*`, `refactor/*`, `docs/*`, `session-*`
- Conventional commit messages: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`

## Pull Requests

- Fill out the PR template completely
- Ensure CI passes (lint, test, validate)
- Keep PRs focused on a single concern
- Include tests for new functionality
- No files > 1MB without git-lfs

## Security

Please report security vulnerabilities via [GitHub Security Advisories](https://github.com/manderson240/cohezion/security/advisories/new), **not** public issues. See [SECURITY.md](SECURITY.md) for details.
