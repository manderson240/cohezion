---
title: "PRIME_CLAUDE_CODE_PRACTICES"
date: 2026-02-12
status: template
tags: [governance, claude-code, prime-skill, platform-health, executable-procedure]
version: 1.0
charter_alignment: ["S01_Intentionality", "S02_Execution_Excellence", "S05_Observability"]
aspect: thinker
neural:
  activation: 0.99
  stage: growing
  synapse_in: 16
  synapse_out: 9
---

# PRIME_CLAUDE_CODE_PRACTICES

> **Executive Summary**: Codified procedures for context-aware Claude Code usage, minimizing uninformed mistakes and maximizing platform intelligence. Executable by agents + operators.

---

## 📋 Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | PRIME_CLAUDE_CODE_PRACTICES |
| **Version** | 1.0 |
| **Author** | Platform Lead (Session 57) |
| **Last Updated** | 2026-02-12 |
| **Status** | Proposed → Testing → Production |
| **Charter Alignment** | S01, S02, S05, S06 |
| **ROI** | 2,500 tokens per instantiation = 10:1 return |
| **Applicability** | All Claude Code sessions, agents, operators |
| **Review Cadence** | Monthly (metrics-driven iteration) |

---

## 🎯 Concepts (6 Core Ideas)

### 1. **Tool Selection Discipline**
**Principle**: Use specialized tools (Read, Edit, Glob, Grep) instead of Bash equivalents.

**Why**: Better UX, transparent to user, faster execution, better security (no shell injection)

**Anti-patterns**:
- `cat file.txt` → **USE** `Read` instead
- `grep pattern file.txt` → **USE** `Grep` instead
- `find . -name "*.ts"` → **USE** `Glob` instead
- `sed 's/old/new/' file.txt` → **USE** `Edit` instead

**Decision Tree**:
```
Need to read a file?
├─ Single file → Read
├─ Pattern search (content) → Grep
├─ Pattern search (filenames) → Glob
└─ Modify text? → Edit

Need to execute a command?
├─ Git/npm/docker/shell ops → Bash
├─ File operations → Read/Edit/Write/Glob/Grep
└─ Python/other language → Bash (with full path to venv)
```

---

### 2. **Parallelization Strategy**
**Principle**: Call independent tools together to maximize efficiency.

**When**: Tools have no dependencies (e.g., reading 3 separate files, 2 glob searches)

**When NOT**: One tool's output feeds into another (e.g., Read → Edit)

**Examples**:
✅ **Parallel**:
```
Read file A
Read file B
Glob pattern X
→ All executed together (single response block)
```

❌ **Sequential**:
```
Read file A
Edit based on file A contents
→ Separate calls (depends on previous result)
```

**Expected Gains**: 30-50% time savings per session

---

### 3. **Agent Delegation Triggers**
**Principle**: Spawn specialized agents for complex, multi-step, or research-heavy tasks.

**Agent Types** & When to Use:

| Agent | Cost | Use When | Examples |
|-------|------|----------|----------|
| **Explore** | Low | Fast pattern matching + codebase analysis | "Find all endpoints", "Search for class Foo" |
| **Plan** | Low | Architecture + implementation strategy | "Design the auth flow", "Refactor the module" |
| **general-purpose** | Medium | Multi-step research + execution | "Implement feature X with tests" |
| **Bash** | Low | Terminal operations (git, builds, tests) | "Run tests", "Deploy to staging" |

**Decision Tree**:
```
Is this task complex/multi-step?
├─ YES: Can it run in parallel with other work?
│   ├─ YES → Spawn agent in background
│   └─ NO → Spawn agent sequentially
└─ NO: Do it inline (save agent overhead)

Is this a search/exploration task?
├─ YES: Is it simple + directed? (specific file/class)
│   ├─ YES → Use Glob/Grep directly
│   └─ NO → Spawn Explore agent (multi-round search)
└─ NO: Proceed with appropriate agent type
```

---

### 4. **Memory System Usage**
**Principle**: Persist knowledge across sessions; don't repeat work.

**What to Save** (to `/home/mike-anderson/.claude/projects/-home-mike-anderson-vaults-cohezion-vault/memory/`):
- ✅ Patterns you use repeatedly
- ✅ Project conventions + decisions
- ✅ Lessons learned from mistakes
- ✅ Infrastructure setup details
- ✅ Service endpoints + credentials (marked as secrets)

