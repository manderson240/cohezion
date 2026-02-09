# Task #3 Known Issues & Separations of Concern

**Created**: 2026-02-09
**Task**: #3 - Ensure proper git branching and Phase 5B setup
**Status**: Task #3 COMPLETE - Issues documented below

---

## Summary

Task #3 has successfully completed all objectives for git branching and workflow setup. However, a pre-existing issue was discovered during testing: import errors in the test suite related to missing swarm module files.

**This is NOT a git branching issue.** This is a separate, pre-existing module initialization problem that exists on the feature/token-efficiency-5b branch.

---

## Pre-Existing Issue: Missing swarm Module Files

### The Problem

When running the full test suite, the following error occurs:
```
ModuleNotFoundError: No module named 'cohezion.swarm.adaptive_router_adapter'
```

This error occurs because:
1. `/src/cohezion/swarm/__init__.py` imports `adaptive_router_adapter`
2. The file `/src/cohezion/swarm/adaptive_router_adapter.py` does not exist

### Files Referenced But Missing

From examining `src/cohezion/swarm/__init__.py`, the following files are imported but don't exist:
- `adaptive_router_adapter.py` (line 3)
- `batch_sizing.py` (referenced as "untracked" - may exist in working dir)
- `hardware_profiler_stub.py` (referenced as "untracked" - may exist)
- `metrics_collector.py` (referenced as "untracked" - may exist)
- `model_profiles_config.py` (referenced as "untracked" - may exist)

### Impact

- Individual subsystem tests pass (they don't import swarm)
- Full test suite fails during collection
- Does not block Phase 5B implementation (subsystems are independent)

---

## Why This Isn't a Task #3 Problem

### Task #3 Objectives (All Complete)
- [✅] Verify feature/token-efficiency-5b branch state
- [✅] Document git workflow for Phase 5B
- [✅] Prepare commit strategy (7 atomic commits)
- [✅] Identify rollback points
- [✅] Preserve all Phase 5B work (144 files)
- [✅] Create team coordination documentation

### Module Import Issue
- ❌ Not a git branching issue
- ❌ Not a Phase 5B setup issue
- ❌ Is a pre-existing module initialization problem
- ❌ Should be fixed separately as a maintenance task

---

## What Should Happen

### For Task #3 (Git Setup)
✅ COMPLETE - All deliverables delivered
- GIT_WORKFLOW_PHASE_5B.md
- GIT_STATE_SNAPSHOT.txt
- PHASE_5B_COMMIT_CHECKLIST.md
- TASK_3_COMPLETION_REPORT.md
- PHASE_5B_QUICK_START.md

**Status**: Ready for Phase 5B team execution

### For Import Issue (Separate Task)
⚠️ NEEDS SEPARATE TASK - Not part of #3
- Create new task to fix swarm module imports
- Fix adaptive_router_adapter.py or remove import
- Fix other missing module references
- Verify full test suite passes

**Status**: Blocked on separate maintenance work

---

## Workaround for Phase 5B

The import issue does NOT block Phase 5B subsystem work because:

1. **Subsystem tests are independent**
   - Each subsystem (5B.1 through 5B.7) tests independently
   - Individual pytest runs work fine
   - Only full test suite collection fails

2. **Quick verification works**
   ```bash
   # Test individual subsystem
   uv run pytest tests/compound/test_global_metrics_aggregator.py -q
   # This works (no swarm imports needed)

   # Full suite fails on collection
   uv run pytest tests/ -q
   # This fails (swarm import error)
   ```

3. **Team should proceed with Phase 5B**
   - Each specialist tests their own subsystem independently
   - Final integration testing will verify all 7 subsystems
   - Full test suite fix is separate maintenance work

---

## Recommended Next Steps

### Immediate (For Team-Lead)
1. Create new task #X: "Fix swarm module imports"
2. Assign to appropriate specialist (likely devops-specialist)
3. Priority: After Phase 5B is complete (doesn't block implementation)

### For That New Task
- Investigate which files should be created vs. removed
- Check git history to see where files went
- Either recreate missing modules or fix __init__.py imports
- Verify full test suite passes: `uv run pytest tests/ -q` → 892+

### For Phase 5B Team (Right Now)
- Follow PHASE_5B_QUICK_START.md
- Use PHASE_5B_COMMIT_CHECKLIST.md for each subsystem
- Test your own subsystem independently
- Don't worry about full suite until final integration

---

## Documentation Links

**For Phase 5B Work**:
- PHASE_5B_QUICK_START.md (start here!)
- GIT_STATE_SNAPSHOT.txt (current status)
- GIT_WORKFLOW_PHASE_5B.md (git operations)
- PHASE_5B_COMMIT_CHECKLIST.md (your execution guide)

**For Import Issue** (separate task):
- This document (TASK_3_KNOWN_ISSUES.md)
- Debug command: `python -c "from cohezion.swarm.adaptive_router_adapter import AdaptiveRouterAdapter"`

---

## Conclusion

**Task #3 is COMPLETE** with all objectives met for git branching and Phase 5B setup.

The module import issue is a pre-existing problem that should be fixed as a separate maintenance task after Phase 5B implementation is complete.

Phase 5B team should proceed with implementation using the provided checklists and workflow guides.

---

**Task**: #3 ✅ COMPLETE
**Issue**: Pre-existing, separate from git setup
**Action**: Create new maintenance task for swarm module fix
**Status**: Phase 5B ready to proceed
