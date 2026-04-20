---
title: 'Service Class & Singleton Factory Pattern'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.69
  stage: growing
  synapse_in: 12
  synapse_out: 7
---
# Service Class & Singleton Factory Pattern

**Validated**: Sessions 38-51 (VaultOps, OllamaClient, HealthChecker)
**Cost**: ~300 tokens to apply
**ROI**: Consistent API across all services, easy testing via reset
**Files**: vault_ops.py, ollama_client.py, health.py

## Pattern Structure

```
Service Class
├── __init__(): Initialize state
├── Public methods: Implement core functionality
├── Logging: Use logger.info/error for observability
└── Error handling: Raise specific exceptions OR return status dicts

Singleton Factory
├── get_service(): Create once, return cached instance
├── reset_service(): Clear cache (for testing)
└── Non-blocking observability: try/except wrappers
```

## Code Template

### Service Class
```python
# src/service_name.py
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MyService:
    """Service for doing work."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize with optional config."""
        self.config = config or {}
        self.state = None
        logger.info("MyService initialized")

    def do_something(self, input_data: str) -> str:
        """Do work and return result.

        Args:
            input_data: Input to process

        Returns:
            Result string

        Raises:
            ValueError: If input is invalid
        """
        if not input_data:
            raise ValueError("Input cannot be empty")

        result = self._process(input_data)
        logger.info("Processed: %s", len(input_data))
        return result

    def _process(self, data: str) -> str:
        """Internal processing."""
        return data.upper()

# Singleton factory
_my_service: Optional[MyService] = None

def get_my_service() -> MyService:
    """Get or create singleton instance."""
    global _my_service
    if _my_service is None:
        _my_service = MyService()
    return _my_service

def reset_my_service() -> None:
    """Reset singleton (for testing)."""
    global _my_service
    _my_service = None
```

### Non-Blocking Observability Pattern
```python
# Vault integration without blocking on failures
def save_to_vault(document: dict) -> None:
    """Non-blocking vault save."""
    try:
        vault.add_document(
            name=f"my-doc-{timestamp}",
            content=document,
            tags=["service", "log"]
        )
        logger.info("Saved to vault")
    except Exception as e:
        # Don't crash service if vault unavailable
        logger.warning("Vault save failed: %s", e)
        # Fall back to local persistence
        save_locally(document)
```

### Test Usage
```python
# tests/test_my_service.py
import pytest

def test_do_something():
    """Test service method."""
    service = get_my_service()
    result = service.do_something("input")
    assert result == "INPUT"

def test_invalid_input():
    """Test error handling."""
    service = get_my_service()
    with pytest.raises(ValueError, match="empty"):
        service.do_something("")

@pytest.fixture(autouse=True)
def reset_services():
    """Reset all singletons between tests."""
    yield
    reset_my_service()
```

## Application Checklist

- [ ] Service class with `__init__`, public methods, logging
- [ ] Specific exceptions (ValueError, RuntimeError, etc.)
- [ ] Logger calls for key operations
- [ ] Singleton factory: `get_*()` + `reset_*()`
- [ ] Non-blocking observability (try/except around vault calls)
- [ ] Docstrings: NumPy-style (Args, Returns, Raises)
- [ ] Tests use `reset_*()` in fixture
- [ ] Config passed to `__init__`, not hardcoded

## Common Mistakes to Avoid

❌ **Don't**: Global state without reset factory
✅ **Do**: get_service() + reset_service() for testing

❌ **Don't**: Raise exceptions from vault/persistence calls
✅ **Do**: try/except with logging fallback

❌ **Don't**: Logger without context (use %)
✅ **Do**: logger.info("Message: %s", var)

❌ **Don't**: Mix sync/async without clear API
✅ **Do**: All methods same paradigm (sync or async)

## Files to Review

- `cloud-vault-mcp/src/mcp_server/vault_ops.py` (read/write pattern)
- `cloud-vault-mcp/src/mcp_server/ollama_client.py` (external API pattern)
- `cloud-vault-mcp/src/mcp_server/health.py` (health check pattern)

## Variations

**Async Service**:
```python
async def do_something_async(self, input_data: str) -> str:
    result = await self._process_async(input_data)
    return result
```

**With Cleanup**:
```python
def __enter__(self):
    return self

def __exit__(self, *args):
    self.cleanup()
```

**Config from File**:
```python
def __init__(self, config_path: str = "config.json"):
    with open(config_path) as f:
        self.config = json.load(f)
```

## Related

- [[2026-02-10-claude-log-mining-architecture]]
- [[2026-02-12-prime-skill-pattern-as-governance-framework]]
- [[2026-02-10-phase-7-executor-pattern-launch]]
- [[compound-async-executor-pattern]]
- [[2026-02-17-singleton-consolidation-mandatory-during-file-splits]] — enforces that singletons are consolidated when the file containing this pattern is split
- [[async-singleton-lock-isolation]] — async-specific extension: asyncio primitives must be in __init__, not class-level

## Session References

- [[session-46-test-isolation-and-phase-2-security]] — singleton pattern used across security components; reset required for test isolation