**What NOT to Save**:
- ❌ Session-specific context
- ❌ Incomplete or speculative information
- ❌ Duplicates of CLAUDE.md or project docs
- ❌ In-progress work details

**Example Memory Entry** (from your vault):
```markdown
## Agent Economics
- Web research agents: Use Haiku + max_turns=5-10 (1/3 cost, 2x faster)
- Token efficiency: ~20K tokens/batch (Haiku) vs 100K+ (Sonnet)
- Template reuse: Always check for working templates before building from scratch
```

**Expected ROI**: 5-10K tokens saved per session

---

### 5. **MCP Integration Awareness**
**Principle**: Know what MCP tools are available; use them to augment work.

**Available MCPs** (in your vault):
- **Cloud Vault MCP** (port 8360): VaultOps, CompoundOps, ObsidianOps, Teleport, SheetsBridge, SurrealDB
- **Ollama MCP** (port 22360): query, embed, batch, select_model

**When to Use**:
- Need to query vault programmatically? → Cloud Vault MCP tools
- Need embeddings or semantic search? → Ollama embed
- Need to analyze codebase + vault together? → Both MCPs

**Example Workflow**:
```
Task: Find papers related to "distributed consensus" + link to decisions

Method 1 (Sub-optimal): Manual search, manual linking
Method 2 (Optimal):
  1. Use Ollama embed to find papers
  2. Use Cloud Vault query to find related decisions
  3. Use ObsidianOps to create wiki-links automatically
```

---

### 6. **Git Safety Protocol**
**Principle**: Prevent accidental destructive operations; confirm risky actions first.

**Safe Operations** (no confirmation needed):
- `git status`, `git diff`, `git log`
- `git add [specific files]`
- `git commit -m "message"`
- `git push` to feature branches
- `git stash` for temporary work

**Risky Operations** (ALWAYS confirm first):
- `git push --force` to any branch
- `git reset --hard` / `git restore` / `git clean`
- Force-pushing to main/master
- Deleting branches (`git branch -D`)
- Amending published commits
- Rebasing published commits

**Confirmation Template**:
```
Before destructive operation, explicitly ask:
"I'm about to [specific action]. This will [consequence]. OK to proceed?"
```

---

## 📖 Instructions (12 Procedural Rules)

### Rule 1: Read Files First (Non-Negotiable)
**Always** read a file before editing or suggesting changes.
- **Why**: Understand existing code, preserve formatting, prevent breaking changes
- **How**: Use Read tool (supports 2000 lines default)
- **Exception**: If file doesn't exist (explicitly OK to skip)

```python
# WRONG
"Let me add error handling to line 42"
# (without reading file first)

# RIGHT
1. Read the file
2. "I see the function at line 35-50. I'll add error handling here..."
```

---

### Rule 2: Use Specialized Tools for File Operations
**NEVER** use Bash for file operations when a dedicated tool exists.

**Tool Selection**:
| Task | Tool | Bash | Status |
|------|------|------|--------|
| Read file | Read | ❌ | ALWAYS use Read |
| Search content | Grep | ❌ | ALWAYS use Grep |
| Find files | Glob | ❌ | ALWAYS use Glob |
| Edit file | Edit | ❌ | ALWAYS use Edit |
| Create file | Write | ❌ | ALWAYS use Write |
| Run command | Bash | ✅ | Only for commands |

---

### Rule 3: Parallelize Independent Operations
**When**: Multiple independent reads/searches needed
**How**: Call all tools in single block
**Expected**: 30-50% time savings

```
❌ Sequential (slow):
  1. Read file A
  2. Read file B
  3. Glob pattern X
  → 3 separate round-trips

✅ Parallel (fast):
  Call Read(A), Read(B), Glob(X) together
  → 1 round-trip, all results returned
```

---

### Rule 4: Know Your Token Budget
**Current**: 17% usage (34k/200k) = 133k tokens free

**Strategy**:
- **Simple tasks** (under 50k): Execute inline
- **Complex tasks** (50-100k): Delegate to agents
- **Research-heavy tasks** (100k+): Spawn agents + parallelize

**Avoid**: Keeping large results in context. Use agents → collect JSON → update files.

---

