---
name: gen-test
description: Generate pytest test scaffolds for a Python module following Cohezion testing conventions. Reads the module, conftest.py, and existing test patterns to produce well-structured tests with proper mocking, fixtures, and priority markers.
arguments:
  - name: module_path
    description: Path to the Python module to generate tests for (e.g., src/cohezion/compound/executor.py)
    required: true
---

# Generate Tests for a Module

You are generating pytest tests for `$ARGUMENTS`. Follow these steps exactly.

## Step 1: Understand the Testing Infrastructure

Read `tests/conftest.py` to understand:
- Available fixtures (singleton resets, mock clients, test data)
- The `autouse` fixtures that run on every test (FLUME VAE reset, RL policy reset, logger cleanup)
- Any shared test utilities

## Step 2: Read the Target Module

Read the module at `$ARGUMENTS` and identify:
- All public functions and classes (skip `_private` methods)
- Constructor parameters and their types
- External dependencies (imports from other packages, HTTP calls, DB queries)
- Return types and possible exceptions

## Step 3: Find Similar Tests

Search for existing test files that test similar modules:
- Use Grep to find `test_<module_name>` or tests in the same package directory
- Study the mocking patterns, fixture usage, and assertion style
- Note which dependencies are mocked and HOW they are mocked

## Step 4: Generate Tests

Create a test file at `tests/<package_path>/test_<module_name>.py` with:

### File Structure
```python
"""Tests for <module_path>."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the module under test
from <module_import_path> import <ClassName or function_name>


class Test<ClassName>:
    """Tests for <ClassName>."""

    def test_<method>_happy_path_p0(self):
        """[P0] <method> returns expected result with valid input."""
        ...

    def test_<method>_error_handling_p1(self):
        """[P1] <method> handles <error_case> gracefully."""
        ...
```

### Rules

1. **5-10 tests maximum** — cover happy path, error cases, and 1-2 edge cases. Do not over-generate.

2. **Mock at source, not at import**:
   ```python
   # CORRECT: patch where the dependency is looked up
   @patch("cohezion.compound.executor.get_compound_client")

   # WRONG: patch where it was imported from
   @patch("cohezion.swarm.compound_client.get_compound_client")
   ```

3. **Priority markers**: Use `[P0]` for critical path tests, `[P1]` for error handling, `[P2]` for edge cases. Put the marker in the docstring.

4. **Pytest marks**:
   - `@pytest.mark.unit` for pure logic tests
   - `@pytest.mark.integration` for tests that touch external systems (even mocked)

5. **Async tests**: If the module has async functions, use `@pytest.mark.asyncio` and `async def test_...`

6. **Never mock what you own**: Test real internal logic. Only mock external boundaries (HTTP clients, DB connections, Ollama, file I/O to external paths).

7. **Fixture usage**: Use conftest.py fixtures where available. Create new fixtures only if they would be reused across 3+ tests.

8. **Assertions**: Use specific assertions (`assert result.status == "ok"`) not vague ones (`assert result is not None`).

9. **No hardcoded paths**: Use `tmp_path` fixture or `PROJECT_ROOT / "relative"` — never `/home/mike-anderson/...`

## Step 5: Run and Verify

After writing tests, run them:
```bash
uv run pytest tests/<path>/test_<module>.py -q
```

Fix any failures before marking complete. Tests must pass on first run.

## Anti-Patterns to Avoid

- Generating 50+ tests for a simple module (5-10 is the target)
- Testing private methods directly (test through public API)
- Mocking everything including the module under test
- Using `assert True` or `assert result` without checking specific values
- Copying test boilerplate without adapting to the actual module
- Writing tests that duplicate conftest.py fixture behavior
