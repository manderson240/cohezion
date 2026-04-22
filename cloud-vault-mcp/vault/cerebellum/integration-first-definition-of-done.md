---
title: 'Integration-First Definition of Done'
date: 2026-02-14
tags: [pattern, software-development-lifecycle]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 11
  synapse_out: 11
---
# Integration-First Definition of Done

**Category**: Software Development Lifecycle
**Domain**: Compound Engineering
**Created**: 2026-02-14
**Source**: Session 57 Track B Integration Gap

---

## Problem

**Track B orphaned code**: 1,494 LOC exists but is **unreachable** via production interface.

**Root cause**: Assumed "code written" = "integrated". Did not test end-to-end until adversarial review.

**Impact**:
- 10+ hours of implementation work
- ZERO production value (code cannot be called)
- Must spend 3-4 hours to wire integration
- Total waste: 30% of implementation time

**Evidence from Session 57**:
```python
# Code exists (entire_ops.py, sync_daemon.py, work_queue.py)
# BUT: No @mcp.tool() decorators
# RESULT: Claude Code cannot invoke Track B functionality
# STATUS: Orphaned (100% waste until integration added)
```

---

## Pattern: Integration-First Definition of Done

**Core Principle**: Feature is NOT complete until user can execute it end-to-end.

### Old Definition of Done (WRONG)

```
✅ Code written
✅ Unit tests passing
✅ Documentation complete
❌ Can user actually use it? (NOT CHECKED)
```

**Result**: Orphaned code, wasted effort, late integration issues

### New Definition of Done (CORRECT)

```
✅ Code written
✅ Unit tests passing
✅ Integration tests passing ← NEW
✅ End-to-end user flow tested ← NEW
✅ Documentation complete
✅ Feature callable via production interface ← NEW
```

**Result**: No orphaned code, production-ready at completion

---

## Integration Verification Checklist

**ALL must be YES before claiming "complete"**:

### 1. Production Interface Integration

**For MCP tools**:
- [ ] `@mcp.tool()` decorator present on all entry points
- [ ] Tool registered in `server.py` or `main.py`
- [ ] Tool appears in Claude Code tool list (`/tools`)
- [ ] Tool can be called via Claude Code chat

**For APIs**:
- [ ] Endpoint registered in FastAPI router
- [ ] Endpoint appears in `/docs` (Swagger UI)
- [ ] Endpoint callable via `curl` or Postman
- [ ] Endpoint returns expected response format

**For CLIs**:
- [ ] Command registered in argument parser
- [ ] Command appears in `--help` output
- [ ] Command can be invoked from terminal
- [ ] Command handles all flags and arguments

### 2. End-to-End Smoke Test

**Template**:
```python
@pytest.mark.integration
@pytest.mark.e2e
async def test_feature_end_to_end_user_flow():
    """
    End-to-end: User invokes feature via production interface
    and gets expected result.
    
    This test uses REAL services (not mocks) to verify full integration.
    """
    # Step 1: User invokes feature (via MCP/API/CLI)
    result = await production_interface.invoke_feature(user_input)
    
    # Step 2: Feature executes with real dependencies
    # (database, external API, file system, etc.)
    
    # Step 3: User receives expected result
    assert result.success
    assert result.data == expected_output
    
    # Step 4: Side effects persisted correctly
    assert real_service.get(result.id) is not None
```

### 3. Integration Test with Real Services

**Each dependency requires integration test**:

```python
@pytest.mark.integration
async def test_feature_with_real_database():
    """Integration: Feature works with REAL database (not mock)."""
    # Use real database connection (not mock)
    result = await feature.save_to_database(data)
    
    # Verify: Data actually persisted
    retrieved = await database.get(result.id)
    assert retrieved.data == data

@pytest.mark.integration
async def test_feature_with_real_api():
    """Integration: Feature works with REAL external API (not mock)."""
    # Use real API client (not mock)
    result = await feature.call_external_api(request)
    
    # Verify: Got real response (not mocked data)
    assert result.from_real_api
    assert result.status_code == 200
```

