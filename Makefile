.PHONY: setup test lint demo serve clean format check rust

# Setup: install dependencies
setup:
	uv sync --dev

# Run all tests
test:
	uv run pytest tests/ -v --tb=short

# Run unit tests only
test-unit:
	uv run pytest tests/unit/ -v --tb=short

# Lint check
lint:
	uv run ruff check src/cohezion/
	uv run ruff format --check src/cohezion/

# Auto-fix linting issues
format:
	uv run ruff check --fix src/cohezion/
	uv run ruff format src/cohezion/

# Full pre-commit check
check: lint test-unit

# Run the 30-second demo
demo:
	uv run python scripts/demo.py

# Start the API server
serve:
	uv run uvicorn cohezion.api:app --reload --port 8080

# Build Rust extension
rust:
	cd src/cohezion_core && maturin develop --release

# Train FLUME VAE (synthetic data, quick)
train-flume:
	uv run python scripts/train_flume.py --synthetic --epochs 20

# Run mass simulation (demo scale)
mass-sim:
	uv run python mass_sim_driver.py --scale demo

# Clean generated artifacts
clean:
	rm -rf data/flume/checkpoints/ data/rl/checkpoints/ renders/ /tmp/demo_flume/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
