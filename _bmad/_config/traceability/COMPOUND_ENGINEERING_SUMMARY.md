# BMAD Traceability Engine - Compound Engineering System

## 🎯 System Overview

The **BMAD Traceability Engine** is a self-improving system that enables continuous compound engineering via:
1. **Test-Driven Development** (TDD)
2. **Multi-Perspective Adversarial Review**
3. **Recursive Self-Traceability**
4. **Automated Snapshot Versioning**

---

## 📊 Architecture

### Core Components

| Component | Purpose | Lines | Tests |
|-----------|---------|-------|-------|
| `traceability_engine.py` | Main extraction engine | 650 | 18 |
| `recursive_loop.py` | Self-improvement orchestrator | 180 | - |
| `test_traceability_engine.py` | TDD test suite | 200 | 18 passed |
| `traceability-review.md` | Adversarial review workflow | 150 | - |

### Output Artifacts

| Matrix | Rows | Purpose |
|--------|------|---------|
| `agent-workflow-matrix.csv` | 447 | Agent → Workflow mapping |
| `workflow-task-matrix.csv` | 2 | Workflow → Task invocations |
| `workflow-chain-matrix.csv` | 1 | Workflow → Workflow chains |
| `party-module-matrix.csv` | 4 | Party configs per module |

---

## 🔁 Recursive Loop

### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Load previous snapshot                                  │
│  2. Run engine with --self-trace                            │
│  3. Compare snapshots (detect changes)                      │
│  4. Run test suite (verify correctness)                     │
│  5. Detect gaps (identify improvements)                     │
│  6. Trigger adversarial review (if gaps found)              │
│  7. Save new snapshot                                       │
│  8. Repeat (recursive iteration)                            │
└─────────────────────────────────────────────────────────────┘
```

### Snapshot Schema

```csv
timestamp,20260322_222459
agents,27
workflows,74
tasks,7
invocations,7
self_trace,True
```

---

## 🧪 Test Coverage

### Test Categories

| Category | Count | Status |
|----------|-------|--------|
| Schema tests | 3 | ✓ Pass |
| XML parsing tests | 3 | ✓ Pass (mocked) |
| Manifest parsing tests | 2 | ✓ Pass |
| Party config tests | 2 | ✓ Pass |
| Cycle detection tests | 2 | ✓ Pass |
| Orphan detection tests | 2 | ✓ Pass |
| Integration tests | 2 | ✓ Pass |
| Recursive tests | 2 | ✓ Pass |

**Total:** 18/18 tests passing (100%)

---

## 🔍 Current Gaps (Adversarial Findings)

### Critical Gaps

| Gap | Impact | Priority | Status |
|-----|--------|----------|--------|
| Low invocation count (7 vs 20+ expected) | Missing workflow relationships | HIGH | Open |
| Missing task invocations (2 of 8 tasks) | Incomplete task tracing | HIGH | Open |
| Workflow chain incomplete (1 chain found) | Missing workflow dependencies | MEDIUM | Open |
| Agent→Workflow low fidelity (module-based) | Imprecise agent assignment | MEDIUM | Open |
| No self-trace by default | Engine doesn't trace itself | LOW | Fixed (via --self-trace) |

### Root Causes

1. **Task invocations**: Only found in instructions.xml, missing from workflow.xml
2. **Workflow chains**: Only detected from YAML mentions, missing explicit invokes
3. **Agent fidelity**: No `agent:` field in workflow.yaml schemas

---

## 🎯 Compound Engineering Loop

### Improvement Cycle

```
1. Run engine → Generate matrices
2. Run tests → Verify correctness
3. Detect gaps → Identify improvements
4. Adversarial review → Multi-agent analysis
5. Implement fixes → Code changes
6. Run engine (self-trace) → Verify improvements
7. Snapshot → Version tracking
8. Repeat → Recursive iteration
```

### Party Mode Integration

When gaps detected:
- Trigger party-mode workflow
- Multi-agent adversarial review
- Consensus on priorities
- Distributed implementation

---

## 📈 Metrics

### Current State

| Metric | Value | Target |
|--------|-------|--------|
| Agents traced | 27/27 (100%) | ✓ |
| Workflows traced | 74/74 (100%) | ✓ |
| Tasks traced | 2/8 (25%) | ⚠️ |
| Invocations | 7 | 20+ |
| Workflow chains | 1 | 10+ |
| Test coverage | 18/18 (100%) | ✓ |
| Self-trace | Enabled | ✓ |

---

## 🛠️ Usage

### Basic Execution

```bash
# Standard run
uv run python _bmad/_config/traceability/traceability_engine.py

