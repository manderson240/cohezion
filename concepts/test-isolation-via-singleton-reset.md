---
title: Test Isolation via Singleton Reset
date: 2026-02-23
tags: [testing, singleton, pattern]
status: stub
---

# Test Isolation via Singleton Reset

Pattern for isolating tests that use singletons: reset the singleton instance between tests to prevent state leakage.

## Pattern
```python
@pytest.fixture(autouse=True)
def reset_singleton():
    MySingleton._instance = None
    yield
    MySingleton._instance = None
```

## Related
- [[lesson-32-concurrent-pytest-contention]]
- [[lesson-38-singleton-executor-for-sessions-new]]
