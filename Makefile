.PHONY: help format lint lint-check lint-tests type-check test test-fast all clean dev-setup ci health-check vault-status session-briefing nav

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

format:  ## Format code with ruff
	uv run ruff format .
	@echo "Code formatted"

lint:  ## Lint and auto-fix issues with ruff
	uv run ruff check --fix .
	@echo "Linting complete"

lint-check:  ## Check linting without fixing
	uv run ruff check .
	uv run ruff format --check .
	@echo "Lint check complete"

type-check:  ## Run type checking with mypy
	uv run mypy --ignore-missing-imports src/cohezion/ || true
	@echo "Type check complete"

test:  ## Run test suite
	uv run pytest tests/
	@echo "Tests complete"

test-fast:  ## Run only fast unit tests (quick feedback)
	uv run pytest -m fast --tb=short tests/
	@echo "Fast tests complete"

test-routing:  ## Run smart routing optimization tests
	uv run pytest tests/swarm/ tests/benchmarks/test_routing_performance.py -v --tb=short
	@echo "Routing tests complete"

test-routing-unit:  ## Run routing unit tests only
	uv run pytest tests/swarm/test_hardware_profiler.py tests/swarm/test_batch_optimizer.py tests/swarm/test_hardware_aware_router.py -v
	@echo "Routing unit tests complete"

test-routing-integration:  ## Run routing integration tests
	uv run pytest tests/swarm/test_routing_integration.py -v
	@echo "Routing integration tests complete"

test-routing-benchmarks:  ## Run routing performance benchmarks
	uv run pytest tests/benchmarks/test_routing_performance.py -v
	@echo "Routing benchmarks complete"

lint-tests:  ## Lint test files for anti-patterns (hardcoded paths, GPG signing, etc.)
	uv run python scripts/ci/lint_tests.py
	@echo "Test lint complete"

all: format lint lint-tests type-check test  ## Run all checks and tests

clean:  ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cache cleaned"

dev-setup:  ## Install dev dependencies and pre-commit hooks
	uv pip install pre-commit
	uv run pre-commit install
	@echo "Pre-commit hooks installed"

ci:  ## Run CI checks locally (fast linters + tests)
	@echo "Running CI checks..."
	uv run python scripts/ci/lint_tests.py
	uv run pre-commit run --all-files
	uv run pytest tests/
	@echo "All CI checks passed"

health-check:  ## Run project health checks
	@echo "Running health checks..."
	@uv run python -c "from cohezion.compound import CompoundExecutor; print('Compound: OK')" 2>/dev/null || echo "Compound: import issue"
	@uv run python -c "from cohezion.swarm import TeamOrchestrator; print('Swarm: OK')" 2>/dev/null || echo "Swarm: import issue"
	@uv run python -c "from cohezion.cache import SemanticCache; print('Cache: OK')" 2>/dev/null || echo "Cache: import issue"
	@echo "Health check complete"

vault-status:  ## Check MCP vault connectivity
	@echo "Checking MCP vault connectivity..."
	@if curl -s http://localhost:8360/mcp >/dev/null 2>&1; then echo "Vault MCP endpoint: Connected"; else echo "Vault MCP endpoint: Disconnected"; fi
	@if [ -d ~/vaults/cohezion-vault ]; then echo "Vault directory: Found"; else echo "Vault directory: Not found"; fi

session-briefing:  ## Generate session context and prepare environment
	@echo "Generating session briefing..."
	@if [ -f scripts/claude/session_start.sh ]; then bash scripts/claude/session_start.sh; else echo "Note: session_start.sh not found"; fi
	@echo "Session briefing complete"

nav:  ## Interactive codebase navigator (symbol lookup)
	@echo "Launching codebase navigator..."
	@if [ -f scripts/claude/nav_utils.py ]; then uv run python scripts/claude/nav_utils.py; else echo "Note: nav_utils.py not found"; fi
