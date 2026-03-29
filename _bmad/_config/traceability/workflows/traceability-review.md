---
name: traceability-review
description: Multiperspective adversarial review of traceability matrices for continuous compound engineering
web_bundle: true
createWorkflow: './steps/step-01-load-matrices.md'
---

# Traceability Adversarial Review

**Goal:** Apply multiperspective adversarial review to traceability engine recursively

**Your Role:** Adversarial reviewer examining completeness, accuracy, and self-improvement capabilities

---

## WORKFLOW ARCHITECTURE

This uses **party-mode multiperspective review** with **recursive self-traceability**:

### Core Principles

- **Multiperspective Analysis**: 5 review perspectives (completeness, accuracy, recursion, TDD, compound)
- **Recursive Self-Trace**: Engine traces its own traceability/ directory
- **Party Mode Integration**: Multi-agent adversarial review
- **TDD Validation**: Tests verify matrix generation
- **Compound Loop**: Each iteration improves the engine

---

## INITIALIZATION

### 1. Configuration Loading

Load config from `{project-root}/_bmad/core/config.yaml`:
- `user_name`, `communication_language`, `output_folder`

### 2. Matrix Loading

Load all 4 traceability matrices:
- `agent-workflow-matrix.csv` (447 rows)
- `workflow-task-matrix.csv` (2 rows - GAP!)
- `workflow-chain-matrix.csv` (0 rows - GAP!)
- `party-module-matrix.csv` (4 rows)

### 3. Engine Code Loading

Load traceability engine:
- `_bmad/_config/traceability/traceability_engine.py`
- `_bmad/_config/traceability/tests/test_traceability_engine.py`

---

## REVIEW PERSPECTIVES

### Perspective 1: Completeness

**Questions:**
- Are all 74 workflows traced? ✓ (agent-workflow matrix has 447 rows)
- Are all 27 agents mapped? ✓
- Are all 8 tasks captured? ⚠️ (only 2 invoke-task found)
- Missing invocation types? ⚠️ (workflow-chain is empty)

**Findings:**
- Agent→Workflow: 447 mappings (module-based, medium confidence)
- Workflow→Task: Only 2 (validate-workflow) - **MISSING 6 tasks**
- Workflow→Workflow: 0 - **MISSING all workflow chains**
- Party configs: 4 complete

### Perspective 2: Accuracy

**Questions:**
- Agent→Workflow matching by module only (low fidelity)
- Need explicit agent assignment in workflow YAML
- Task names extracted correctly? ✓ (validate-workflow)
- Line references accurate? ✓ (Line 314, Line 313)

**Findings:**
- Module matching is coarse (all agents in module assigned to all workflows)
- Need workflow-level agent field in workflow.yaml
- Task extraction works but only finds validate-workflow
- Missing: workflow.xml, help.md, editorial-review-*, shard-doc, index-docs

### Perspective 3: Recursion

**Questions:**
- Can the engine trace itself? ⚠️ (not implemented)
- Is traceability/ directory traced? ⚠️ (excluded from scan)
- Version snapshots created? ⚠️ (not implemented)

**Findings:**
- Engine doesn't trace _bmad/_config/traceability/
- No version snapshot mechanism
- No self-improvement loop

### Perspective 4: TDD

**Questions:**
- Test coverage sufficient? ✓ (18 tests)
- Integration tests real or mocks? ⚠️ (mostly mocks)
- Edge cases tested? ⚠️ (cycle detection not implemented)

**Findings:**
- Schema tests: 3 ✓
- XML parsing tests: 3 ✓ (mocked)
- Manifest parsing tests: 2 ✓
- Party config tests: 2 ✓
- Cycle detection tests: 2 ⚠️ (not implemented)
- Orphan tests: 2 ✓
- Integration tests: 2 ✓
- Recursive tests: 2 ⚠️ (not implemented)

### Perspective 5: Compound Engineering

**Questions:**
- Does this enable continuous improvement? ⚠️ (manual trigger)
- Multi-agent party mode integration? ⚠️ (workflow exists, not auto-triggered)
- Recursive self-improvement loop? ⚠️ (not implemented)

**Findings:**
- Engine runs once, no auto-improvement
- Party mode workflow exists but not integrated
- No automatic recursive iteration

---

## CRITICAL GAPS

### Gap 1: Workflow→Task Incomplete
**Problem:** Only 2 of 8 tasks found
**Cause:** Task invocations in workflow.xml not parsed
**Fix:** Parse workflow.xml for invoke-task tags

### Gap 2: Workflow→Workflow Missing
**Problem:** 0 workflow chains found
**Cause:** invoke-workflow tags not in instructions.xml
**Fix:** Scan workflow.yaml for workflow references

### Gap 3: Agent→Workflow Low Fidelity
**Problem:** Module-based matching (all agents→all workflows in module)
**Cause:** No explicit agent assignment in workflows
**Fix:** Add `agent:` field to workflow.yaml

### Gap 4: No Self-Trace
**Problem:** Engine doesn't trace traceability/
**Cause:** Hardcoded exclusion
**Fix:** Remove exclusion, add self-trace mode

### Gap 5: No Version Snapshots
**Problem:** No iteration tracking
**Cause:** No version mechanism
**Fix:** Add timestamp + iteration counter

---

## IMPROVEMENT PLAN

### Phase 1: Complete Task Extraction (HIGH)
1. Parse workflow.xml for invoke-task
2. Parse task-manifest.csv for all 8 tasks
3. Match workflow.xml invocations to tasks

### Phase 2: Workflow Chain Detection (HIGH)
1. Scan workflow.yaml for workflow references
2. Parse instructions.xml for workflow names
3. Build workflow→workflow graph

### Phase 3: Self-Trace Mode (MEDIUM)
1. Add `--self-trace` flag
2. Include traceability/ directory
3. Generate self-trace matrix

### Phase 4: Version Snapshots (MEDIUM)
1. Add iteration counter
2. Timestamp each run
3. Compare snapshots (diff)

### Phase 5: Party Mode Integration (LOW)
1. Auto-trigger party mode on gaps
2. Multi-agent gap analysis
3. Consensus on priorities

---

## RECURSIVE LOOP

After improvements:
1. Run engine on itself
2. Verify new traces captured
3. Commit snapshot with version
4. Trigger next iteration if gaps remain

---

## OUTPUT

Generate findings report:
1. **Critical gaps** (blocking compound engineering)
2. **High-priority improvements** (enable recursion)
3. **Medium-priority enhancements** (better fidelity)
4. **Low-priority polish** (documentation, UX)
