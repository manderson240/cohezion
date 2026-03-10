## Update: New Rules Discovered (2026-03-09)

### Simplified Module Patterns

**Plugin Architecture (New Pattern):**
- Accept optional dependencies as constructor parameters, not god objects
- Maximum 4 constructor parameters for core classes
- Use dependency injection for analyzers, persisters, and plugins

```python
# CORRECT: Clean plugin architecture
def __init__(
    self,
    execute_fn: Callable,
    config: ExecutionConfig | None = None,
    analyzer: Callable | None = None,
    persister: Callable | None = None,
):

# WRONG: God object with 15+ dependencies
# (old CompoundExecutor had 15 optional parameters)
```

**Unified Data Models (New Pattern):**
- Consolidate scattered dataclasses into single models.py
- Use type aliases for cleaner code: `TaskId = str`, `SessionId = str`
- All core types in one location for consistency

**Backward Compatibility (Required):**
- Create compat.py module when refactoring
- Preserve old API while introducing new implementation
- Archive old code before deletion (cohezion-archive/)

### Test Patterns Discovered

**Async Test Patterns:**
- Always use `@pytest.mark.asyncio()` decorator
- Mock async executors properly:

```python
# CORRECT: Mock returns ExecutionResult
def mock_executor(task, context):
    return ExecutionResult(success=True, output="done")

# WRONG: Mock returns tuple
def mock_executor(task, context):
    return ("output", {"tokens": 100})  # This fails!
```

**Test Boundaries (Critical):**
- Duration threshold: 80% of timeout triggers degradation
- Coherence threshold: 0.5 minimum for quality passes
- Token limit: 100,000+ triggers anomaly detection

### Code Reduction Rules

**When Simplifying Code:**
1. Archive first (never delete immediately)
2. Mine for critical components
3. Create unified replacement
4. Add compatibility layer
5. Validate with tests (aim for 100% pass rate)
6. Document in context

**Target Metrics:**
- Minimum 60% code reduction for legacy modules
- Maintain 99%+ test pass rate
- Zero breaking changes (compat layer)

### Batch Processing Rules

**BatchConfig Standards:**
- `max_batch_size`: 10 (hard limit)
- `optimal_batch_size`: 5 (trigger threshold)
- `max_concurrent`: 4 (semaphore limit)
- Always use semaphore for concurrency control

**BatchResult Requirements:**
- Calculate `success_rate` as successful/total
- Track `failed_tasks` separately from results
- Support mixed success/failure in single batch

### Analytics Engine Rules

**Analysis Priority Order:**
1. Quality check (coherence, quality_score)
2. Degradation check (duration vs timeout)
3. Anomaly detection (tokens, errors)
4. Retry recommendation

**Suggested Actions:**
- Quality issue: `"retry_with_quality_improvement"`
- Degradation: `"retry_with_optimization"`
- Anomaly: `"retry_with_monitoring"`
- None: `"retry_standard"`

### Testing Workflow Rules

**BMAD TEA Workflow Integration:**
- Use step-file architecture for disciplined execution
- Always save progress after each step
- Update frontmatter: `stepsCompleted`, `lastStep`, `lastSaved`
- Never skip steps or proceed without user confirmation

**Test Generation Priority:**
- P0: Core execution paths (BatchProcessor, ExecutionAnalyzer)
- P1: Supporting components (SkillSelector, SessionPersister)
- P2: Infrastructure (MCP manager, Security pipeline)

### Documentation Standards

**Project Context Maintenance:**
- Update date when adding new rules
- Increment `existing_patterns_found` count
- Group related rules under clear headers
- Include code examples for every rule

---

**Status:** Project context updated with new patterns from elegant simplification work.