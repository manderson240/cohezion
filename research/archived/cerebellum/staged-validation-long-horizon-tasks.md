---
title: 'Staged Validation for Long-Horizon Tasks'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.96
  stage: growing
  synapse_in: 8
  synapse_out: 7
---
# Staged Validation for Long-Horizon Tasks

## Pattern ID
`staged-validation-long-horizon-tasks`

## Category
Project Management, Compound Engineering, Risk Mitigation

## Problem Statement

**Session 57 Evidence**:
- Phase 2 declared "100% complete" after 21.5 hours
- Adversarial review 6 hours later revealed only 29% actually complete
- 15 critical blockers (8× P0, 7× P1) discovered AFTER "completion"
- Track B: 1,494 LOC orphaned (NOT integrated into MCP server)
- Track A: SQL injection CVSS 9.8 found in "production-ready" code

**Root Cause**: No intermediate validation checkpoints. Work proceeded for 21.5h without adversarial review until final "completion" claim. All blockers discovered simultaneously at end.

**Impact**:
- 6 hours of adversarial review invalidated 21.5 hours of implementation
- 71% of claimed work needs rework (15 blockers across 3 tracks)
- User trust degraded (100% claim → 29% reality)
- No incremental value delivery (all-or-nothing)

## Pattern Description

**Staged Validation** divides long-horizon tasks (>8h) into validation stages with GO/NO-GO gates. Each gate performs mini-adversarial review before proceeding.

### Stage Design Principles

1. **Stage Duration**: 4-8h max per stage (single session)
2. **Exit Criteria**: Must pass adversarial review to proceed
3. **Rollback Cost**: <25% of stage effort to revert
4. **Incremental Value**: Each stage delivers usable artifact
5. **Dependency Ordering**: Critical-path stages first

### 5-Stage Template for Multi-Week Projects

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class StageStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    GO = "go"              # Passed review, proceed to next stage
    NO_GO = "no_go"        # Failed review, rework required
    COMPLETE = "complete"  # All stages GO + final validation

@dataclass
class ValidationGate:
    """GO/NO-GO gate between stages."""
    stage_id: int
    criteria: list[str]              # Required pass conditions
    reviewer: str                     # "self" | "peer" | "adversarial_team"
    duration_minutes: int = 30        # Time budget for review
    
    # Outputs
    status: Optional[StageStatus] = None
    blockers: list[str] = None        # Reasons for NO-GO
    recommendations: list[str] = None  # Improvements for next stage

@dataclass
class Stage:
    """Work stage with validation gate."""
    id: int
    name: str
    deliverables: list[str]           # Concrete artifacts
    estimated_hours: float
    gate: ValidationGate
    dependencies: list[int] = None     # Stage IDs that must be GO first
    
    # Tracking
    status: StageStatus = StageStatus.NOT_STARTED
    actual_hours: float = 0.0
    rework_hours: float = 0.0

class StagedProject:
    """Long-horizon project with staged validation."""
    
    def __init__(self, stages: list[Stage]):
        self.stages = {s.id: s for s in stages}
        self.current_stage_id: Optional[int] = None
    
    def start_stage(self, stage_id: int) -> bool:
        """Start a stage if dependencies are GO."""
        stage = self.stages[stage_id]
        
        # Check dependencies
        if stage.dependencies:
            for dep_id in stage.dependencies:
                if self.stages[dep_id].status != StageStatus.GO:
                    print(f"Cannot start Stage {stage_id}: "
                          f"Stage {dep_id} not GO")
                    return False
        
        stage.status = StageStatus.IN_PROGRESS
        self.current_stage_id = stage_id
        print(f"✓ Started Stage {stage_id}: {stage.name}")
        return True
    
    def submit_for_review(self, stage_id: int) -> ValidationGate:
        """Mark stage ready for validation."""
        stage = self.stages[stage_id]
        assert stage.status == StageStatus.IN_PROGRESS
        stage.status = StageStatus.READY_FOR_REVIEW
        print(f"→ Stage {stage_id} submitted for {stage.gate.reviewer} review")
        return stage.gate
    
    def record_review(
        self,
        stage_id: int,
        status: StageStatus,
        blockers: list[str] = None,
        recommendations: list[str] = None
    ):
        """Record gate review decision."""
        stage = self.stages[stage_id]
        gate = stage.gate
        
        gate.status = status
        gate.blockers = blockers or []
        gate.recommendations = recommendations or []
        stage.status = status
        
        if status == StageStatus.GO:
            print(f"✓ Stage {stage_id} GO - proceed to next stage")
        elif status == StageStatus.NO_GO:
            print(f"✗ Stage {stage_id} NO-GO - {len(blockers)} blockers")
            for blocker in blockers:
                print(f"  • {blocker}")
    
    def get_progress(self) -> dict:
        """Get project status."""
        go_count = sum(1 for s in self.stages.values() 
                       if s.status == StageStatus.GO)
        total = len(self.stages)
        
        return {
            "stages_complete": go_count,
            "total_stages": total,
            "completion_pct": (go_count / total) * 100,
            "current_stage": self.current_stage_id,
            "blockers": [
                f"Stage {sid}: {b}"
                for sid, s in self.stages.items()
                if s.status == StageStatus.NO_GO
                for b in s.gate.blockers
            ]
        }