### 4. No Orphaned Code

**Verification questions**:
1. Can this code be reached from user entry point? (trace call path)
2. Is there a path from `main()` or MCP tool to this code?
3. Can I invoke this code WITHOUT modifying production interface?

**How to verify**:
```python
# Method 1: Call graph analysis
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

with PyCallGraph(output=GraphvizOutput()):
    # Invoke user entry point
    production_interface.invoke_feature()

# Result: Verify your code appears in call graph

# Method 2: Coverage with integration tests
pytest --cov=your_module --cov-report=html tests/integration/

# Result: Verify >80% coverage from integration tests alone
```

### 5. Cross-System Tests

**For multi-system features** (Track A + Track B + Track C):

```python
@pytest.mark.integration
async def test_track_a_integrates_with_track_b():
    """Cross-system: Track A can invoke Track B functionality."""
    # Track A code calls Track B
    result = await track_a.use_track_b_feature(input)
    
    # Verify: Track B executed correctly
    assert result.from_track_b
    assert track_b_state.updated

@pytest.mark.integration
async def test_full_system_integration():
    """Cross-system: All tracks work together end-to-end."""
    # User action triggers Track A
    result = await user_action()
    
    # Track A uses Track B (sync daemon)
    assert result.track_b_checkpoint_created
    
    # Track B updates Track C (vault)
    assert vault.read("checkpoint.md") is not None
```

---

## Implementation Workflow

### Step-by-Step Process

**1. Design Phase** (before writing code):
```
Q: How will user invoke this feature?
A: Via MCP tool "sync_daemon_start"

Q: What is the entry point?
A: @mcp.tool() decorated function in server.py

Q: What dependencies are required?
A: SurrealDB, Entire.io API, git repository

Q: What does end-to-end flow look like?
A: User → MCP → sync_daemon_start() → Entire.io API → checkpoint created
```

**2. Implementation Phase** (code + integration):
```python
# Step 1: Write code
class SyncDaemon:
    async def start(self):
        # Implementation...
        pass

# Step 2: Add integration decorator (IMMEDIATELY, not later)
from mcp_server import mcp

@mcp.tool()
async def sync_daemon_start(repo_path: str) -> dict:
    """Start sync daemon for repository."""
    daemon = SyncDaemon(repo_path)
    await daemon.start()
    return {"status": "started", "repo": repo_path}

# Step 3: Register in server (IMMEDIATELY)
# In server.py:
from .sync_daemon import sync_daemon_start
# Tool auto-registered via @mcp.tool() decorator

# Step 4: Integration test (IMMEDIATELY)
@pytest.mark.integration
async def test_sync_daemon_callable_via_mcp():
    """Integration: sync_daemon_start is callable via MCP."""
    # Simulate MCP server call
    result = await sync_daemon_start("/path/to/repo")
    
    assert result["status"] == "started"
    assert Path(result["repo"]).exists()
```

**3. Validation Phase** (before claiming "complete"):
```bash
# Test 1: Tool appears in Claude Code
claude-code /tools | grep sync_daemon_start
# Expected: Tool listed

# Test 2: Tool is callable
claude-code "Start sync daemon for /path/to/repo"
# Expected: Daemon starts successfully

# Test 3: Integration tests pass
pytest tests/integration/test_sync_daemon.py -v
# Expected: All tests pass
```

**4. Only then claim "complete"**

---

## Real Example: Session 57 Track B

### What Went Wrong (NO Integration)

**Implementation**:
```python
# entire_ops.py (348 LOC) - NO @mcp.tool() decorator
class EntireOpsClient:
    async def create_checkpoint(...):
        pass

# sync_daemon.py (373 LOC) - NO @mcp.tool() decorator
class SyncDaemon:
    async def start(...):
        pass

# Result: Code exists but is UNREACHABLE
# Status: 100% orphaned, 0% production value
```

**Claimed**: "Track B complete, production-ready"

**Reality**: Cannot be called via Claude Code MCP tools

