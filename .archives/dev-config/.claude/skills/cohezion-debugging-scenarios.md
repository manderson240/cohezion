---
name: cohezion-debugging-scenarios
description: Cohezion-specific debugging scenarios for test isolation, flaky tests, singleton pollution, Ollama timeouts, journey tracking issues, and token count mismatches. Use when debugging test failures, investigating flaky tests, or troubleshooting Cohezion infrastructure.
---

# Common Debugging Scenarios

### Scenario: Tests Pass Individually but Fail in Suite
**Root cause**: Singleton pollution in conftest.py fixtures
```bash
# Fix: Verify singleton reset is running
grep -n "_vae_trainer\|_rl_policy\|handlers.clear" tests/conftest.py

# Debug: Run single test module to verify
uv run pytest tests/compound/test_executor.py -v
# If passes → singleton issue
# If fails → logic bug
```

### Scenario: Flaky Test with Random Seed Issues
**Root cause**: FLUME VAE or numpy random state not reset
```python
# In your test:
import numpy as np
from cohezion.api import reset_flume_vae

@pytest.fixture(autouse=True)
def reset_random():
    np.random.seed(42)
    reset_flume_vae()
    yield
```

### Scenario: Ollama Timeout in Tests
**Root cause**: Test is hitting live Ollama instead of mock
```python
# Fix: Mock at source
@patch("cohezion.swarm.compound_client.get_compound_client")
def test_my_thing(mock_client):
    mock_client.return_value = AsyncMock()  # Never talks to real Ollama
```

### Scenario: Journey Tracking Missing from Logs
**Root cause**: Non-blocking try/except swallowed the error
```python
# Debug: Temporarily make it blocking
try:
    tracker.record_transition(...)
except Exception as e:
    logger.error(f"Journey tracking: {e}")  # See the actual error
    raise  # Temporarily, to find issue
```

### Scenario: Token Count Doesn't Match Estimate
**Root cause**: Cost tracker using wrong model rate
```python
# Verify cost is being computed
agg = GlobalMetricsAggregator()
metrics = agg.get_metrics_snapshot()

# Check: Are costs accumulating?
if metrics.total_cost_usd == 0.0:
    logger.warning("Cost tracking not working, check model rates in cost_aware_router.py")
```
