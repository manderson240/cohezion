---
name: cohezion-test
description: Run Cohezion tests with the correct patterns. Use when asked to run tests, verify changes, check coverage, or debug test failures. Includes singleton reset, mock-at-source, and isolation patterns.
---

# Cohezion Test Runner

## Quick Commands

```bash
# Full test suite (~90s)
uv run pytest tests/ -q

# Fast unit tests only
uv run pytest tests/ -q -m fast

# Single module
uv run pytest tests/compound/ -v

# Single test
uv run pytest tests/test_file.py::TestClassName::test_name -v

# With coverage
uv run pytest tests/ -q --cov=cohezion --cov-report=html

# Compound loop validation (23 checks, ~18s)
make validate
```

## Critical Test Patterns

### Singleton Reset (conftest.py)
When tests pass individually but fail in suite, reset singletons:
```python
cohezion.api._vae_trainer = None
cohezion.api._rl_policy = None
logging.getLogger().handlers.clear()
```

### Mock at Source (NOT after import)
```python
# CORRECT
@patch("cohezion.swarm.compound_client.get_compound_client")

# WRONG
with patch("cohezion.api.compound_client"):
```

### Pytest Markers
- `@pytest.mark.fast` — Unit tests under 1s, no live services
- `@pytest.mark.integration` — Requires Ollama/SurrealDB
- `@pytest.mark.mcp` — Requires vault access

## Known Issues
- 1 failing test: `test_jepa_world_model.py::TestTraining::test_training_updates_metrics`
- FLUME VAE + RL policy must be reset between test modules (conftest.py handles this)

## Anti-Patterns
- NEVER use `walk_packages` for test discovery — too slow
- NEVER mock after import — mock at the source module
- NEVER write 600 pre-implementation tests — implement ONE feature, validate, write 5 tests