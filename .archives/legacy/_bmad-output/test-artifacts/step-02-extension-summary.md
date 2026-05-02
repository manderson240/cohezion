---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-identify-targets-extension']
lastStep: 'step-02-identify-targets-extension'
lastSaved: '2026-03-09'
inputDocuments:
  - Previous: tests/compound/test_context_integration.py (14 tests, ✅ PASSED)
  - Current: tests/compound/test_executor_comprehensive.py (19 tests, ~84% passing)
  - New simplified modules identified
---

# Step 2: Identify Targets - EXTENSION

## Previous Work Summary (2026-03-08)

**Completed:**
- ✅ `test_context_integration.py` - 14 tests, all passing
- Context manager, ContextCoherenceError, CompoundContextMixin

## Current State Analysis

### Test File Count by Module

| Module | Test Files | Status |
|--------|-----------|--------|
| compound | 45 files | Testing OLD implementation |
| api | ~15 files | Limited coverage |
| security | ~12 files | Partial coverage |
| swarm | ~10 files | Limited coverage |

### Simplified Modules - Coverage Gap Identified

| Simplified Module | Lines | Has Tests? | Priority |
|------------------|-------|-----------|----------|
| compound/core/executor.py | ~200 | ✅ test_executor_comprehensive.py | P1 |
| compound/core/batch_processor.py | ~200 | ❌ **NO TESTS** | **P0** |
| compound/analytics/engine.py | ~200 | ❌ **NO TESTS** | **P0** |
| compound/analytics/metrics.py | ~150 | ❌ **NO TESTS** | **P0** |
| compound/skills/selector.py | ~150 | ❌ **NO TESTS** | **P1** |
| compound/persistence/vault.py | ~150 | ❌ **NO TESTS** | **P1** |
| swarm/orchestrator.py | ~150 | ❌ **NO TESTS** | **P1** |
| mcp/manager.py | ~200 | ❌ **NO TESTS** | **P1** |
| security/pipeline.py | ~200 | ❌ **NO TESTS** | **P1** |

## Extension Targets

### Primary (P0 - Critical Gap)
1. **BatchProcessor** - Core execution flow
2. **ExecutionAnalyzer** - Analytics engine
3. **MetricsCollector** - Metrics collection

### Secondary (P1 - Important)
4. **SkillSelector** - Skill selection logic
5. **SessionPersister** - Persistence layer
6. **Swarm orchestrator** - Agent coordination

### Tertiary (P2 - Medium)
7. **MCP manager** - Server management
8. **Security pipeline** - Guardrails

## Test Level Assignment

All targets are **Unit/Integration tests** (backend stack):

- **Unit**: Pure logic functions, data transformations
- **Integration**: Component interaction, API contracts

## Priority Justification

**P0**: Core execution components - failures block all functionality
**P1**: Supporting components - failures impact specific features
**P2**: Infrastructure components - failures have workarounds

## Next Step

Generate tests for P0 targets:
1. BatchProcessor
2. ExecutionAnalyzer  
3. MetricsCollector

**Estimated Test Count**: 45-60 new tests
**Estimated Lines**: ~2,000-3,000 lines of test code
