---
title: 'MCP Tool Scaffold Pattern'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.68
  stage: growing
  synapse_in: 4
  synapse_out: 6
---
# MCP Tool Scaffold Pattern

**Validated**: Session 53 (Kyutai Pocket TTS)
**Cost**: ~500 tokens to apply
**ROI**: 90% token savings vs test-first approach
**Files**: pocket_tts.py (126L), test_pocket_tts.py (222L), server.py (+19L)

## Pattern Structure

```
1. Service Class (Lazy Init + Validation)
   ├── __init__(): Initialize placeholders
   ├── initialize(): Load model on first use
   ├── public_method(): Validate input → call → return dict
   └── Error handling: Return error dict (never raise)

2. MCP Tool Registration
   ├── @mcp.tool()
   ├── Docstring: Args + Returns + Format
   ├── Call service.method()
   ├── Return json.dumps(result, indent=2)
   └── Optional import pattern (try/except)

3. Tests (After Confirmation)
   ├── Mock external deps (TTSModel, torchaudio)
   ├── Unit tests: validation, errors, init
   ├── Integration tests: MCP call + JSON return
   └── All 11 tests passing (1.62s total)
```

## Code Template

### Service Class
```python
# src/mcp_server/my_service.py
import logging
from typing import Any

logger = logging.getLogger(__name__)

class MyService:
    def __init__(self):
        self.model = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        try:
            # Load heavy model/resource
            self.model = SomeModel.load()
            self._initialized = True
        except ImportError as e:
            raise RuntimeError(f"Dependency missing: {e}") from e

    def do_work(self, input_data: str) -> dict[str, Any]:
        # Validate BEFORE init (cheap)
        if not input_data or not input_data.strip():
            return {"status": "error", "error": "Input cannot be empty"}

        # Initialize on first use
        if not self._initialized:
            try:
                self.initialize()
            except RuntimeError as e:
                return {"status": "error", "error": str(e)}

        # Do work
        try:
            result = self.model.process(input_data)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error("Work failed: %s", e)
            return {"status": "error", "error": str(e)}
```

### MCP Tool Registration
```python
# src/mcp_server/server.py
try:
    from .my_service import MyService

    my_service = MyService()

    @mcp.tool()
    def my_tool(input_data: str) -> str:
        """Do work on input data.

        Args:
            input_data: String input (max 4096 chars)

        Returns:
            JSON with status, result/error, and metadata.
        """
        result = my_service.do_work(input_data)
        return json.dumps(result, indent=2)

except ImportError:
    logger.warning("MyService not available (pip install my-service)")
```

### Test Template
```python
# tests/test_my_service.py
@patch("my_module.SomeModel")
def test_do_work_success(mock_model_class):
    """Test successful work."""
    mock_model = MagicMock()
    mock_model.process.return_value = "output"
    mock_model_class.load.return_value = mock_model

    service = MyService()
    result = service.do_work("input")

    assert result["status"] == "success"
    assert result["result"] == "output"

def test_do_work_empty_input():
    """Test validation (no mock needed)."""
    service = MyService()
    result = service.do_work("")

    assert result["status"] == "error"
    assert "empty" in result["error"].lower()

@pytest.mark.asyncio
async def test_mcp_tool():
    """Test MCP integration."""
    # Create server, call tool, verify JSON
    mcp = create_server(config)
    result_content, _ = await mcp.call_tool("my_tool", {"input_data": "test"})
    result = json.loads(result_content[0].text)

    assert result["status"] in ["success", "error"]
```

## Application Checklist

- [ ] Create service class with lazy init + validation
- [ ] Validate input BEFORE model loading (cheap checks first)
- [ ] Return dict from all methods (never raise to MCP layer)
- [ ] Register tool with docstring (Args + Returns)
- [ ] Optional import pattern (try/except)
- [ ] Write 11 tests: 9 unit + 2 integration
- [ ] Mock external deps (no real model downloads)
- [ ] Async tests for MCP integration
- [ ] Result unpacking: `result_content[0].text`

## Token Savings

**Cost to apply**: ~500 tokens (copy template)
**vs. Test-first**: ~61,000 tokens (Session 52 failed attempt)
**Savings**: 99% for minimal features

## Files to Review

- `cloud-vault-mcp/src/mcp_server/pocket_tts.py` (worked example)
- `cloud-vault-mcp/tests/test_pocket_tts.py` (test pattern)
- `cloud-vault-mcp/src/mcp_server/server.py` (registration pattern)

## Next Patterns

- Service Class Pattern (vault_ops, ollama_client)
- Test Mocking Pattern (FastMCP, external services)

## Related

- [[2026-02-10-claude-log-mining-architecture]]
- [[2026-02-12-prime-skill-pattern-as-governance-framework]]
- [[2026-02-10-phase-7-executor-pattern-launch]]
- [[claude-code-swiftui-skill-patterns]]
- [[ADOPTION_CHECKLIST]] — team checklist that references and operationalizes this MCP tool scaffold pattern
- [[test-mocking-pattern]] — the mocking strategy for testing services built with this scaffold
