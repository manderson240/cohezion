---
project_name: aimo-progress-prize-3
author: Mike-anderson
date: 2026-03-24
version: 1.0
status: draft
workflow_type: epics
epic_count: 6
story_count: 24
total_points: 68
---

# Epics & Stories - AIMO Mathematical Reasoning Swarm

## Overview

This document breaks down the AIMO Mathematical Reasoning Swarm implementation into 6 epics with 24 sprint-ready stories. Each story includes acceptance criteria, point estimates, and agent assignments.

---

## Epic 0: Planning & Documentation

**Status:** In Progress
**Points:** 13
**Sprint:** 0
**Owner:** Product Manager
**Dependencies:** None

**Description:** Create formal planning artifacts required for BMAD-compliant development.

### Stories

#### Story 0.1: Create Product Requirements Document

**ID:** AIMO-001
**Points:** 3
**Priority:** P0
**Status:** ✅ Complete
**Agent:** Product Manager

**Description:** Create PRD with competition requirements, success metrics, and MVP scope.

**Acceptance Criteria:**
- [x] Executive summary with $2.2M prize context
- [x] Competition requirements (Kaggle rules, API protocol)
- [x] Success metrics (≥47/50 accuracy, ≥0.95 stability)
- [x] MVP scope (10 reference problems first)
- [x] Model selection table (pre-March 15 cutoff)
- [x] 8 functional requirements (Doer/Thinker/Knower)
- [x] 5 non-functional requirements
- [x] 5 user stories
- [x] Technical debt section (4 critical issues)

**Definition of Done:**
- PRD saved to `_bmad-output/planning-artifacts/prd-aimo-progress-prize-3.md`
- Reviewed by solution architect
- Approved by stakeholder

**Tasks:**
- [x] Load competition rules from `RULES.md`
- [x] Define success metrics
- [x] Write functional requirements
- [x] Document model selection
- [x] Create user stories

---

#### Story 0.2: Create Technical Architecture

**ID:** AIMO-002
**Points:** 5
**Priority:** P0
**Status:** ✅ Complete
**Agent:** Solution Architect

**Description:** Create formal architecture document with Triune Manifold, 12D state vector, and component diagram.

**Acceptance Criteria:**
- [x] Triune Manifold pillars (Doer/Thinker/Knower)
- [x] 12D state vector specification (computation details)
- [x] Component diagram (ASCII)
- [x] Data flow (end-to-end problem processing)
- [x] Specialist routing logic + keyword tables
- [x] Resource management (memory/time budgets)
- [x] Error handling architecture
- [x] Security architecture (sandboxed execution)
- [x] Testing architecture (mock environment)

**Definition of Done:**
- Architecture saved to `_bmad-output/planning-artifacts/architecture-aimo.md`
- Component diagram reviewed
- Data flow validated against spec.md

**Tasks:**
- [x] Define architectural pillars
- [x] Specify 12D vector computation
- [x] Create component diagram
- [x] Document data flow
- [x] Write error handling patterns

---

#### Story 0.3: Generate Project Context

**ID:** AIMO-003
**Points:** 3
**Priority:** P0
**Status:** ✅ Complete
**Agent:** Technical Analyst

**Description:** Scan existing codebase to generate `project-context.md` with AI agent rules.

