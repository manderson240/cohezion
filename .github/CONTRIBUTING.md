# Contributing to Cohezion

Thank you for your interest in contributing to Cohezion! This project follows the **BMad Method**, a comprehensive, AI-driven framework for agile development. Before you begin, please familiarize yourself with the core principles of the BMad Method.

## The BMad Method

The BMad Method is a modular, agent-based system for managing the entire software development lifecycle. It is composed of several key modules:

- **BMM (BMad Method Module):** The core orchestration system for AI-driven agile development. It defines the agents, workflows, and processes for managing stories and development. For more information, please see the [BMM README](bmad/bmm/README.md).
- **BMB (BMad Builder Module):** A set of tools and workflows for creating and extending BMad components, such as agents, workflows, and modules. For more information, please see the [BMB README](bmad/bmb/README.md).
- **CIS (Creative Intelligence Suite):** A suite of AI agents that facilitate creative processes like brainstorming, design thinking, and problem-solving. For more information, please see the [CIS README](bmad/cis/README.md).

## Getting Started

To contribute to Cohezion, please follow these steps:

1. **Familiarize yourself with the BMad Method:** Before creating or modifying any components, it is essential to understand the principles and conventions of the BMad Method. The README files for each module are the best place to start.
2. **Follow the workflows:** The BMad Method is built around a set of well-defined workflows. Please use these workflows to guide your contributions.
3. **Use the provided agents:** The BMad Method includes a variety of specialized agents for different tasks. Please use these agents to ensure consistency and quality.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- pip or uv for package management

### Initial Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Install development tools:
   ```bash
   pip install ruff mypy pytest pre-commit
   ```

4. Set up pre-commit hooks (optional but recommended):
   ```bash
   make dev-setup
   # or manually:
   pre-commit install
   ```

### Code Quality Tools

This project uses modern Python tooling for code quality:

- **Ruff** - Fast linter and formatter (replaces Black, isort, flake8)
- **mypy** - Static type checking
- **pytest** - Testing framework

### Development Workflow

#### Using Make (Recommended)

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

#### Manual Commands

```bash
# Format code
ruff format .

# Lint and auto-fix
ruff check --fix .

# Check linting without fixing
ruff check .

# Type checking
mypy --ignore-missing-imports bmad/

# Run tests
pytest tests/
```

### Pre-commit Hooks

Pre-commit hooks automatically run quality checks before each commit. Install with:

```bash
pre-commit install
```

To run hooks manually on all files:

```bash
pre-commit run --all-files
```

### Code Style

- Line length: 88 characters
- Quote style: Double quotes
- Python version: 3.11+
- Type hints encouraged but not required

The project configuration in `pyproject.toml` enforces:
- PEP 8 compliance
- Import sorting
- Security best practices (Bandit rules)
- Common bug patterns (Bugbear rules)
- Code simplifications
- Modern Python syntax (pyupgrade)

## Pull Requests

When submitting a pull request, please ensure that you have followed the BMad Method and that your changes are consistent with the project's architecture and conventions. The pull request template will guide you through the process of submitting a pull request.

## Issues

When submitting an issue, please provide as much detail as possible. The issue template will guide you through the process of submitting an issue.