```

### Session 57 Retrospective: What Should Have Happened

```python
# Define Phase 2 as 5 stages with validation gates
phase2_stages = [
    Stage(
        id=1,
        name="Track A Foundation (Schema + SurrealQL)",
        deliverables=[
            "Schema definitions (agents, decisions, patterns)",
            "5 basic SurrealQL queries",
            "Unit tests (50+ assertions)"
        ],
        estimated_hours=6.0,
        gate=ValidationGate(
            stage_id=1,
            criteria=[
                "All schema types compile",
                "Zero SQL injection vulnerabilities (f-string check)",
                "Unit tests pass",
                "Manual query test (create agent → query → verify)"
            ],
            reviewer="self"
        )
    ),
    Stage(
        id=2,
        name="Track B Implementation (Entire.io Sync Daemon)",
        deliverables=[
            "7 Python modules (entire_ops, sync_daemon, work_queue, ...)",
            "Basic integration test",
            "@mcp.tool() decorators + registration"
        ],
        estimated_hours=8.0,
        gate=ValidationGate(
            stage_id=2,
            criteria=[
                "User can call `sync_daemon_start()` via MCP",
                "End-to-end test: git commit → entire.io checkpoint created",
                "No orphaned code (all modules reachable)",
                "Health endpoints return 200"
            ],
            reviewer="adversarial",
            duration_minutes=30
        ),
        dependencies=[1]  # Needs Track A schema for agent context
    ),
    Stage(
        id=3,
        name="Track C Cross-Linking",
        deliverables=[
            "10+ new decision→pattern links",
            "5+ new pattern→concept links",
            "Graph query validation"
        ],
        estimated_hours=3.0,
        gate=ValidationGate(
            stage_id=3,
            criteria=[
                "Links verified in SurrealDB (SELECT count() FROM links)",
                "Traversal query returns expected results",
                "No dangling references (broken links)"
            ],
            reviewer="self"
        ),
        dependencies=[1]  # Needs schema from Track A
    ),
    Stage(
        id=4,
        name="Production Hardening",
        deliverables=[
            "Retry logic + timeouts (Track B)",
            "State persistence (checkpoint recovery)",
            "Failure injection tests (50% of test suite)"
        ],
        estimated_hours=6.0,
        gate=ValidationGate(
            stage_id=4,
            criteria=[
                "Survives network timeout (test passes)",
                "Recovers from crash (checkpoint reload works)",
                "No P0/P1 blockers from adversarial review"
            ],
            reviewer="adversarial",
            duration_minutes=60
        ),
        dependencies=[2]  # Needs Track B integrated first
    ),
    Stage(
        id=5,
        name="Deployment + Documentation",
        deliverables=[
            "Systemd service file",
            "ENTIRE_SYNC_DEPLOYMENT.md",
            "Health check guide"
        ],
        estimated_hours=4.0,
        gate=ValidationGate(
            stage_id=5,
            criteria=[
                "External reviewer can deploy in <30 min",
                "All checklist items green",
                "Zero P0 blockers remaining"
            ],
            reviewer="adversarial",
            duration_minutes=90
        ),
        dependencies=[4]  # Production hardening must be GO first
    )
]

