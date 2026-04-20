---
project_name: aimo-progress-prize-3
date: 2026-03-24
change_trigger: Ad-hoc implementation without BMAD planning → 0.0% accuracy, stability issues
change_scope: Moderate
artifacts_modified:
  - PRD (new)
  - Architecture (new)
  - Epics & Stories (new)
  - Project Context (created)
  - Codebase (stability fixes)
routed_to: Product Manager / Solution Architect / Development Team
status: draft
---

# Sprint Change Proposal: AIMO Progress Prize 3

## 1. Issue Summary

### Problem Statement

The AIMO Mathematical Reasoning Swarm was implemented ad-hoc (17 Python files, 1,425 lines) before completing formal BMAD planning artifacts. This resulted in:

- **0.0% accuracy** on 10 reference problem benchmarks
- **4 critical stability issues** documented in troubleshooting retro
- **Missing planning artifacts**: No PRD, Architecture doc, or structured Epics/Stories
- **Low success probability** without BMAD structure for $2.2M competition

### Context & Discovery

**When discovered:** March 22, 2026 - after overnight autonomous research sprints

**Evidence:**
- `TROUBLESHOOTING_RETRO.md` documents 4 root causes:
  1. Ollama API timeout → infinite hang
  2. Silent extraction failures → error-as-answer
  3. Dependency desync → pd not defined
  4. Process management → zombie swarms (load 24+)
- Implementation: `sandbox/aimo/` complete but non-functional
- Specification: `spec.md` and `plan.md` exist but not BMAD-compliant

### Impact

- **Competition timeline**: 5-hour compute limit, 110 problems
- **Current state**: Cannot complete single reference problem reliably
- **Risk**: $2.2M prize opportunity at risk without structured approach

---

## 2. Impact Analysis

### Epic Impact

**Current Epic Structure (from plan.md):**
```
Epic 1: Phase 1 - Environment & API Integration (3 tasks)
Epic 2: Phase 2 - Reasoning Swarm Development (2 tasks)
Epic 3: Phase 3 - Verification & Stability (2 tasks)
Epic 4: Phase 4: Submission & Optimization (2 tasks)
```

**Required Changes:**
1. **Add Epic 0**: Planning & Documentation (NEW - must come first)
   - Create PRD, Architecture, Epics, Stories
   - Generate project context (completed)
   
2. **Modify Epic 1**: Add stability fixes from troubleshooting retro
   - Timeout configuration (300s explicit)
   - Error handling (check before regex extraction)
   - Polars migration (replace pandas)
   - Process management (zombie cleanup)
   
3. **Add Epic 5**: BMAD Sprint Execution (NEW)
   - Run Correct Course workflow
   - Execute sprint planning
   - Implement with BMAD method

**Re-sequenced Epic Order:**
```
Epic 0: Planning & Documentation (NEW)
Epic 1: Environment & API Integration (fixes)
Epic 2: Reasoning Swarm Development
Epic 3: Verification & Stability
Epic 4: Submission & Optimization
Epic 5: BMAD Sprint Execution (NEW)
```

### Artifact Conflicts

**Missing Artifacts (must create):**
1. **PRD**: AIMO-specific product requirements
   - Competition constraints ($2.2M, 110 problems, 5 hours)
   - Success metrics (≥47/50 accuracy, ≥0.95 stability)
   - MVP scope (reference problems first)
   
2. **Architecture**: Formal technical architecture
   - Triune Manifold (Doer/Thinker/Knower)
   - 12D State Vector specification
   - Component diagram
   - Data flow
   
3. **Epics & Stories**: BMAD-compliant breakdown
   - 6 epics with acceptance criteria
   - Sprint-ready stories with estimates
   - Dependency mapping
   
4. **Sprint Plan**: `sprint-status.yaml`
   - Story sequence
   - Agent assignments
   - Timeline

**Existing Artifacts (update needed):**
- `spec.md`: Update with lessons from troubleshooting
- `plan.md`: Convert to BMAD epic structure
- `project-context.md`: Created ✅

### Technical Impact

**Code Changes Required:**
1. `base_specialist.py`: Add timeout=300, error handling
2. `math_parser.py`: Already correct (12D state vector)
3. `swarm_driver.py`: Integrate polars, fix extraction
4. `mock_aimo_api.py`: Migrate pandas → polars
5. `math_research_harness.py`: Add explicit imports, error handling

**Estimated LOC changes**: ~150 lines (mostly error handling + imports)

---

## 3. Recommended Approach

### Selected Path: **Direct Adjustment** (Option 1)

**Rationale:**

1. **Architecture is correct**: Triune Manifold (Doer/Thinker/Knower) is sound
2. **Issues are known**: All 4 bugs documented with fixes in retro
3. **Codebase is functional**: 1,425 lines working but unstable
4. **Fixes are straightforward**: Timeout, error handling, polars, process mgmt
5. **Planning artifacts missing**: Create PRD, Architecture, Epics

**Effort Estimate:**
- **Planning artifacts**: 2-3 sessions (6-8 hours)
- **Code fixes**: 1 session (2-3 hours)
- **Total**: 3-4 sessions (8-11 hours)

**Risk Assessment:**
- **Technical risk**: Low (all fixes known)
- **Timeline risk**: Low (straightforward changes)
- **Team morale**: Positive (clear path forward)
- **Business value**: High ($2.2M prize opportunity)

**Timeline Impact:**
- **Original**: Ad-hoc continuation → unknown timeline
- **Revised**: BMAD-structured → 3-4 sessions to readiness
- **Net**: +1-2 sessions for planning, -4-6 sessions debugging

---

