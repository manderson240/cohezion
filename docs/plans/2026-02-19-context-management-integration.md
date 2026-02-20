# Context Management Integration Plan

Created: 2026-02-20
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Integrate Claude Code context management best practices — restructure CLAUDE.md with @ file references, create CODE_MAP.md for source navigation, add CLAUDE.local.md with practical examples, and document the patterns.

**Architecture:** Leverage Claude Code's @ mention system to reference key files directly from CLAUDE.md, reducing context pollution while improving discoverability. Create dedicated code map for source navigation. Provide local customization examples.

**Tech Stack:** Markdown files with @ reference syntax, no code changes required

## Scope

### In Scope

- Add @ Reference Files section to CLAUDE.md (top of file)
- Convert inline file mentions to @ syntax throughout CLAUDE.md
- Create docs/CODE_MAP.md with @ references to key source modules
- Create CLAUDE.local.md with practical examples (personal workflows, context optimization, tool integration, compound engineering)
- Add .gitignore entry for CLAUDE.local.md (should not be committed)
- Update docs/DEVELOPMENT.md with context management best practices section

### Out of Scope

- Changes to source code or existing .claude/rules files (those are already well-structured)
- Modifications to testing infrastructure
- MCP server configuration changes

## Prerequisites

- None - this is documentation only

## Context for Implementer

> This section is critical for cross-session continuity. Write it for an implementer who has never seen the codebase.