### Rule 5: Confirm Risky Operations Before Executing
**Risky**: Push, force-push, hard reset, branch deletion, file deletion

**Process**:
1. Identify operation is risky
2. Explicitly state consequence
3. Ask for confirmation
4. Wait for user approval
5. Execute after approval

```
"I'm about to force-push to main to squash commits. This will
overwrite upstream history. Only do this if you've coordinated
with the team. OK to proceed?"
```

---

### Rule 6: Avoid Destructive Shortcuts
**Principle**: Don't use `-f`, `--no-verify`, `--hard`, etc. to bypass safety checks.

**When Stuck**:
- Investigate root cause instead of forcing
- Try alternative approaches
- Ask user for guidance
- Never bypass safety checks without explicit authorization

---

### Rule 7: Use Venv Python (Not Bare `python3`)
**CRITICAL** for your vault project:

```bash
# ❌ WRONG
python3 script.py

# ✅ RIGHT
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 script.py
```

**Why**: Isolated dependencies, reproducible environment, matches CI/CD

---

### Rule 8: Create Task Lists for Complex Work
**When**: Task requires 3+ steps or involves multiple agents

**Format**:
- Subject: Imperative ("Fix auth bug")
- Description: Full context + acceptance criteria
- Track: Mark in_progress before starting, completed after finishing

**Benefits**: User visibility, team coordination, compound context

---

### Rule 9: Respect Existing Patterns
**Principle**: Follow conventions established in the project.

**In Your Vault**:
- Frontmatter: title, date, status, tags
- Directories: decisions/, patterns/, papers/, lessons/
- Templates: Use _template.md as reference
- Wiki-links: Use `[[note-name]]` for cross-references
- Commits: Follow existing message style

---

### Rule 10: Plan Before Implementing (For Non-Trivial Changes)
**When**: New feature, significant refactor, architectural change

**Process**:
1. Use EnterPlanMode to propose approach
2. Explore codebase + understand context
3. Design implementation strategy
4. Get user approval
5. Execute approved plan

**Expected**: Better alignment, fewer false starts

---

### Rule 11: Test After Code Changes
**What**: Run existing tests, add new tests for new code

**How**: Use Bash to run test suite
```bash
cd /repo && pytest tests/ -v
```

**Rule**: Don't commit code with failing tests

---

### Rule 12: Track Decisions & Metrics
**What**: Record significant decisions in decisions/ directory

**When**: Architectural choice, big change, lesson learned

**Format**: ADR template (Context, Decision, Consequences, Alternatives)

---

## 💡 Examples (Real Scenarios)

### Example 1: Tool Selection Mistake → Recovery

**Scenario**: Need to search for a function name across 50 files

**❌ WRONG (Anti-pattern)**:
```
bash command: find . -name "*.py" -exec grep -l "function_name" {} \;
```
**Problem**: Bash command is opaque, harder to understand, less safe

**✅ RIGHT (Correct)**:
```
1. Glob("**/*.py") to find Python files
2. Grep("function_name", glob_results) to search content
→ Both called together (parallel)
```

**Impact**: Same result, better UX, 30% faster

---

### Example 2: Parallelization Success

**Scenario**: Setup task requires reading 3 config files + finding all handlers

**❌ Sequential** (3 round-trips, 1.5min):
```
1. Read ~/.claude/mcp.json
2. Read CLAUDE.md
3. Read cloud-vault-mcp/config.py
4. Glob for handler files
→ Separate calls, wait between each
```

**✅ Parallel** (1 round-trip, 0.5min):
```
Call all 4 in single block:
- Read ~/.claude/mcp.json
- Read CLAUDE.md
- Read cloud-vault-mcp/config.py
- Glob for handler files
→ All results returned together
```

**Impact**: 66% faster, same information

---

### Example 3: Agent Delegation Smart Choice

**Scenario**: "Implement OAuth flow in React app with tests"

**❌ Inline** (Wrong):
- Can't parallelize code writing + testing
- 1000+ LOC in single conversation
- Context bloat

**✅ Agent Delegation** (Correct):
```
1. Spawn general-purpose agent with scope:
   - Implement OAuth component
   - Write integration tests
   - Document setup
2. Meanwhile, work on other tasks
3. Agent reports back when complete
→ 70% time savings via parallelization
```

**Impact**: Non-blocking progress on multiple tasks

---

