---
title: 'Pattern Adoption Checklist - Team Use'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.8
  stage: growing
  synapse_in: 3
  synapse_out: 7
---
# Pattern Adoption Checklist - Team Use

**Purpose**: Ensure patterns are applied correctly across team
**Usage**: Copy checklist for each new feature
**ROI**: 80-90% token savings, 3x faster implementation

---

## Before Starting Feature

- [ ] Read: `/vaults/cohezion-vault/patterns/quick-start-mcp-tool.md`
- [ ] Identify which patterns apply (MCP tool? Service class? Persistence?)
- [ ] Estimated time: 2-4 hours (pattern-based)
- [ ] Estimated tokens: 2-4K (vs 10-15K without pattern)

---

## Pattern 1: Service Class + Singleton (All Services)

**Files to create/modify:**
- [ ] `src/mcp_server/my_service.py` — Service class
- [ ] `src/mcp_server/server.py` — Add get_my_service() + reset_my_service()
- [ ] `tests/conftest.py` — Add reset to fixture
- [ ] `tests/test_my_service.py` — Unit tests

**Validation:**
- [ ] `get_my_service()` creates instance once
- [ ] `reset_my_service()` clears singleton (testing)
- [ ] Non-blocking vault calls (try/except wrappers)
- [ ] Logging on init/key operations
- [ ] All methods return consistent types

**Reference**: `/vaults/cohezion-vault/patterns/service-class-singleton-pattern.md`

---

## Pattern 2: MCP Tool Scaffold (All MCP Tools)

**Files to create/modify:**
- [ ] `src/mcp_server/my_service.py` — Service class (Step 1)
- [ ] `src/mcp_server/server.py` — Tool registration (Step 2)
- [ ] `pyproject.toml` — Add dependencies (Step 3)
- [ ] `tests/test_my_service.py` — Write tests (Step 5)

**Validation:**
- [ ] Service validates input BEFORE initialization
- [ ] All methods return dict with "status" key
- [ ] Tool decorated with @mcp.tool()
- [ ] Docstring explains Args/Returns/Format
- [ ] Optional import pattern (try/except)
- [ ] 11 tests passing in <2s
- [ ] Manual validation passed

**Reference**: `/vaults/cohezion-vault/patterns/quick-start-mcp-tool.md`

---

## Pattern 3: Test Mocking (All Tests)

**Rules:**
- [ ] Mock at import point: `@patch("my_module.ExternalClass")`
- [ ] Use MagicMock for object mocks
- [ ] Use real tensors: `torch.zeros()` not mock
- [ ] @pytest.mark.asyncio for async tests
- [ ] Unpack FastMCP results: `result_content[0].text`
- [ ] Reset singletons in fixture (before/after each test)

**Validation:**
- [ ] Mocks work (no hanging on real models)
- [ ] Tests run <2s total
- [ ] All tests passing
- [ ] No real API calls during CI

**Reference**: `/vaults/cohezion-vault/patterns/test-mocking-pattern.md`

---

## Quality Gates (Before Commit)

### Code Quality
- [ ] Ruff format: `uv run ruff format src/mcp_server/`
- [ ] Ruff lint: `uv run ruff check src/mcp_server/`
- [ ] Type hints on public methods (mypy compatible)
- [ ] Docstrings: NumPy-style (Args, Returns, Raises)

### Testing
- [ ] 11/11 tests passing
- [ ] Execution time <2s
- [ ] Manual validation passed
- [ ] No import errors

### Documentation
- [ ] Docstring explains tool purpose
- [ ] Args/Returns documented
- [ ] Error cases documented
- [ ] Optional dependencies noted in docstring

### Git
- [ ] Create feature branch: `session-NN-feature-name`
- [ ] Atomic commit (test + code together)
- [ ] Commit message template:
  ```
  feat: Add my_service MCP tool

  - Implementation: 120L service class
  - Tests: 11 passing (1.6s)
  - Pattern: MCP Tool Scaffold
  - Tokens: ~2.5K | Savings: 90%
  ```

---

## Red Flags (Stop & Review)

🚩 **Test takes >5s** → Mocking not working, real model loading
🚩 **Implementation >300 lines** → Over-engineering, split into smaller features
🚩 **11+ tests failing** → Pattern not applied correctly
🚩 **Token estimate >5K** → Check if pattern exists
🚩 **Manual validation fails** → Validation logic broken

---

## Common Patterns by Feature Type

### Adding MCP Tool
1. Copy MCP Tool Scaffold pattern
2. Implement service class (30 min)
3. Register tool (10 min)
4. Write tests (45 min)
5. **Total: ~2 hours**

### Adding Service (No MCP Tool)
1. Copy Service Class pattern
2. Implement class (30 min)
3. Add singleton factory (10 min)
4. Write tests (30 min)
5. **Total: ~1.5 hours**

### Adding Persistence Layer
1. Copy Persistence pattern [TODO: extract Session 38-39]
2. Implement storage (45 min)
3. Add atomic writes (20 min)
4. Write tests (30 min)
5. **Total: ~2 hours**

---

## Success Metrics

✅ **First feature using pattern**: 2-3 hours, 2.5K tokens
✅ **Second feature**: 1.5-2 hours, 1.8K tokens (50% faster)
✅ **Third feature**: 1.5 hours, 1.5K tokens (3x faster than test-first)

**If feature still takes 4+ hours**: Pattern needs refinement, flag in retrospective

---

## Team Responsibilities

**Feature implementer:**
- [ ] Follow checklist exactly
- [ ] Time each step (compare to estimates)
- [ ] Flag deviations from pattern
- [ ] Commit with pattern name in message

**Code reviewer:**
- [ ] Verify pattern applied correctly
- [ ] Check quality gates passed
- [ ] Approve if checklist complete

**Pattern maintainer:**
- [ ] Collect feedback from implementations
- [ ] Update pattern if multiple teams struggle
- [ ] Version pattern updates in vault

---

## Quick Links

- **Quick Start Guide**: `quick-start-mcp-tool.md`
- **MCP Tool Pattern**: `mcp-tool-scaffold-pattern.md`
- **Service Pattern**: `service-class-singleton-pattern.md`
- **Test Mocking Pattern**: `test-mocking-pattern.md`
- **Vault Patterns**: `/vaults/cohezion-vault/patterns/`

---

**Last Updated**: Session 53 (2026-02-10)
**Validated by**: Session 53 Kyutai Pocket TTS (11 tests, 1.62s, 90% savings)

## Related

- [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced]]
- [[2026-02-13-phase-2-execution-strategy-wave-2]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-14-compound-engineering-team-execution-retrospective]]
- [[token-efficiency-patterns]] — quantifies the token savings this checklist is designed to achieve (80-90% reduction)
- [[mcp-tool-scaffold-pattern]] — the primary MCP tool pattern this checklist references and operationalizes
- [[concept-testing]] — analogous quality-gate methodology applied to knowledge concepts rather than code