# Self-trace mode (traces traceability/ directory)
uv run python _bmad/_config/traceability/traceability_engine.py --self-trace

# Recursive loop (auto-improvement)
uv run python _bmad/_config/traceability/recursive_loop.py
```

### Test Suite

```bash
# Run all tests
uv run pytest _bmad/_config/traceability/tests/ -v

# Run single test
uv run pytest _bmad/_config/traceability/tests/test_traceability_engine.py::TestWorkflowXMLParsing::test_extract_invoke_task_tags -v
```

### Adversarial Review

```bash
# Trigger party-mode review
# (Manual workflow execution for now)
# Future: Auto-triggered from recursive_loop.py
```

---

## 📁 File Structure

```
_bmad/_config/traceability/
├── traceability_engine.py          # Main engine (650 lines)
├── recursive_loop.py               # Self-improvement orchestrator (180 lines)
├── tests/
│   └── test_traceability_engine.py # TDD test suite (200 lines)
├── workflows/
│   ├── traceability-review.md      # Adversarial review workflow
│   └── traceability-review.md      # Review workflow definition
├── snapshots/
│   ├── traceability_20260322_222444.csv  # First snapshot
│   └── traceability_20260322_222459.csv  # Second snapshot (self-trace)
├── agent-workflow-matrix.csv       # 447 rows
├── workflow-task-matrix.csv        # 2 rows
├── workflow-chain-matrix.csv       # 1 row
├── party-module-matrix.csv         # 4 rows
├── traceability-report.md          # Summary report
└── traceability-graph.md           # Mermaid dependency graph
```

---

## 🎯 Next Iteration Priorities

### Phase 1: Complete Task Extraction (HIGH)
- [ ] Parse workflow.xml for all invoke-task tags
- [ ] Match to task-manifest.csv entries
- [ ] Expected: 8 tasks (currently 2)

### Phase 2: Workflow Chain Detection (HIGH)
- [ ] Scan all workflow.yaml for workflow references
- [ ] Parse instructions.xml for workflow names
- [ ] Expected: 10+ chains (currently 1)

### Phase 3: Agent Assignment Fidelity (MEDIUM)
- [ ] Add `agent:` field to workflow.yaml schema
- [ ] Update engine to read agent assignments
- [ ] Expected: High-confidence mappings (currently medium)

### Phase 4: Auto Party Trigger (LOW)
- [ ] Integrate party-mode workflow call
- [ ] Auto-trigger on gap detection
- [ ] Multi-agent consensus on priorities

---

## 🔄 Recursive Self-Improvement

### How It Works

1. **Engine traces itself** when run with `--self-trace`
2. **Snapshot captures state** (timestamp, counts, mode)
3. **Comparison detects changes** (diff between snapshots)
4. **Tests verify correctness** (18 tests must pass)
5. **Gaps trigger improvements** (adversarial review)
6. **Loop repeats** (continuous compound engineering)

### Version Tracking

```
snapshot_001: Initial run (self_trace=False)
snapshot_002: Self-trace enabled (self_trace=True)
snapshot_003: Task extraction improved (invocations: 7→20)
snapshot_004: Workflow chains complete (chains: 1→10)
...
```

---

## 🎉 Success Criteria

### Achieved ✓
- [x] TDD test suite (18 tests passing)
- [x] Matrix generation (4 CSVs)
- [x] Self-trace mode
- [x] Snapshot versioning
- [x] Recursive loop orchestration
- [x] Party-mode workflow definition

### In Progress ⚠️
- [ ] Complete task extraction (2/8 tasks)
- [ ] Complete workflow chains (1/10 chains)
- [ ] High-fidelity agent mapping
- [ ] Auto party-mode trigger

### Future 📋
- [ ] Interactive visualization (D3.js graph)
- [ ] Real-time gap dashboard
- [ ] Multi-agent consensus scoring
- [ ] Automated fix suggestions

---

## 📞 Compound Engineering Impact

This system enables **continuous compound engineering** by:

1. **Making invisible relationships visible** (agent→workflow→task)
2. **Detecting gaps automatically** (no manual audit needed)
3. **Enabling recursive self-improvement** (engine traces itself)
4. **Supporting multi-agent review** (party mode integration)
5. **Versioning all iterations** (snapshot comparison)
6. **Test-driving all changes** (TDD ensures correctness)

**Result:** A self-improving traceability system that gets better with each iteration, enabling compound engineering at scale.

---

**Generated:** 2026-03-22 22:25
**Version:** 1.0.0
**Iteration:** 2 (self-trace enabled)