- **Patterns to follow:** Check .claude/rules/git-workflow.md:1-23 for examples of frontmatter with path triggers (not used in CLAUDE.md but good reference for rule files)
- **Conventions:** CLAUDE.md uses markdown with code blocks, tables, and clear section headers. Maintain current formatting style
- **Key files:**
  - Current CLAUDE.md is 610 lines at root
  - .claude/rules/ has specialized rule files (don't modify these)
  - No CLAUDE.local.md exists yet (we'll create it)
- **Gotchas:**
  - @ references work like `@file/path.py` - Claude will include that file's contents automatically
  - CLAUDE.local.md should NEVER be committed (personal customization only)
  - The file paths in @ mentions must be relative to project root
- **Domain context:**
  - Cohezion is a compound AI orchestration system with FLUME VAE, multi-agent swarm, and skill refinement
  - Critical files include governance docs (.agent/CONSTITUTION.md, COHEZION_CHARTER.md), testing infrastructure (tests/conftest.py), and configuration (pyproject.toml, pytest.ini)

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Create @ Reference Files Section in CLAUDE.md
- [x] Task 2: Convert Inline File Mentions to @ Syntax
- [x] Task 3: Create docs/CODE_MAP.md
- [x] Task 4: Create CLAUDE.local.md with Examples
- [x] Task 5: Update .gitignore and docs/DEVELOPMENT.md

**Total Tasks:** 5 | **Completed:** 5 | **Remaining:** 0

## Implementation Tasks

### Task 1: Create @ Reference Files Section in CLAUDE.md

**Objective:** Add a dedicated "## @ Reference Files" section at the top of CLAUDE.md (after the summary paragraph) that lists all critical files with @ mentions, organized by category.

**Dependencies:** None

**Files:**
- Modify: `CLAUDE.md`

**Key Decisions / Notes:**
- Place section after the opening summary, before "## Token-Efficient Essentials"
- Organize into subsections: Governance & Charter, Configuration, Testing Infrastructure, Documentation
- Each @ mention should have a brief description (1 line) of why it's important
- Follow pattern: `- @path/to/file.ext - Brief description of file's purpose`

**Definition of Done:**
- [ ] @ Reference Files section exists in CLAUDE.md after the summary
- [ ] Section includes subsections for: Governance, Configuration, Testing, Documentation
- [ ] All critical files from exploration are @ referenced:
  - `.agent/CONSTITUTION.md`
  - `.agent/COHEZION_CHARTER.md`
  - `.agent/HARDWARE_PROFILE_PRIME.md`
  - `tests/conftest.py`
  - `pytest.ini`
  - `pyproject.toml`
  - `.mcp.json`
- [ ] Each @ reference has a one-line description
- [ ] No linting errors in markdown

**Verify:**
- Read CLAUDE.md and confirm @ Reference Files section exists with all required files
- Verify @ syntax is correct (format: `@path/to/file`)

### Task 2: Convert Inline File Mentions to @ Syntax

**Objective:** Replace existing text-only file references throughout CLAUDE.md with @ mentions where those files are discussed in context (e.g., in "Critical References" table, "Test Isolation" section, etc.)

**Dependencies:** Task 1 (so we don't duplicate @ references)

**Files:**
- Modify: `CLAUDE.md`

**Key Decisions / Notes:**
- Focus on the "Critical References" table (lines 265-276) — convert file path column to @ references
- In "Test Isolation" section (lines 183-187) — convert `tests/conftest.py` mention to @tests/conftest.py
- In other sections where specific files are mentioned as examples, add @ references
- Keep the @ Reference Files section as the canonical list; inline mentions are supplementary

**Definition of Done:**
- [ ] "Critical References" table updated with @ syntax for file paths
- [ ] `tests/conftest.py` in "Test Isolation" section uses @ syntax
- [ ] Other file mentions (e.g., in code examples) converted to @ where it adds value
- [ ] No broken references or syntax errors

**Verify:**
- Search CLAUDE.md for old-style file paths (e.g., `tests/conftest.py` without @)
- Verify @ syntax matches files that exist in the project

### Task 3: Create docs/CODE_MAP.md

**Objective:** Create a new file `docs/CODE_MAP.md` that provides @ references to all key source code modules, organized by architecture layer (Compound, Swarm, Cache, etc.)

**Dependencies:** None

**Files:**
- Create: `docs/CODE_MAP.md`

**Key Decisions / Notes:**
- Mirror the "Architecture at a Glance" table from CLAUDE.md but with @ references to actual source files
- Organize by layers: Compound, Swarm, Cache, Cost Optimization, Persistence, Knowledge
- Each entry should have: Module name, @ reference to file, and brief description of purpose
- Include link from CLAUDE.md to CODE_MAP.md in the Architecture section

**Definition of Done:**
- [ ] docs/CODE_MAP.md exists with header explaining purpose
- [ ] File organized by architecture layers matching CLAUDE.md structure
- [ ] @ references for key modules:
  - Compound: `src/cohezion/compound/executor.py`, `journey_tracker.py`, `skill_refiner.py`
  - Swarm: `src/cohezion/swarm/team_executor.py`, `cost_aware_router.py`
  - Cache: `src/cohezion/cache/semantic_cache.py`
  - Persistence: `src/cohezion/persistence/surreal_client.py`
  - API: `src/cohezion/api/__init__.py`
- [ ] Link to CODE_MAP.md added in CLAUDE.md "Architecture at a Glance" section

**Verify:**
- `cat docs/CODE_MAP.md` — file exists with @ references
- Verify all @ referenced files actually exist
- Check link from CLAUDE.md works

### Task 4: Create CLAUDE.local.md with Examples

**Objective:** Create a new CLAUDE.local.md file at project root with practical examples for: personal development workflows, context optimization tips, tool integration, and compound engineering workflows.

**Dependencies:** None

**Files:**
- Create: `CLAUDE.local.md`

**Key Decisions / Notes:**
- This file is for personal customization and should NOT be committed
- Include header explaining this is for personal use
- Provide 4 main sections based on user requirements:
  1. Personal Development Workflows (custom test fixtures, debug configs)
  2. Context Optimization Tips (using @ mentions strategically)
  3. Integration with Tools (IDE, git hooks, scripts)
  4. Compound Engineering Workflows (skill refinement, journey tracking)
- Each section should have concrete, copy-pasteable examples
- Use @ references to show best practices
- Include edge case examples (e.g., working with large files, handling context limits)

**Definition of Done:**
- [ ] CLAUDE.local.md exists at project root
- [ ] Header explains this is for personal customization only
- [ ] Section 1: Personal Development Workflows with 2-3 examples
- [ ] Section 2: Context Optimization Tips with @ reference examples
- [ ] Section 3: Integration with Tools with practical configs
- [ ] Section 4: Compound Engineering Workflows with Cohezion-specific examples
- [ ] Edge case examples included (handling large files, context limits)
- [ ] Examples use actual Cohezion files/patterns

**Verify:**
- `cat CLAUDE.local.md` — file exists with all 4 sections
- Examples are practical and copy-pasteable
- @ references point to real files

### Task 5: Update .gitignore and docs/DEVELOPMENT.md

**Objective:** Add CLAUDE.local.md to .gitignore (so it's never committed) and update docs/DEVELOPMENT.md with a "Context Management Best Practices" section explaining how to use @ mentions, CLAUDE.md structure, and the three file locations.

**Dependencies:** Tasks 1-4 (so documentation reflects completed state)

**Files:**
- Modify: `.gitignore`
- Modify: `docs/DEVELOPMENT.md`

**Key Decisions / Notes:**
- Add `CLAUDE.local.md` to .gitignore near other editor-specific ignores
- In DEVELOPMENT.md, add new section after existing content
- Explain the three CLAUDE.md locations: root (shared), CLAUDE.local.md (personal), ~/.claude/CLAUDE.md (global)
- Document @ reference syntax and when to use it
- Link to CODE_MAP.md for source navigation
- Provide examples from CLAUDE.local.md

**Definition of Done:**
- [ ] `.gitignore` includes `CLAUDE.local.md`
- [ ] docs/DEVELOPMENT.md has new "Context Management Best Practices" section
- [ ] Section explains:
  - Three CLAUDE.md file locations and their purposes
  - @ reference syntax and best practices
  - How to use CODE_MAP.md for source navigation
  - Link to CLAUDE.local.md examples
- [ ] README.md mentions CLAUDE.local.md as optional personal config (or note added to DEVELOPMENT.md about how users discover it)
- [ ] Examples are clear and actionable

**Verify:**
- `grep "CLAUDE.local.md" .gitignore` — entry exists
- Read docs/DEVELOPMENT.md section — complete and helpful
- Verify git status shows CLAUDE.local.md as ignored (if it exists)

## Testing Strategy

- No automated tests needed (documentation only)
- Manual verification: Read each updated file to ensure clarity and correctness
- Verification: Check that @ references point to files that actually exist
- Edge case testing: Try loading CLAUDE.md and verify no errors from @ references

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| @ references break if files are moved | Medium | Low | Use relative paths; document in DEVELOPMENT.md that file moves require updating @ references |
| CLAUDE.local.md accidentally committed | Low | Low | Add to .gitignore; document clearly that it's personal only |
| Context bloat from too many @ references | Low | Medium | Only @ reference files that are frequently needed; CODE_MAP.md exists for deep dives |
| Inline @ references duplicate section | Low | Low | Keep @ Reference Files section as canonical; inline mentions are contextual supplements |

## Open Questions

_None remaining after clarification phase_

### Deferred Ideas

- Automatic validation of @ references (script to check all @ mentions point to real files) - could be added later if needed
- Path-based triggers in CLAUDE.md (like .claude/rules files) - not needed since CLAUDE.md always loads