### Example 4: Memory System ROI

**Scenario**: New session, you notice this pattern in MEMORY.md:
```markdown
### Python Environment
- ALWAYS use: `/home/mike-anderson/dev/cohezion/.../venv/bin/python3`
- NEVER use: bare `python3`
```

**Impact**:
- ✅ Operator reads once (5 seconds)
- ✅ Agents follow automatically
- ✅ 3 sessions × 5 min of debugging saved = 15 min ROI
- ✅ Memory cost: 100 tokens

**ROI**: 15 * 60 / 100 = 9:1

---

### Example 5: Git Safety Protocol

**Scenario**: Need to rebase feature branch before merging

**❌ Unsafe**:
```
"Running: git rebase -i main --no-verify"
(force-rebasing without confirmation)
```

**✅ Safe**:
```
"I need to rebase this branch onto main to clean up commits.
This will rewrite history (safe for feature branches, not for main).
Is this OK?"

(waits for confirmation before executing)
```

**Impact**: Prevents accidental history destruction

---

## 📈 Evolution History (Tracked Monthly)

| Version | Date | Changes | Metrics Impact |
|---------|------|---------|-----------------|
| 1.0 | 2026-02-12 | Initial PRIME codification | Baseline |
| 1.1 | TBD (1 month) | Rule refinements based on metrics | ±10% efficiency |
| 1.2 | TBD (2 months) | New concepts from lessons learned | +15-20% |
| 2.0 | TBD (3 months) | Full integration with automation | +30-50% |

---

## ✅ Validation Checklist

Before marking PRIME_CLAUDE_CODE_PRACTICES as "Production", verify:

- [ ] **Rules 1-12 Understood**: Can operators explain each rule in their own words
- [ ] **Tool Selection**: Operators correctly identify when to use Read vs Bash vs Glob vs Edit
- [ ] **Parallelization**: At least 50% of multi-tool sessions use parallelization
- [ ] **Agent Delegation**: Complex tasks (4+ steps) delegated to agents instead of inline
- [ ] **Git Safety**: Zero force-push incidents; all risky ops confirmed first
- [ ] **Memory Reuse**: MEMORY.md referenced + used in 70%+ of sessions
- [ ] **MCP Tools**: At least 2 MCP tools used per week in compound operations
- [ ] **Metrics Tracked**: Daily logs show mistake categories + prevention rate

---

## 🏛️ Charter Alignment

### S01: Intentionality
**How**: Rules encode explicit intention (why tool X, not bash; why parallel, not sequential)

### S02: Execution Excellence
**How**: Procedures automate quality checks (Rule 1: read first; Rule 5: confirm risky ops)

### S05: Observability
**How**: Metrics track adoption, mistake prevention, efficiency gains

### S06: Compound Engineering
**How**: Knowledge layers (policy → procedure → metrics) compound improvements over time

---

## 📞 Support & Iteration

**Questions about a rule?**
- Review the rule's decision tree
- Check the examples
- Ask in session (will inform v1.1 refinements)

**Discover a mistake prevention pattern?**
- Document in daily log
- Link to this skill via decision
- Propose as new rule in monthly review

**Found a gap in the concepts?**
- Note it in evolution history
- Propose new rule with examples
- Track metrics impact over 1 month

---

## Implementation Status

| Component | Status | Owner | Timeline |
|-----------|--------|-------|----------|
| Policy (CLAUDE.md) | Proposed | Platform Lead | 2026-02-12 (30 min) |
| Procedure (This skill) | Template | Platform Lead | 2026-02-12 (complete) |
| MCP Indexing | Proposed | Integration Eng | 2026-02-12 (15 min) |
| Metrics Tracking | Proposed | Session Leads | 2026-02-12+ (15 min/week) |
| Validation (2 weeks) | Proposed | All agents | 2026-02-26 |

---

**Last Updated**: 2026-02-12
**Next Review**: 2026-03-12 (1 month metrics cycle)

## Related Concepts

- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-13-phase-2-execution-strategy-wave-2]]
- [[2026-02-12-platform-codification-summary-guide]]
- [[2026-02-13-session-60-retrospective-and-revised-plan]]
- [[_claude-code-metrics-2026-02-14]]
- [[_claude-code-metrics-template]]
- [[2026-02-10-telemetry-corruption-fix]]
