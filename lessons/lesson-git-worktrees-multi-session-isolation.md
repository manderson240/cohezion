---
title: Git Worktrees for Multi-Session Work Isolation
date: 2026-02-10
severity: HIGH
category: tooling
tags: [git, workflow, multi-session, token-efficiency]
source: decisions/2026-02-09-session-46-git-unification-complete.md
status: validated
---

# Lesson: Git Worktrees for Multi-Session Work Isolation

## Context

When multiple agents or sessions work on the same repository concurrently, divergent histories can emerge (213 commits local vs 145 commits remote, no common ancestor). Unifying requires manual conflict resolution (30+ files) and risks data loss.

## Core Learning

**Use git worktrees or feature branches for concurrent multi-session work.**

### Why This Matters
- Prevents history divergence (0 common ancestors)
- Eliminates merge conflicts from concurrent edits
- Provides clear audit trail per session
- Enables independent testing/validation
- Zero interference between sessions

### Pattern
```bash
# Create worktree for new session
git worktree add ../cohezion-session-47 -b session-47

# Work in isolated directory
cd ../cohezion-session-47
# ... make changes, commit ...

# When done, merge back to main
cd ../cohezion
git merge session-47

# Clean up worktree
git worktree remove ../cohezion-session-47
```

## What Went Wrong

**Anti-pattern**: Multiple agents/sessions committing to same `main` branch simultaneously
- Local: 213 commits ahead
- Remote: 145 commits ahead
- Result: Completely diverged histories, no common ancestor
- Recovery: Manual merge with `--allow-unrelated-histories` + 30+ conflict resolutions

## What Worked

**Recovery solution**:
1. `git pull --no-rebase --allow-unrelated-histories`
2. Resolve conflicts (prefer local versions)
3. Create merge commit with clear documentation
4. Verify with full test suite (98.5% passing)
5. Push unified history

## Recommendations

### Do ✅
- Use git worktrees for concurrent sessions (primary)
- Use feature branches if worktrees not feasible (secondary)
- Commit frequently with clear messages
- Verify test results after merge
- Document merge strategy in commit message

### Don't ❌
- Let multiple sessions commit to `main` directly
- Assume remote and local are in sync without checking
- Skip conflict resolution (can cause data loss)
- Trust test counts without running full suite

## Applicability

**When to apply**:
- Multi-agent swarms working on same codebase
- Long-running sessions (4+ hours) with periodic commits
- Concurrent development by multiple team members
- Token-efficient workflows requiring isolation

**When NOT to apply**:
- Single-session, single-developer work (overkill)
- Read-only operations (no commit risk)
- Ephemeral environments (containers, temp dirs)

## Token Efficiency

**Cost of prevention** (worktrees): ~2 min setup, 0 tokens
**Cost of recovery** (diverged history): ~30 min merge + conflict resolution, ~10K tokens (reading diffs, resolving)
**ROI**: 15x time savings, ~10K token savings per divergence event

## Related Concepts

- [[compound-engineering]] - Multi-session isolation enables parallel compound work
- [[token-efficiency]] - Prevents wasted tokens on merge conflict resolution

## Validation

**Verified by**: Session 46 git unification (2026-02-09)
**Impact**: Prevented future divergence, established pattern for Sessions 47+
**Status**: Adopted as standard practice

## Implementation Checklist

- [ ] Create worktree for each new session
- [ ] Use naming convention: `session-{number}` or `feature-{name}`
- [ ] Verify worktree isolation before starting work
- [ ] Merge back to main when session complete
- [ ] Run full test suite after merge
- [ ] Clean up worktree after merge
- [ ] Document merge strategy in commit message

---

**Severity**: HIGH - Prevents data loss and wasted recovery effort
**Adoption**: Immediate (all future multi-session work)

## Related Papers

  - [[langchain-deep-agents-context-management]] (similarity: 0.67) — LangChain's filesystem offloading strategy for large tool responses parallels worktrees as isolation: both use filesystem boundaries to prevent session-to-session interference
  - [[openai-codex-agent-loop]] (similarity: 0.653) — the Codex agent loop's inner/outer architecture benefits from worktree isolation: each outer-loop session works on its own branch without interfering with concurrent sessions
  - [[scaling-agent-systems]] (similarity: 0.645) — git worktrees implement the paper's "centralized coordination" architecture: isolated branches (decentralized work) + merge review (centralized validation bottleneck)

## Scientific Foundation

- [[llm-in-sandbox-agentic-intelligence]] — git worktrees are a filesystem-level sandbox: each worktree is an isolated "virtual computer" (code, venv, state) that shares only the underlying `.git/objects`. This is structurally identical to the LLM-in-Sandbox framework — the agent gets full environment access without contaminating concurrent agents. Both achieve emergent multi-agent capability through isolation rather than coordination overhead.
- [[scaling-agent-systems]] — the 17.2x error amplification in independent non-isolated systems explains exactly why diverged git histories occur: each session committing to `main` directly is the "independent multi-agent" configuration the paper shows is worst-performing. Worktrees + merge review IS the "centralized coordinator bottleneck" the paper shows contains amplification to 4.4x.