**Fix Required** (3-4 hours):
```python
# Step 1: Add decorators
@mcp.tool()
async def entire_create_checkpoint(...):
    """Create checkpoint in entire.io."""
    client = get_entire_ops()
    return await client.create_checkpoint(...)

@mcp.tool()
async def sync_daemon_start(...):
    """Start bidirectional git<>entire.io sync daemon."""
    daemon = get_sync_daemon()
    return await daemon.start()

# Step 2: Register in server.py
from .sync_tools import (
    entire_create_checkpoint,
    sync_daemon_start,
)

# Step 3: Integration tests
@pytest.mark.integration
async def test_tools_callable_via_mcp():
    # Verify tools are reachable...
    pass
```

**Time wasted**: 10+ hours implementation without integration = 30% waste

### What Should Have Happened (Integration-First)

**Implementation** (same time, but integrated from day 1):
```python
# Day 1: Implement entire_ops.py (3h) + integrate (30min)
class EntireOpsClient:
    async def create_checkpoint(...):
        pass

@mcp.tool()  # ← Added IMMEDIATELY
async def entire_create_checkpoint(...):
    client = get_entire_ops()
    return await client.create_checkpoint(...)

# Integration test (30min)
@pytest.mark.integration
async def test_entire_create_checkpoint_callable():
    result = await entire_create_checkpoint(...)
    assert result.success

# Day 2: Implement sync_daemon.py (3h) + integrate (30min)
# ... same pattern ...
```

**Result**: No orphaned code, production-ready at completion, 0% waste

---

## Benefits

**Time savings**:
- Old way: 10h implementation + 3h late integration = 13h
- New way: 10h implementation + 0.5h immediate integration = 10.5h
- **Savings**: 2.5 hours (19% reduction)

**Quality improvements**:
- No orphaned code (0% waste)
- Integration issues found early (easier to fix)
- Production-ready at completion (no surprises)
- User can test immediately (early feedback)

**Risk reduction**:
- Late integration often reveals architectural issues
- Early integration = smaller, fixable issues
- No "integration hell" at end of project

---

## When to Use

**Always use for**:
- New features (anything user-facing)
- Multi-system integrations (Track A + Track B)
- External API integrations
- Database operations

**Can skip for**:
- Internal utility functions (not user-facing)
- Test helpers
- Documentation changes

---

## Antipatterns to Avoid

❌ **"I'll integrate it later"**
- Later never comes (or is very expensive)
- Integrate IMMEDIATELY after writing code

❌ **"Unit tests are enough"**
- Unit tests use mocks (hide integration issues)
- Must have integration tests with real services

❌ **"Integration is someone else's job"**
- Integration is YOUR responsibility
- Don't hand off orphaned code

❌ **"It works on my branch"**
- Must work on main/production interface
- Test via production entry point, not test harness

---

## Code Template

