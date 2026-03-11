---
title: Stale Branch Mining: Old Branches Contain Valuable Abandoned Work
date: 2026-02-23
severity: MEDIUM
category: git
cost_of_forgetting: "Re-implementing features that were already partially built on abandoned branches; lost learning from failed experiments"
tags: [git, branches, knowledge-recovery, archaeology]
status: validated
aspect: knower
neural:
  activation: 0.454
  stage: growing
  cluster: lessons
---

# Lesson: Stale Branch Mining: Old Branches Contain Valuable Abandoned Work

## Context

During Cohezion repository archaeology in February 2026, a new feature was being implemented that required embedding pipeline optimization. Before starting from scratch, the developer checked stale branches and discovered `feature/embedding-cache-v2` -- an abandoned branch from a previous session that contained a working batch cache implementation. The code needed minor updates but saved an estimated 2-3 hours of implementation time. A subsequent audit found 4 more stale branches with recoverable work.

## Problem

Stale branches accumulate silently in repositories. They represent abandoned work, but the reason for abandonment varies:

1. **Context switch**: Work was interrupted by a higher priority task and never resumed
2. **Approach changed**: A different architectural approach was chosen, but the original implementation was partially working
3. **Session boundary**: A compound engineering session ended, and the next session started fresh instead of continuing

In all cases, the branch contains useful artifacts: working code, passing tests, informative error traces from failed approaches, and design exploration that informs future decisions. Without active mining, this knowledge is invisible.

## Core Learning

**Before starting new work, mine stale branches for prior art. Check for abandoned implementations that can be resurrected.**

### Pattern
```bash
# List stale branches sorted by last commit
git for-each-ref --sort=-committerdate refs/heads/ \
  --format='%(refname:short) %(committerdate:relative)'

# Diff to extract code
git diff main...feature/old-attempt -- src/relevant_module.py

# Cherry-pick valuable commits
git cherry-pick abc1234
```

## Solution

Stale branch mining is now a standard step at the beginning of new feature work:

1. **List branches**: `git for-each-ref --sort=-committerdate` to see all branches ordered by recency
2. **Search by keyword**: `git branch -a | grep embedding` to find branches related to the current feature
3. **Diff for relevant code**: `git diff main...branch -- src/relevant/` to see what changed
4. **Cherry-pick or copy**: Extract valuable code and tests into the current branch
5. **Document lessons**: If the branch contains a failed experiment, document why it failed

## Prevention

- **Mine before building**: Make branch audit the first step of new feature work
- **Tag valuable abandoned branches**: Before context switching, tag the branch with a description of what is working
- **Never delete without review**: Before `git branch -D`, review the branch contents
- **Write continuation notes on branches**: If a branch is being abandoned, commit a note explaining what is done and what remains

## Cost of Forgetting

- **Duplicated effort**: Re-implementing features that were already partially built
- **Lost learning**: Failed experiments on abandoned branches contain valuable "what not to do" knowledge
- **Missed tests**: Abandoned branches often contain passing tests that are more comprehensive than what a fresh implementation would write

## Recommendations

### Do
- Run stale branch audit at the start of new feature work
- Extract passing tests from abandoned branches even if implementation was abandoned

### Don't
- Delete stale branches without reviewing them first

## Related Concepts

- [[compound-engineering]] - Prior work compounds forward, even failed attempts
- [[lesson-37-experience-guided-execution-works-new]] - stale branch mining is a form of experience-guided execution: using prior session output to accelerate current work
- [[session-retrospective]] - retrospectives can identify which branches contain recoverable work
- [[lesson-git-worktrees-multi-session-isolation]] - worktree branches are a common source of stale branches with valuable work

## Validation

**Discovered**: Feb 2026 during repository archaeology
**Impact**: Recovered 2-3 hours of implementation time from abandoned branches
**Status**: Validated -- recovered usable code from multiple stale branches
