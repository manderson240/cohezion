---
title: 'Quick Start: Build MCP Tool in 2 Hours'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.74
  stage: growing
  synapse_in: 7
  synapse_out: 7
---
# Quick Start: Build MCP Tool in 2 Hours

**Goal**: Use MCP Tool Scaffold pattern to add new tool
**Time**: 2 hours
**Tokens**: ~2.5K
**Tests**: 11 passing, 1.62s

## 5-Step Checklist

### Step 1: Copy Service Class Template (30 min)
```bash
# Create src/mcp_server/my_service.py
# Copy from: patterns/mcp-tool-scaffold-pattern.md → "Service Class" section
# Change: class name, method names, business logic
# Keep: lazy init structure, validation first, error dicts
```

**Checklist:**
- [ ] Service.__init__() initializes placeholders
- [ ] initialize() loads resources on first use
- [ ] do_work() validates input BEFORE initialization
- [ ] All methods return dict (never raise exceptions)
- [ ] Logging with logger.info/error

### Step 2: Register MCP Tool (10 min)
```bash
# Add to src/mcp_server/server.py (around line 730)
# Copy from: patterns/mcp-tool-scaffold-pattern.md → "MCP Tool Registration" section
# Change: service name, tool name, docstring
# Keep: @mcp.tool() decorator, JSON return, try/except import
```

**Checklist:**
- [ ] Tool function decorated with @mcp.tool()
- [ ] Docstring explains Args and Returns
- [ ] Calls service.method() and returns json.dumps()
- [ ] Optional import pattern (try/except)

### Step 3: Add Dependencies (5 min)
```bash
# Update cloud-vault-mcp/pyproject.toml
# Add to [project.dependencies] section
# Example: "my-lib>=1.0.0"
# Then: uv sync
```

**Checklist:**
- [ ] New dependencies added to pyproject.toml
- [ ] uv sync succeeds
- [ ] No version conflicts

### Step 4: Manual Validation (30 min)
```bash
# Run the simplest possible test first
uv run python -c "
from mcp_server.my_service import MyService
service = MyService()

# Test validation (no model loading)
result = service.do_work('')
assert result['status'] == 'error'
print('✓ Validation works')
"
```

**Checklist:**
- [ ] Import succeeds
- [ ] Input validation works
- [ ] Error handling works (no crashes)
- [ ] Tool appears in server (38+ tools total)

### Step 5: Write Real Tests (45 min)
```bash
# Create tests/test_my_service.py
# Copy from: patterns/mcp-tool-scaffold-pattern.md → "Test Template" section
# Change: class names, mock targets, assertions
# Keep: @patch() order, @pytest.mark.asyncio, result unpacking
```

Run tests:
```bash
uv run pytest tests/test_my_service.py -v --no-cov
# Expected: 11/11 passing in <2s
```

**Checklist:**
- [ ] 9 unit tests written (validation, errors, lazy init)
- [ ] 2 integration tests written (MCP tool calls)
- [ ] All tests passing
- [ ] Execution time <2s

---

## Common Mistakes (Avoid These!)

❌ **Mistake 1**: Initialize model in __init__
```python
# WRONG
def __init__(self):
    self.model = SomeModel.load()  # Blocks startup!
```
✅ **Fix**: Load in initialize() on first use
```python
# RIGHT
def initialize(self):
    if self._initialized:
        return
    self.model = SomeModel.load()
```

---

❌ **Mistake 2**: Validate AFTER initialization
```python
# WRONG - wastes time loading model for invalid input
def do_work(self, data):
    if not self._initialized:
        self.initialize()  # Don't do this yet!
    if not data:
        raise ValueError("empty")
```
✅ **Fix**: Validate BEFORE initialization
```python
# RIGHT - quick check first
def do_work(self, data):
    if not data:
        return {"status": "error", "error": "empty"}
    if not self._initialized:
        self.initialize()
```

---

❌ **Mistake 3**: Raising exceptions instead of error dicts
```python
# WRONG - MCP layer crashes
def do_work(self, data):
    raise ValueError("something broke")
```
✅ **Fix**: Return error dict
```python
# RIGHT - MCP tool returns JSON with error
def do_work(self, data):
    return {"status": "error", "error": "something broke"}
```

---

❌ **Mistake 4**: Mocking wrong import location
```python
# WRONG - won't affect my_service.py namespace
@patch("external_lib.MyModel")
def test_wrong(mock_class):
    pass
```
✅ **Fix**: Mock where it's imported
```python
# RIGHT - patches my_service.py namespace
@patch("my_service.MyModel")
def test_right(mock_class):
    pass
```

---

## Validation Checklist (Before Committing)

- [ ] All 11 tests passing in <2s
- [ ] No import errors (run: `uv run python -c "from mcp_server.my_service import MyService"`)
- [ ] Tool registered (38+ tools total in server)
- [ ] Manual validation passed (empty input rejected, etc.)
- [ ] Docstring explains Args/Returns
- [ ] Error handling: all paths return dict, never raise
- [ ] Logging: key operations logged
- [ ] No hardcoded paths or credentials

## Expected Output

```
Session XX: Add my_service MCP tool

- Implementation: 120-150 lines (service class)
- Tests: 11 passing (1.6s execution)
- Coverage: Validation, errors, lazy init, MCP integration
- Ready: Deployment ready as minimal feature

Token cost: ~2.5K
Savings vs test-first: 90%
```

## Next Feature After This?

Use EXACT same checklist. Time should be:
- Step 1: 20 min (pattern familiar now)
- Step 2: 5 min
- Step 3: 5 min
- Step 4: 20 min
- Step 5: 30 min
- **Total: 1.5 hours (vs 2 hours first time)**

Pattern reuse compounds: every feature gets faster.

---

## Reference Files

- **Worked example**: `cloud-vault-mcp/src/mcp_server/pocket_tts.py` (126L)
- **Test example**: `cloud-vault-mcp/tests/test_pocket_tts.py` (222L)
- **Pattern templates**: `/vaults/cohezion-vault/patterns/mcp-tool-scaffold-pattern.md`

---

**Pro tip**: Bookmark this guide. Copy it for every new MCP tool.

## Related

- [[claude-code-swiftui-skill-patterns]]
- [[transcranial-ultrasound-consciousness]]
- [[prime-skill-quick-reference]]
- [[mcp-tool-scaffold-pattern]]

## Related Decisions

- [[2026-02-09-session-43-mcp-setup|Decision: Session 43 MCP Server Setup & Obsidian Integration]] — established the MCP server infrastructure this pattern builds tools for
- [[2026-02-09-fastmcp-asgi-integration-fix|Decision: FastMCP ASGI Integration Fix]] — critical fix without which the tool registration step (Step 2) would fail
- [[2026-02-10-kyutai-pocket-tts-token-efficient-success|Decision: Kyutai Pocket TTS Token-Efficient Success]] — the worked example referenced in this pattern (pocket_tts.py)