```python
# integration_check.py - Verify integration before claiming "complete"

class IntegrationChecker:
    """Verify feature is integrated (not orphaned)."""
    
    def __init__(self, feature_name: str):
        self.feature_name = feature_name
    
    async def check(self) -> bool:
        """Returns True if integrated, False if orphaned."""
        print(f"\nIntegration Check: {self.feature_name}")
        print("=" * 60)
        
        issues = []
        
        # Check 1: Callable via production interface
        if not await self._check_callable():
            issues.append("Not callable via production interface")
        
        # Check 2: Integration tests exist and pass
        if not await self._check_integration_tests():
            issues.append("No integration tests or tests failing")
        
        # Check 3: End-to-end smoke test passes
        if not await self._check_e2e_flow():
            issues.append("End-to-end user flow fails")
        
        # Check 4: No orphaned code
        if not await self._check_code_reachable():
            issues.append("Code is orphaned (unreachable from entry point)")
        
        if issues:
            print(f"\n❌ NOT INTEGRATED: {len(issues)} issues found")
            for issue in issues:
                print(f"  - {issue}")
            print("\nFix integration issues before claiming 'complete'.\n")
            return False
        else:
            print(f"\n✅ INTEGRATED: Feature is production-ready\n")
            return True
    
    async def _check_callable(self) -> bool:
        """Verify feature is callable via production interface."""
        # For MCP tools
        if self.interface_type == "mcp":
            tools = await mcp.list_tools()
            return self.feature_name in [t.name for t in tools]
        
        # For APIs
        elif self.interface_type == "api":
            routes = app.routes
            return f"/{self.feature_name}" in [r.path for r in routes]
        
        return False
    
    async def _check_integration_tests(self) -> bool:
        """Verify integration tests exist and pass."""
        test_file = f"tests/integration/test_{self.feature_name}.py"
        if not Path(test_file).exists():
            return False
        
        # Run integration tests
        result = subprocess.run(
            ["pytest", test_file, "-v"],
            capture_output=True
        )
        return result.returncode == 0
    
    async def _check_e2e_flow(self) -> bool:
        """Verify end-to-end user flow works."""
        try:
            # Simulate user invoking feature
            result = await production_interface.invoke(self.feature_name)
            return result.success
        except Exception:
            return False
    
    async def _check_code_reachable(self) -> bool:
        """Verify code is reachable from entry point (not orphaned)."""
        # Run coverage with integration tests only
        result = subprocess.run(
            ["pytest", f"tests/integration/test_{self.feature_name}.py",
             "--cov=your_module", "--cov-report=json"],
            capture_output=True
        )
        
        # Check if >50% coverage from integration tests
        # (proves code is reachable from production entry point)
        with open("coverage.json") as f:
            coverage_data = json.load(f)
            coverage_pct = coverage_data["totals"]["percent_covered"]
            return coverage_pct > 50


# Usage before claiming "complete":
async def verify_feature_complete():
    checker = IntegrationChecker("sync_daemon")
    is_integrated = await checker.check()
    
    if not is_integrated:
        raise AssertionError(
            "Feature is NOT complete - integration issues found. "
            "Fix issues before proceeding."
        )
    
    print("✅ Feature is complete and integrated!")
```

---

## Success Metrics

**Track these per feature**:
- Time to first integration (target: same day as code written)
- Orphaned code % (target: 0%)
- Late integration issues (target: 0 per feature)

**Session-level metrics**:
- Features with integration tests (target: 100%)
- Features callable via production interface (target: 100%)
- Rework due to late integration (target: <5%)

---

## Related Patterns

- [[mini-adversarial-review-checkpoints]] - When to verify integration
- [[staged-validation-long-horizon-tasks]] - Integration checkpoints in multi-week projects
- [[production-ready-definition-checklist]] - Integration is part of production-ready
- [[2026-02-09-session-43-phase-5b-verification-phase-6-launch|Decision: Session 43 Phase 5B Verification & Phase 6 Launch]] - Negative example: SessionPersistence delivered without integration
- [[2026-02-14-adversarial-multi-agent-review-protocol|Decision: Adversarial Multi-Agent Review Protocol]] - Adversarial review as integration gate
- [[2026-02-13-phase-2-track-b-entire-io-sync-daemon-complete]] — Track B: the definitive negative example (1,494 LOC orphaned, prompted this pattern)
- [[2026-02-14-phases-1-3-retrospective-key-learnings]] — retrospective that codified this pattern as project standard
- [[2026-02-14-end-to-end-compound-cycle-validation-script]] — the end-to-end validation script that embodies this pattern's "executable spec" principle
- [[2026-02-23-enforce-no-orphan-modules-policy]] — policy that enforces integration-first at code review level
- [[2026-02-24-anti-pattern-disconnected-modules-without-consumers]] — the anti-pattern this principle prevents
- [[bidirectional-linking]] — bidirectional wiki-links are a documentation-level implementation of integration-first: every note must link back to its referrers

---

**Last Updated**: 2026-02-14
**Validated**: Session 57 Track B (negative example - orphaned code)
**Fix Required**: 3-4 hours to add integration (30% of implementation time wasted)