project = StagedProject(phase2_stages)

# Session 57 actual timeline (what happened):
# Hour 0-21.5: Implement all 5 stages without intermediate validation
# Hour 21.5: Declare "100% complete"
# Hour 27.5: Adversarial review finds 15 blockers → NO-GO

# What SHOULD have happened with staged validation:
# Hour 0-6: Stage 1 implementation
# Hour 6-6.5: Stage 1 gate review → GO (foundation solid)
# Hour 6.5-14.5: Stage 2 implementation
# Hour 14.5-15: Stage 2 gate review → NO-GO (missing @mcp.tool, no retry)
#   ↑ CRITICAL: Blockers found at 15h, not 27.5h (12.5h savings)
# Hour 15-17: Rework Stage 2 (add @mcp.tool, retry logic)
# Hour 17-17.5: Stage 2 re-review → GO
# ... continue with Stages 3-5
```

## Benefits

1. **Early Blocker Detection**: Find issues at 15h instead of 27.5h (12.5h savings)
2. **Incremental Value**: Each GO stage delivers usable artifact
3. **Reduced Rework**: Fix blockers immediately (25% effort) vs late rework (100% effort)
4. **Accurate Status**: "3/5 stages GO" more honest than "100% complete"
5. **Risk Mitigation**: Can stop project at any stage if ROI negative

## ROI Analysis

**Session 57 Case Study**:
- Without staged validation: 21.5h implementation + 6h review → 15 blockers → 26-29h rework
- With staged validation: 5× 30-min gates (2.5h total) → blockers found early → 8-10h rework
- **Savings**: 18-21h (66-72% reduction in rework)

**Cost**: 2.5h validation overhead (11.6% of 21.5h)  
**Benefit**: 18-21h rework avoided (84-97% savings)  
**ROI**: 7.2-8.4× return

## When to Use

✅ **Use staged validation when**:
- Task duration >8h (multi-session)
- Multiple integration points
- Production deployment (NO rollback path)
- Critical-path dependency for other work
- High rework cost if blockers found late

❌ **Don't use (single-pass OK) when**:
- Throwaway prototype (<4h)
- Tight feedback loop (can iterate quickly)
- No integration dependencies
- Easy rollback (feature flag, canary)

## Antipatterns

### ❌ Antipattern 1: "Big Bang" Validation
```python
# BAD: Work for 21.5h, then validate at end
implement_all_tracks()  # 21.5h
adversarial_review()    # Finds 15 blockers (too late!)

# GOOD: Validate after each stage
for stage in stages:
    implement(stage)
    if not validate(stage):  # NO-GO at Stage 2 (15h, not 27.5h)
        rework(stage)
```

### ❌ Antipattern 2: Self-Only Review for Critical Stages
```python
# BAD: Self-review for production code
stage2_gate = ValidationGate(
    criteria=["Code looks good to me"],
    reviewer="self"  # Missed 8 P0 blockers!
)

# GOOD: Adversarial review for critical stages
stage2_gate = ValidationGate(
    criteria=["Survives network timeout", "No SQL injection", ...],
    reviewer="adversarial",  # External perspective catches blind spots
    duration_minutes=30
)
```

### ❌ Antipattern 3: Weak Exit Criteria
```python
# BAD: Vague criteria (easy to game)
criteria = ["Track B looks complete"]

# GOOD: Concrete, testable criteria
criteria = [
    "User can call sync_daemon_start() via MCP",
    "End-to-end test passes (git → entire.io)",
    "Health endpoint returns 200",
    "Zero P0 blockers from adversarial review"
]
```

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Early blocker detection** | 80%+ at gates | Blockers found at gate / total blockers |
| **Rework reduction** | 50%+ savings | Rework hours (staged) / rework hours (big bang) |
| **Stage pass rate** | 70%+ first-try GO | Stages GO first time / total stages |
| **Status accuracy** | <10% error | Claimed % complete vs actual |

## Stage Gate Checklist Template

```markdown
# Stage N Gate Review