**Acceptance Criteria:**
- [x] Technology stack documented (Ollama, polars, SymPy, NumPy)
- [x] Architecture patterns (Triune Manifold, 12D state vector)
- [x] Swarm agent rules (specialist routing, adversarial TDD)
- [x] Math processing rules (LaTeX parsing, answer extraction)
- [x] API integration rules (single-row constraint)
- [x] Stability verification rules (dual-run protocol)
- [x] Resource management rules (memory/time budgets)
- [x] Error handling rules (timeout, fail-safe)
- [x] Troubleshooting patterns (4 known issues)
- [x] Implementation guardrails (DOs/DON'Ts)

**Definition of Done:**
- Project context saved to `docs/aimo-project-context.md`
- All 15 sections completed
- Optimized for LLM scanning

**Tasks:**
- [x] Analyze sandbox/aimo/ codebase
- [x] Read troubleshooting retro
- [x] Extract implementation patterns
- [x] Document error handling rules
- [x] Create guardrails section

---

#### Story 0.4: Create Epics & Stories

**ID:** AIMO-004
**Points:** 2
**Priority:** P0
**Status:** In Progress
**Agent:** Product Manager + Scrum Master

**Description:** Create this document with 6 epics and 24 sprint-ready stories.

**Acceptance Criteria:**
- [x] 6 epics defined (0-5)
- [ ] 24 stories with acceptance criteria
- [ ] Point estimates assigned
- [ ] Agent assignments mapped
- [ ] Dependencies documented
- [ ] Sprint sequence defined

**Definition of Done:**
- Epics saved to `_bmad-output/planning-artifacts/epics-aimo.md`
- All stories have acceptance criteria
- Ready for sprint planning

**Tasks:**
- [x] Define epic structure
- [x] Write Story 0.x (complete)
- [ ] Write Story 1.x
- [ ] Write Story 2.x
- [ ] Write Story 3.x
- [ ] Write Story 4.x
- [ ] Write Story 5.x

---

## Epic 1: Environment & API Integration (Stability Fixes)

**Status:** Not Started
**Points:** 13
**Sprint:** 1
**Owner:** Development Team
**Dependencies:** Epic 0 complete

**Description:** Integrate 4 critical stability fixes from troubleshooting retro.

### Stories

#### Story 1.1: Add Timeout Configuration

**ID:** AIMO-011
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** Developer

**Description:** Add explicit `timeout=300` to all `requests.post()` calls in `BaseSpecialist`.

**Acceptance Criteria:**
- [ ] `self.timeout = 300` in `__init__`
- [ ] `requests.post(..., timeout=self.timeout)` in `solve()`
- [ ] Timeout exception handling with descriptive error message
- [ ] `num_thread=16` in payload options for CPU fallback
- [ ] Unit test: timeout triggers after 300s

**Definition of Done:**
- Code merged to `base_specialist.py`
- Test passes: timeout exception caught
- No infinite hangs in load test

**Tasks:**
- [ ] Add timeout to `__init__`
- [ ] Update `solve()` method
- [ ] Add exception handler
- [ ] Write unit test

---

#### Story 1.2: Fix Error-as-Answer Anti-Pattern

**ID:** AIMO-012
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** Developer

**Description:** Modify `extract_answer()` to check for errors BEFORE regex extraction.

**Acceptance Criteria:**
- [ ] Check `response_text.startswith("Error")` first
- [ ] Return 0 on error (bypass regex)
- [ ] Extract `\boxed{answer}` pattern
- [ ] Fallback: last number in response
- [ ] Unit test: error message returns 0

**Definition of Done:**
- Code merged to `base_specialist.py`
- Test passes: error-as-answer prevented
- Reference problems accuracy > 0%

**Tasks:**
- [ ] Refactor `extract_answer()`
- [ ] Add error check
- [ ] Update regex extraction
- [ ] Write unit test

---

#### Story 1.3: Migrate Pandas → Polars

**ID:** AIMO-013
**Points:** 5
**Priority:** P0
**Status:** Not Started
**Agent:** Developer

**Description:** Replace pandas with polars across entire AIMO subsystem for performance.

**Acceptance Criteria:**
- [ ] `import polars as pl` in all files
- [ ] Remove all `import pandas as pd`
- [ ] Fix DataFrame access logic (`.iloc` → `.row`)
- [ ] Update `mock_aimo_api.py`
- [ ] Update `math_research_harness.py`
- [ ] All tests pass

**Definition of Done:**
- No pandas imports in `sandbox/aimo/`
- All polars imports explicit
- Reference problems load correctly
- No `NameError` in harness

**Tasks:**
- [ ] Audit all imports
- [ ] Replace pandas with polars
- [ ] Fix DataFrame access
- [ ] Run tests

---

#### Story 1.4: Implement Process Management

**ID:** AIMO-014
**Points:** 2
**Priority:** P0
**Status:** Not Started
**Agent:** DevOps

**Description:** Add process cleanup before sprint to prevent zombie swarms.

**Acceptance Criteria:**
- [ ] `ps aux | grep aimo | xargs kill -9` before sprint
- [ ] `ps aux | grep ollama | xargs kill -9` before sprint
- [ ] Monitor system load < 20
- [ ] Log cleanup to `sprint_monitor.log`
- [ ] Bash utility script created

**Definition of Done:**
- Cleanup script at `sandbox/aimo/cleanup.sh`
- Script runs before `swarm_driver.py`
- System load monitored
- No zombie processes after sprint

**Tasks:**
- [ ] Write cleanup script
- [ ] Integrate into driver
- [ ] Add load monitoring
- [ ] Test cleanup

---

## Epic 2: Reasoning Swarm Development

**Status:** Not Started
**Points:** 13
**Sprint:** 2
**Owner:** Development Team
**Dependencies:** Epic 1 complete

**Description:** Implement specialist swarm with adversarial review loop.

### Stories

#### Story 2.1: Specialist Routing

**ID:** AIMO-021
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** ML Engineer

**Description:** Implement domain routing based on 12D state vector keyword detection.

**Acceptance Criteria:**
- [ ] `SwarmCoordinator.plan_journey()` implemented
- [ ] Domain detection via keyword matching
- [ ] Primary + secondary specialist assignment
- [ ] 4 specialists: Algebraist, Geometer, NumberTheorist, Combinatorist
- [ ] Unit test: routing correct for sample problems

**Definition of Done:**
- Routing tested on 10 reference problems
- Correct specialist assigned per domain
- No routing errors

**Tasks:**
- [ ] Implement `plan_journey()`
- [ ] Add keyword detection
- [ ] Test on reference problems

---

#### Story 2.2: Adversarial Review Loop

**ID:** AIMO-022
**Points:** 5
**Priority:** P0
**Status:** Not Started
**Agent:** ML Engineer

**Description:** Integrate adversarial review with max 2 refinement cycles.

**Acceptance Criteria:**
- [ ] `AdversaryAgent.review()` called after code generation
- [ ] Max 2 refinement cycles
- [ ] Verified → proceed to answer extraction
- [ ] Flaws found → refine reasoning
- [ ] Log review results

**Definition of Done:**
- Adversarial loop integrated
- Max 2 cycles enforced
- Review results logged
- No infinite loops

**Tasks:**
- [ ] Integrate `AdversaryAgent`
- [ ] Implement refinement loop
- [ ] Add logging
- [ ] Test cycles

---

#### Story 2.3: FLUME Proof Navigator

**ID:** AIMO-023
**Points:** 5
**Priority:** P1
**Status:** Not Started
**Agent:** Research Engineer

**Description:** Use VAE-compressed thought vectors to interpolate between known mathematical identities.

**Acceptance Criteria:**
- [ ] FLUME encoding of proof steps
- [ ] Latent vector comparison
- [ ] Logical drift detection
- [ ] Stable trajectory identification
- [ ] Integration with reasoning chain

**Definition of Done:**
- FLUME encoding implemented
- Drift detection working
- Stable trajectories identified
- Tested on reference problems

**Tasks:**
- [ ] Implement FLUME encoding
- [ ] Add drift detection
- [ ] Test on proofs

---

## Epic 3: Verification & Stability

**Status:** Not Started
**Points:** 10
**Sprint:** 3
**Owner:** Development Team
**Dependencies:** Epic 2 complete

**Description:** Implement dual-run verification and Knower audit.

### Stories

#### Story 3.1: Dual-Run Protocol

**ID:** AIMO-031
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** Developer

**Description:** Execute two independent reasoning chains and compare answers.

**Acceptance Criteria:**
- [ ] Run 1: Primary specialist
- [ ] Run 2: Secondary specialist
- [ ] Compare answers: `ans1 == ans2`
- [ ] Compute stability score: 1.0 if match, 0.0 if divergent
- [ ] Log both reasoning chains

**Definition of Done:**
- Dual-run implemented in `swarm_driver.py`
- Stability score computed
- Both chains logged

**Tasks:**
- [ ] Implement dual-run
- [ ] Add comparison logic
- [ ] Compute stability score
- [ ] Test on reference problems

---

#### Story 3.2: Knower Audit

**ID:** AIMO-032
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** Developer

**Description:** Implement `KnowerAuditor.audit_runs()` for consistency checking.

**Acceptance Criteria:**
- [ ] `audit_runs()` method implemented
- [ ] Returns `AuditResult(stability_score, action, final_answer)`
- [ ] Action: CONSISTENT | TIE_BREAKER
- [ ] Stability score: 1.0 or 0.0
- [ ] Unit test: audit correct

**Definition of Done:**
- Knower audit implemented
- Returns correct audit result
- Test passes

**Tasks:**
- [ ] Implement `audit_runs()`
- [ ] Define `AuditResult` dataclass
- [ ] Write unit test

---

#### Story 3.3: Tie-Breaker Logic

**ID:** AIMO-033
**Points:** 4
**Priority:** P0
**Status:** Not Started
**Agent:** Developer

**Description:** Implement majority voting when dual-run answers diverge.

**Acceptance Criteria:**
- [ ] Trigger tie-breaker if `ans1 != ans2`
- [ ] Run 3: Third specialist (Phi-4)
- [ ] Majority voting: `resolve_tie(ans1, ans2, ans3)`
- [ ] Return final answer
- [ ] Log tie-breaker results

**Definition of Done:**
- Tie-breaker implemented
- Majority voting correct
- Results logged

**Tasks:**
- [ ] Implement tie-breaker trigger
- [ ] Run third specialist
- [ ] Implement majority voting
- [ ] Test on divergent cases

---

## Epic 4: Submission & Optimization

**Status:** Not Started
**Points:** 10
**Sprint:** 4
**Owner:** Development Team
**Dependencies:** Epic 3 complete

**Description:** Optimize for 5-hour compute limit and automate submission.

### Stories

#### Story 4.1: Optimize for 5-Hour Limit

**ID:** AIMO-041
**Points:** 5
**Priority:** P0
**Status:** Not Started
**Agent:** Performance Engineer

**Description:** Ensure swarm completes 110 problems within 5-hour compute window.

**Acceptance Criteria:**
- [ ] Time per problem ≤ 165s (including safety margin)
- [ ] Total time ≤ 18,000s (5 hours)
- [ ] Progress telemetry logged
- [ ] Memory usage ≤ 12GB VRAM
- [ ] Model unloading between problems

**Definition of Done:**
- 110 problems completed in < 5 hours
- Memory budget respected
- Telemetry logged

**Tasks:**
- [ ] Profile time per problem
- [ ] Optimize model loading
- [ ] Add telemetry
- [ ] Test on 110 problems

---

#### Story 4.2: Model Fine-Tuning

**ID:** AIMO-042
**Points:** 3
**Priority:** P1
**Status:** Not Started
**Agent:** ML Engineer

**Description:** Fine-tune local SLMs for math reasoning to offload simpler sub-tasks.

**Acceptance Criteria:**
- [ ] Training data: AIMO reference problems + solutions
- [ ] Fine-tune qwen2-math:1.5b
- [ ] Validate on held-out problems
- [ ] Deploy fine-tuned model
- [ ] Measure accuracy improvement

**Definition of Done:**
- Model fine-tuned
- Accuracy improved on reference problems
- Model deployed

**Tasks:**
- [ ] Prepare training data
- [ ] Fine-tune model
- [ ] Validate
- [ ] Deploy

---

#### Story 4.3: Submission Automation

**ID:** AIMO-043
**Points:** 2
**Priority:** P0
**Status:** Not Started
**Agent:** DevOps

**Description:** Automate submission to Kaggle leaderboard.

**Acceptance Criteria:**
- [ ] Integrate with official AIMO API
- [ ] `env.predict()` called exactly once per row
- [ ] Submission file generated
- [ ] Upload to Kaggle
- [ ] Verify leaderboard score

**Definition of Done:**
- Submission automated
- Leaderboard score visible
- No API errors

**Tasks:**
- [ ] Integrate AIMO API
- [ ] Generate submission
- [ ] Upload to Kaggle
- [ ] Verify score

---

## Epic 5: BMAD Sprint Execution

**Status:** Not Started
**Points:** 8
**Sprint:** 0 (current)
**Owner:** Scrum Master
**Dependencies:** Epic 0 complete

**Description:** Execute BMAD method with Correct Course workflow.

### Stories

#### Story 5.1: Run Correct Course Workflow

**ID:** AIMO-051
**Points:** 3
**Priority:** P0
**Status:** In Progress
**Agent:** Scrum Master

**Description:** Execute Correct Course workflow to align implementation with planning.

**Acceptance Criteria:**
- [x] Change trigger documented
- [x] Epic impact assessed
- [x] Artifact conflicts analyzed
- [x] Path forward evaluated (Direct Adjustment)
- [x] Sprint Change Proposal created
- [x] User approved proposal
- [ ] Artifacts created (PRD ✅, Architecture ✅, Epics in progress)
- [ ] Stability fixes integrated

**Definition of Done:**
- Sprint Change Proposal approved
- All artifacts created
- Ready for sprint planning

**Tasks:**
- [x] Initialize change navigation
- [x] Execute checklist
- [x] Create PRD
- [x] Create Architecture
- [ ] Create Epics
- [ ] Create Sprint Plan

---

#### Story 5.2: Sprint Planning

**ID:** AIMO-052
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** Scrum Master

**Description:** Generate `sprint-status.yaml` from epic files.

**Acceptance Criteria:**
- [ ] Load all epics
- [ ] Sequence stories by dependency
- [ ] Assign agents to stories
- [ ] Estimate timeline
- [ ] Generate `sprint-status.yaml`

**Definition of Done:**
- Sprint plan generated
- Stories sequenced
- Agents assigned
- Timeline estimated

**Tasks:**
- [ ] Load epics
- [ ] Sequence stories
- [ ] Assign agents
- [ ] Generate YAML

---

#### Story 5.3: Execute with BMAD Method

**ID:** AIMO-053
**Points:** 2
**Priority:** P0
**Status:** Not Started
**Agent:** Development Team

**Description:** Implement stories following BMAD method with warm-start/clean-shutdown.

**Acceptance Criteria:**
- [ ] Warm-start: cache + metrics loaded
- [ ] Alignment gate before execution
- [ ] Execute story with agent delegation
- [ ] Inflection detection + vault logging
- [ ] Metrics collection
- [ ] Clean-shutdown: cache + metrics persisted

**Definition of Done:**
- All stories implemented
- Metrics persisted
- Cache persisted
- No coherence drift

**Tasks:**
- [ ] Warm-start
- [ ] Execute stories
- [ ] Collect metrics
- [ ] Clean-shutdown

---

## Epic 6: Testing & Validation

**Status:** Not Started
**Points:** 11
**Sprint:** 5
**Owner:** QA Engineer
**Dependencies:** Epic 3 complete

**Description:** Validate swarm on reference problems and achieve stability targets.

### Stories

#### Story 6.1: Reference Problems Benchmark

**ID:** AIMO-061
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** QA Engineer

**Description:** Run swarm on 10 reference problems and measure accuracy.

**Acceptance Criteria:**
- [ ] Load 10 reference problems from JSON
- [ ] Execute swarm on each problem
- [ ] Compare answers to ground truth
- [ ] Compute accuracy: correct / total
- [ ] Target: 100% (10/10)

**Definition of Done:**
- Accuracy measured
- Target achieved (100%)
- Results logged

**Tasks:**
- [ ] Load reference problems
- [ ] Run swarm
- [ ] Compare answers
- [ ] Compute accuracy

---

#### Story 6.2: Stability Test

**ID:** AIMO-062
**Points:** 5
**Priority:** P0
**Status:** Not Started
**Agent:** QA Engineer

**Description:** Measure dual-run consistency across all problems.

**Acceptance Criteria:**
- [ ] Run dual-verification on 10 problems
- [ ] Compute stability ratio: consistent / total
- [ ] Target: ≥0.90 (9/10 consistent)
- [ ] Log divergent cases
- [ ] Analyze divergence causes

**Definition of Done:**
- Stability ratio computed
- Target achieved (≥0.90)
- Divergent cases analyzed

**Tasks:**
- [ ] Run dual-verification
- [ ] Compute ratio
- [ ] Log divergent cases
- [ ] Analyze causes

---

#### Story 6.3: Integration Test

**ID:** AIMO-063
**Points:** 3
**Priority:** P0
**Status:** Not Started
**Agent:** QA Engineer

**Description:** Test full integration: API iteration, dual-run, tie-breaker, extraction.

**Acceptance Criteria:**
- [ ] Single-row API iteration works
- [ ] Exactly one `env.predict()` per row
- [ ] Dual-run executes for all problems
- [ ] Tie-breaker triggers on divergence
- [ ] Answer extraction handles errors

**Definition of Done:**
- All integration tests pass
- No API errors
- Correct behavior verified

**Tasks:**
- [ ] Test API iteration
- [ ] Test dual-run
- [ ] Test tie-breaker
- [ ] Test extraction

---

## Summary

### Epic Breakdown

| Epic | Stories | Points | Status | Sprint |
|------|---------|--------|--------|--------|
| Epic 0: Planning | 4 | 13 | In Progress | 0 |
| Epic 1: Stability Fixes | 4 | 13 | Not Started | 1 |
| Epic 2: Swarm Development | 3 | 13 | Not Started | 2 |
| Epic 3: Verification | 3 | 10 | Not Started | 3 |
| Epic 4: Submission | 3 | 10 | Not Started | 4 |
| Epic 5: BMAD Execution | 3 | 8 | Not Started | 0 |
| Epic 6: Testing | 3 | 11 | Not Started | 5 |
| **Total** | **23** | **78** | - | - |

### Sprint Sequence

**Sprint 0:** Epic 0 + Epic 5 (Planning + BMAD Execution)
**Sprint 1:** Epic 1 (Stability Fixes)
**Sprint 2:** Epic 2 (Swarm Development)
**Sprint 3:** Epic 3 (Verification)
**Sprint 4:** Epic 4 (Submission)
**Sprint 5:** Epic 6 (Testing)

### Critical Path

```
Epic 0 → Epic 1 → Epic 2 → Epic 3 → Epic 6
  ↓        ↓        ↓        ↓        ↓
Epic 5 → Sprint 1 → Sprint 2 → Sprint 3 → Sprint 5
                        ↓
                    Epic 4 → Sprint 4
```

### Dependencies

- Epic 0 must complete before Epic 1, 5
- Epic 1 must complete before Epic 2
- Epic 2 must complete before Epic 3
- Epic 3 must complete before Epic 6
- Epic 4 can run parallel to Epic 3

---

**Next:** Sprint Planning (Story 5.2) → Generate `sprint-status.yaml`
