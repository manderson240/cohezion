---
title: 'Test Mocking Pattern - External Services & FastMCP'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.76
  stage: growing
  synapse_in: 3
  synapse_out: 6
---
# Test Mocking Pattern - External Services & FastMCP

**Validated**: Session 53 (Pocket TTS, FastMCP integration)
**Cost**: ~200 tokens to apply
**ROI**: Fast tests (1.6s vs 5m+ with real models), reliable CI
**Files**: test_pocket_tts.py, test_*_integration.py

## Pattern Structure

```
Mocking Strategy
├── Unit tests: Mock at import (patch("module.Class"))
├── Integration tests: Mock only externals (FastMCP calls work)
├── Async tests: @pytest.mark.asyncio
├── Result unpacking: Handle tuple returns from async calls
└── Fixtures: Reset singletons between tests
```

## Code Template

### Mock External Service (Unit Tests)
```python
# tests/test_my_service.py
from unittest.mock import patch, MagicMock
import pytest

@patch("my_module.ExternalModel")  # Patch at import point
def test_service_success(mock_model_class):
    """Test service with mocked external dependency."""
    # Setup mock
    mock_model = MagicMock()
    mock_model.process.return_value = "output"
    mock_model_class.load.return_value = mock_model

    # Use service
    from my_module import MyService
    service = MyService()
    result = service.do_work("input")

    # Verify
    assert result["status"] == "success"
    mock_model.process.assert_called_once_with("input")

@patch("external_lib.SomeModel")
def test_service_error(mock_model_class):
    """Test error handling."""
    mock_model_class.load.side_effect = RuntimeError("CUDA OOM")

    from my_module import MyService
    service = MyService()
    result = service.do_work("input")

    assert result["status"] == "error"
    assert "CUDA OOM" in result["error"]
```

### Mock at Import Point (Critical!)
```python
# CORRECT: Patch where it's imported, not where it's defined
@patch("my_module.ExternalModel")  # ✅ Patch in my_module
def test_correct(mock_class):
    pass

# WRONG: Patch where it's defined (won't work)
@patch("external_lib.ExternalModel")  # ❌ Won't affect my_module
def test_wrong(mock_class):
    pass

# Why: my_module does `from external_lib import ExternalModel`
# So the reference is in my_module's namespace
```

### Mock Torch/NumPy Tensors
```python
import torch
from unittest.mock import MagicMock, patch

@patch("torchaudio.save")
@patch("pocket_tts.TTSModel")
def test_with_torch(mock_tts_class, mock_save):
    """Test with mocked audio output."""
    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock_model.sample_rate = 24000
    mock_model.generate_audio.return_value = torch.zeros(24000)  # Real tensor!
    mock_tts_class.load.return_value = mock_model

    # torchaudio.save is mocked, so no real file I/O
    service = MyService()
    result = service.speak("hello")

    assert result["status"] == "success"
    assert mock_save.called
```

### Async Integration Tests (FastMCP)
```python
# tests/test_mcp_integration.py
@pytest.mark.asyncio
async def test_mcp_tool_with_mock():
    """Test MCP tool with mocked service."""
    from mcp_server.server import create_server
    from mcp_server.config import ServerConfig
    from pathlib import Path
    from unittest.mock import patch

    with patch("mcp_server.my_service.MyService") as mock_class:
        mock_service = MagicMock()
        mock_service.do_work.return_value = {
            "status": "success",
            "result": "output"
        }
        mock_class.return_value = mock_service

        # Create MCP server
        config = ServerConfig(
            vault_path=str(Path.home() / "vaults" / "cohezion-vault"),
            watcher_enabled=False
        )
        mcp = create_server(config)

        # Call tool
        result_content, result_dict = await mcp.call_tool(
            "my_tool",
            {"input_data": "test"}
        )

        # Unpack result (FastMCP returns tuple)
        result_text = result_content[0].text
        result_data = json.loads(result_text)

        assert result_data["status"] == "success"
        mock_service.do_work.assert_called_once()
```

### Singleton Reset in Fixture
```python
# tests/conftest.py
import pytest

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before and after each test."""
    # Reset before test
    from my_module import reset_my_service
    reset_my_service()

    yield  # Run test

    # Reset after test
    reset_my_service()
    # Also clear logging handlers
    import logging
    logging.getLogger().handlers.clear()
```

## Common Patterns

### Mock Function Return Values
```python
mock_func.return_value = {"key": "value"}
mock_func.side_effect = RuntimeError("error")
mock_func.side_effect = [1, 2, 3]  # Multiple calls
```

### Assert Mock Was Called
```python
mock_func.assert_called_once()
mock_func.assert_called_with("arg1", "arg2")
mock_func.assert_not_called()
assert mock_func.call_count == 5
```

### Mock Object Attributes
```python
mock_obj = MagicMock()
mock_obj.attr = "value"
mock_obj.method.return_value = "result"

# Access chain
mock_obj.nested.method.return_value = "deep"
```

## FastMCP Result Unpacking

```python
# FastMCP returns (content_list, metadata_dict)
result_content, result_dict = await mcp.call_tool("tool_name", {"arg": "val"})

# result_content is list of TextContent objects
result_text = result_content[0].text  # Get first item's text

# Parse JSON
import json
result_data = json.loads(result_text)
assert result_data["status"] == "success"
```

## Application Checklist

- [ ] Identify external dependencies (models, APIs, files)
- [ ] Mock at import point, not definition
- [ ] Use MagicMock for object mocks, patch() for import mocks
- [ ] Set return_value or side_effect for mock behavior
- [ ] Use real tensors (torch.zeros) not mock tensors
- [ ] @pytest.mark.asyncio for async tests
- [ ] Unpack FastMCP results: result_content[0].text
- [ ] Reset singletons in autouse fixture
- [ ] Assert mock calls to verify behavior

## Files to Review

- `cloud-vault-mcp/tests/test_pocket_tts.py` (worked example: 11 tests)
- `src/cohezion/tests/test_*.py` (compound executor mocking patterns)

## Execution Time Comparison

| Approach | Time | Token Cost |
|----------|------|-----------|
| Real model | 5+ min | ∞ (model download) |
| Mocked model | 1.6s | ~100 (test setup) |
| Savings | 99.5% | 99% |

---

**Pattern validated**: Session 53 delivered 11 passing tests in 1.62s with full coverage

## Related

- [[2026-02-10-claude-log-mining-architecture]]
- [[2026-02-12-prime-skill-pattern-as-governance-framework]]
- [[2026-02-10-phase-7-executor-pattern-launch]]
- [[service-class-singleton-pattern]]
- [[concept-testing]] — analogous quality validation methodology for knowledge concepts; both ensure correctness before integration
- [[mcp-tool-scaffold-pattern]] — the MCP tool pattern whose test strategy this mocking pattern supports