## Deliverables (Check ALL boxes)
- [ ] Artifact 1 exists and is testable
- [ ] Artifact 2 passes integration test
- [ ] Artifact 3 documented in deployment guide

## Quality Gates (MUST PASS)
- [ ] Zero P0 blockers (security, data loss, crash)
- [ ] Zero P1 blockers (broken integration, wrong behavior)
- [ ] Unit test coverage >80% for new code
- [ ] Integration test passes end-to-end
- [ ] Manual smoke test succeeds (user can execute)

## Adversarial Checks (Pick 3 minimum)
- [ ] Survives network timeout
- [ ] Survives disk full
- [ ] Survives malformed input
- [ ] Survives concurrent requests
- [ ] No SQL injection (if DB queries)
- [ ] No command injection (if shell calls)

## GO/NO-GO Decision
- **GO**: All deliverables ✓, All quality gates ✓, 3+ adversarial checks ✓
- **NO-GO**: ANY P0/P1 blocker OR <80% quality gates pass

## If NO-GO
- [ ] Blockers documented with reproduction steps
- [ ] Estimated rework time: ___h
- [ ] Re-review scheduled after rework
```

## Related Patterns

- **`mini-adversarial-review-checkpoints.md`**: Use for stage gate reviews (30-min validation)
- **`conservative-baseline-estimation.md`**: Estimate stage durations with P75 buffers
- **`integration-first-definition-of-done.md`**: Stage deliverable = integrated + testable
- **`production-ready-definition-checklist.md`**: Final stage must pass full 40-item checklist

## Code Template

```python
# src/cohezion/planning/staged_project.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class StageStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    GO = "go"
    NO_GO = "no_go"

@dataclass
class ValidationGate:
    stage_id: int
    criteria: list[str]
    reviewer: str  # "self" | "peer" | "adversarial"
    duration_minutes: int = 30
    status: Optional[StageStatus] = None
    blockers: list[str] = field(default_factory=list)

@dataclass
class Stage:
    id: int
    name: str
    deliverables: list[str]
    estimated_hours: float
    gate: ValidationGate
    dependencies: list[int] = field(default_factory=list)
    status: StageStatus = StageStatus.NOT_STARTED
    actual_hours: float = 0.0

class StagedProject:
    def __init__(self, stages: list[Stage]):
        self.stages = {s.id: s for s in stages}
    
    def start_stage(self, stage_id: int) -> bool:
        """Start stage if dependencies GO."""
        stage = self.stages[stage_id]
        if any(self.stages[d].status != StageStatus.GO 
               for d in stage.dependencies):
            return False
        stage.status = StageStatus.IN_PROGRESS
        return True
    
    def record_review(self, stage_id: int, status: StageStatus, 
                      blockers: list[str] = None):
        """Record gate decision."""
        stage = self.stages[stage_id]
        stage.gate.status = status
        stage.gate.blockers = blockers or []
        stage.status = status
```

## Historical Context

**Session 57 Learnings**:
- 21.5h implementation without intermediate validation
- Adversarial review at end found 15 blockers (29% actually complete)
- Track B: 1,494 LOC orphaned (missing @mcp.tool integration)
- Staged validation would have caught integration gap at Stage 2 gate (15h, not 27.5h)

**Compounding Impact**:
- Early detection → less rework → faster iterations
- Incremental value → usable artifacts at each stage
- Accurate status → preserved trust → better planning

---

**Pattern Status**: Production-ready  
**Domain**: Project Management, Compound Engineering  
**Evidence Base**: Session 57 adversarial review (15 blockers, 71% rework)  
**ROI**: 7.2-8.4× return (2.5h validation → 18-21h rework avoided)  
**Last Updated**: 2026-02-14

## Related

- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-14-wave-1-status-all-phases-6-complete]]
- [[2026-02-14-end-to-end-compound-cycle-validation-script]]
- [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]]
- [[adversarial-review]] — each stage gate uses adversarial review as the validation mechanism; the Session 57 lesson showed self-review alone missed 15 blockers
- [[workflow-orchestration]] — staged validation is an orchestration pattern that sequences work into dependency-ordered phases with quality gates
- [[concept-validation]] — stage gate criteria apply the same evidence-gated validation principle used for concept accuracy verification