## 4. Detailed Change Proposals

### Proposal 1: Create AIMO PRD

**Artifact**: `planning-artifacts/prd-aimo-progress-prize-3.md`

**Sections:**
1. Executive Summary ($2.2M prize, 110 problems, 5-hour limit)
2. Competition Requirements (Kaggle rules, data format)
3. Success Metrics (≥47/50 accuracy, ≥0.95 stability)
4. MVP Scope (10 reference problems → 50 public → 50 hidden)
5. Model Selection (DeepSeek-R1-32B, Phi-4, etc.)
6. Constraints (memory, time, compute budget)

**Format:**
```markdown
# Product Requirements Document - AIMO Progress Prize 3

## Executive Summary
...

## Competition Requirements
...

## Success Metrics
- Primary: ≥47/50 on leaderboard
- Secondary: ≥0.95 dual-run stability
- MVP: 100% on 10 reference problems
```

---

### Proposal 2: Create AIMO Architecture

**Artifact**: `planning-artifacts/architecture-aimo.md`

**Sections:**
1. Triune Manifold Architecture (Doer/Thinker/Knower)
2. 12D State Vector Specification
3. Component Diagram
4. Data Flow (problem → state → routing → reasoning → verification → answer)
5. Specialist Routing (4 domains)
6. Resource Management (memory, time, models)

**Format:**
```markdown
# Architecture - AIMO Mathematical Reasoning Swarm

## Triune Manifold Architecture

### The Doer (Perception & Execution)
...

### The Thinker (Reasoning & Interpolation)
...

### The Knower (Validation & Stability)
...

## 12D State Vector
[diagram]
```

---

### Proposal 3: Create Epics & Stories

**Artifact**: `planning-artifacts/epics-aimo.md`

**Structure:**
```
Epic 0: Planning & Documentation
  Story 0.1: Create PRD
  Story 0.2: Create Architecture
  Story 0.3: Create Epics & Stories
  Story 0.4: Generate Project Context ✅

Epic 1: Environment & API Integration (Stability Fixes)
  Story 1.1: Add timeout=300 to all API calls
  Story 1.2: Fix error-as-answer anti-pattern
  Story 1.3: Migrate pandas → polars
  Story 1.4: Implement process management

Epic 2: Reasoning Swarm Development
  Story 2.1: Specialist routing (4 domains)
  Story 2.2: Adversarial review loop
  Story 2.3: FLUME proof navigator

Epic 3: Verification & Stability
  Story 3.1: Dual-run protocol
  Story 3.2: Knower audit
  Story 3.3: Tie-breaker logic

Epic 4: Submission & Optimization
  Story 4.1: Optimize for 5-hour limit
  Story 4.2: Model fine-tuning
  Story 4.3: Submission automation

Epic 5: BMAD Sprint Execution
  Story 5.1: Run Correct Course workflow ✅
  Story 5.2: Sprint planning
  Story 5.3: Execute with BMAD method
```

---

### Proposal 4: Integrate Stability Fixes

**Files to modify:**
1. `base_specialist.py` (line 29): Add `timeout=300`
2. `base_specialist.py` (extract_answer): Check error before regex
3. `mock_aimo_api.py`: Import polars, fix DataFrame access
4. `math_research_harness.py`: Add explicit imports
5. `swarm_driver.py`: Add process cleanup

**Changes:**
```python
# Before
timeout = 180  # implicit default

# After
timeout = 300  # 5 minutes for reasoning models

# Before
def extract_answer(response_text):
    numbers = re.findall(r"\d+", response_text)
    return int(numbers[-1]) if numbers else 0

# After
def extract_answer(response_text):
    if response_text.startswith("Error"):
        return 0  # Prevent error-as-answer
    boxed_match = re.search(r"\\boxed{([^}]+)}", response_text)
    if boxed_match:
        return int(boxed_match.group(1))
    numbers = re.findall(r"\d+", response_text)
    return int(numbers[-1]) if numbers else 0
```

---

## 5. Implementation Handoff

### Change Scope Classification

**Classification:** **Moderate**

**Rationale:**
- Requires backlog reorganization (new epics, story sequence)
- Code changes are straightforward (known fixes)
- Planning artifacts must be created before implementation
- PO/SM coordination needed for sprint planning

### Handoff Recipients

**Primary:**
- **Product Manager**: Create PRD, Architecture, Epics
- **Scrum Master**: Sprint planning, backlog organization
- **Development Team**: Implement stability fixes

**Responsibilities:**
- **PM**: Own planning artifacts (Stories 0.1-0.3)
- **SM**: Own sprint execution (Epic 5)
- **Dev**: Own code fixes (Epic 1 stories)

### Success Criteria

**Definition of Done:**
1. ✅ PRD created with competition requirements
2. ✅ Architecture doc with Triune Manifold
3. ✅ 6 epics with sprint-ready stories
4. ✅ Stability fixes integrated (4 issues)
5. ✅ Sprint plan generated (`sprint-status.yaml`)
6. ✅ 100% accuracy on 10 reference problems
7. ✅ ≥0.95 dual-run stability

---

## Next Steps

1. **Review this proposal** - Confirm accuracy and completeness
2. **Approve for implementation** - Explicit yes/no
3. **Route to agents**:
   - PM: Create PRD + Architecture
   - SM: Create Epics + Sprint plan
   - Dev: Implement stability fixes
4. **Execute sprint** - BMAD method with Correct Course workflow

---

**Generated by:** Correct Course Workflow (bmad-bmm-correct-course)
**Date:** 2026-03-24
**Workflow:** Incremental Mode - Change Proposal 1 of 4