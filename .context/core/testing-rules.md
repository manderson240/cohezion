---
title: Testing Rules
description: Testing patterns and requirements for Cohezion
created: 2026-03-08
traced_from:
  - source: AGENTS.md
    section: Testing Guidelines
    commit: d2f7129f
  - source: AGENTS.md
    section: Test Isolation
    commit: d2f7129f
  - source: compound-engineering/skill
    section: Common Issues
    commit: 810f2e10
coherence_threshold: 0.5
---

# Core Testing Rules

## Test Markers
- `@pytest.mark.fast` - Unit tests under 1s, no live services
- `@pytest.mark.integration` - Requires Ollama/SurrealDB
- `@pytest.mark.mcp` - Requires vault access

## Test Isolation (Critical)
**Always mock external services at the source level:**

```python
# CORRECT: Mock at source
@patch("cohezion.swarm.compound_client.get_compound_client")

# WRONG: Mock after import
with patch("cohezion.api.compound_client"):  # Import already happened
```

## Singleton Reset Pattern
When tests pass individually but fail in suite, reset singletons:

```python
# In conftest.py or test setup
cohezion.api._vae_trainer = None
cohezion.api._rl_policy = None
logging.getLogger().handlers.clear()
```

## Test Structure
```python
class TestMyFeature:
    @pytest.mark.fast
    @patch("cohezion.module.function_to_mock")
    async def test_something(self, mock_fn):
        mock_fn.return_value = "mocked"
        result = await function_under_test()
        assert result == expected
```

## Commands
```bash
make test-fast       # Fast unit tests only (<1s each)
make test            # Full test suite (~90s)
```

## FUTURE HOOKS
1. **Test parallelization**: Future test runner will auto-distribute by marker
2. **Mock verification**: Future CI will verify mocks are at source level
3. **Flaky test detection**: Future metrics will track and quarantine flaky tests
