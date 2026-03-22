.PHONY: help format lint lint-check type-check test all clean

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

format:  ## Format code with ruff
	ruff format .
	@echo "✓ Code formatted"

lint:  ## Lint and auto-fix issues with ruff
	ruff check --fix .
	@echo "✓ Linting complete"

lint-check:  ## Check linting without fixing
	ruff check .
	ruff format --check .
	@echo "✓ Lint check complete"

type-check:  ## Run type checking with mypy
	mypy --ignore-missing-imports bmad/ || true
	@echo "✓ Type check complete"

test:  ## Run test suite
	pytest tests/
	@echo "✓ Tests complete"

all: format lint type-check test  ## Run all checks and tests

clean:  ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cache cleaned"

# Development workflow targets
dev-setup:  ## Install pre-commit hooks
	pip install pre-commit
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

ci:  ## Run CI checks locally
	@echo "Running CI checks..."
	ruff format --check .
	ruff check .
	mypy --ignore-missing-imports bmad/ || true
	pytest tests/
	@echo "✓ All CI checks passed"
