# Untracked Files Triage Analysis

**Date:** 2026-03-04  
**Total Untracked:** 752 files  
**Analysis Method:** Category-based with learning patterns

---

## 📊 Category Breakdown

| Category | Count | Analysis | Recommendation |
|----------|-------|----------|----------------|
| **tests/** | 153 | Test files, valid source code | TRACK - Add to git |
| **src/** | 152 | Source code, valid implementation | TRACK - Add to git |
| **.claude/** | 118 | Claude Code commands & worktrees | EVALUATE - Some should track |
| **.agent/** | 115 | BMAD agent configurations | EVALUATE - Core agents should track |
| **scripts/** | 48 | Driver scripts, utility code | EVALUATE - Production scripts track |
| **data/** | 29 | Data files, likely generated | IGNORE - Add to .gitignore |
| **apps/** | 24 | Web applications | EVALUATE - Core apps track |
| **reports/** | 9 | Generated reports | IGNORE - Add to .gitignore |
| **.github/** | 8 | GitHub configs | TRACK - Add to git |
| Root docs | ~40 | Documentation files | TRACK - Add to git |

---

## 🔍 Key Learnings from Wall of Red Pattern

### The `__GALLERY_OF_RED_CONTINUOUS.md` File

This file documents **continuous test/fix cycles** with:

```markdown
### RED-YYYY-MM-DD-###
**Date:** Date
**Time:** Hour X, Cycle Y
**Severity:** MEDIUM/HIGH/LOW
**Category:** Test Infrastructure

**Root Cause:**
- What caused the failure

**Learning:**
Tests should be created alongside infrastructure setup.

**Compound Value:**
Documentation of gap leads to infrastructure hardening.
```

### Learning
**These `__` prefixed files represent continuous loop session documentation** - they capture:
1. Test execution failures (RED states)
2. Root causes
3. Learnings
4. Compound metrics

**Recommendation:** These should be **TRACKED** as they represent institutional learning.

---

## 📁 Category Analysis

### 1. tests/ (153 files) - TRACK

**Pattern:** Test files with standardized structure:
- `tests/agents/` - Agent tests
- `tests/compound/` - Compound engineering tests
- `tests/api/` - API endpoint tests
- `tests/healing/` - Ouroboros healing tests

**Learnings:**
- Tests were created iteratively during development
- Some tests are integration tests requiring services
- `@pytest.mark.fast` marker used consistently

**Action:** Add all test files to git.

### 2. src/ (152 files) - TRACK

**Pattern:** Source code organized by module:
- `src/cohezion/compound/` - Compound engineering
- `src/cohezion/healing/` - Ouroboros immune system
- `src/cohezion/security/` - Security layer
- `src/cohezion/flume/` - FLUME VAE

**Learnings:**
- Contains core implementation
- Some files are INDEX.md (module documentation)
- All should be version controlled

**Action:** Add all source files to git.

### 3. .claude/ (118 files) - EVALUATE

**Pattern:** Claude Code worktrees and commands:
- `.claude/commands/bmad-agent-*.md` - Slash commands
- `.claude/worktrees/` - Isolated worktrees

**Learnings:**
- Commands should be shared for team consistency
- Worktrees are ephemeral and should NOT be tracked

**Action:** 
- Track `.claude/commands/` 
- Add `.claude/worktrees/` to .gitignore

### 4. .agent/ (115 files) - TRACK

**Pattern:** BMAD agent configurations:
- `.agent/workflows/` - Agent workflows
- `.agent/CONSTITUTION.md` - Core constraints
- `.agent/COHEZION_CHARTER.md` - Project charter

**Learnings:**
- These define the AI agent behavior
- Essential for reproducibility
- Already partially tracked

**Action:** Add missing .agent files to git.

### 5. Wall of Red Docs (~10 files) - TRACK

**Pattern:** Continuous loop session documentation:
- `__GALLERY_OF_RED_CONTINUOUS.md`
- `__FINAL_GREEN_STATE.md`
- `__OUROBOROS_REFINEMENT_COMPLETE.md`
- `__CONTINUOUS_LOOP_SUMMARY.md`

**Learnings:**
- These document the development journey
- Capture failures and recoveries
- Provide institutional memory

**Action:** MOVE to `docs/sessions/` and track.

---

## 🚫 Ignored Categories

### data/ (29 files) - IGNORE
Generated data files, database files, cache files.

### reports/ (9 files) - IGNORE
Auto-generated reports that can be regenerated.

### Build artifacts:
- `ruff_*.txt`, `mypy_*.txt` - Linter output
- `*.pyc`, `__pycache__/` - Python bytecode
- `node_modules/` - Node dependencies

---

## 📝 Recommended .gitignore Additions

```gitignore
# Generated data
data/
*.db
*.sqlite

# Linter output
ruff_*.txt
ruff_*.json
mypy_*.txt

# Build artifacts
__pycache__/
*.pyc
*.pyo

# Claude worktrees (ephemeral)
.claude/worktrees/

# Generated reports
reports/

# Temporary files
*.tmp
*.temp
EOF
```

---

## 🎯 Phase 1: Track Everything Critical

**Batch 1: Core Source Code**
```bash
git add src/cohezion/
git add tests/
git add scripts/
```

**Batch 2: Agent & Workflow Configs**
```bash
git add .agent/
git add .claude/commands/
git add .github/
```

**Batch 3: Documentation**
```bash
git add docs/
git add _bmad-output/
git add *.md
```

---

## 💡 Key Insights

### Pattern 1: Iterative Development Creates Many Files
Each development cycle generates:
- Test files
- Documentation
- Session logs

**Learning:** Need a "session completion" workflow to consolidate and commit.

### Pattern 2: Wall of Red as Institutional Memory
The RED files capture failure → learning cycles:
- What broke
- Why it broke
- How we fixed it
- What we learned

**Learning:** This is valuable documentation, not noise.

### Pattern 3: Agent Configs Should Be Versioned
The `.agent/` and `.claude/commands/` define how AI agents work.

**Learning:** Losing these means losing reproducibility.

---

_Save this analysis to vault for transparency._