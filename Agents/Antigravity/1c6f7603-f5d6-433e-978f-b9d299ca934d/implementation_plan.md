---
type: antigravity-artifact
session_id: 1c6f7603-f5d6-433e-978f-b9d299ca934d
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.322
  stage: embryo
  cluster: Agents
---

# Implementation Plan: Git Worktree Automation

The goal is to automate the mandatory git worktree pattern in the Cohezion project. Currently, sessions are set up manually following documentation. This plan introduces a `session.py` script to automate startup, validation, and cleanup.

## Proposed Changes

### Scripts

#### [NEW] [session.py](file:///home/mike-anderson/dev/cohezion/scripts/session.py)
A Python CLI tool using `argparse` to:
- `start`: Find the next session ID, create a branch (`session-XX-phase-name`), add a git worktree, and run the validator.
- `status`: List active session worktrees and their branches.
- `clean`: Safely remove a session worktree and its branch after verification.

### Documentation

#### [MODIFY] [CLAUDE.md](file:///home/mike-anderson/dev/cohezion/CLAUDE.md)
Update the "MANDATORY: Multi-Session Git Worktree Pattern" section to recommend using `python scripts/session.py start`.

#### [MODIFY] [GIT_WORKTREE_WORKFLOW.md](file:///home/mike-anderson/dev/cohezion/GIT_WORKTREE_WORKFLOW.md)
Update the operational guide to reflect the new automated workflow.

## Verification Plan

### Automated Tests
1. **Creation Test**:
   - Run `python scripts/session.py start --phase integration-test`
   - Verify:
     - Directory `~/dev/cohezion-session-XX` exists.
     - Branch `session-XX-integration-test` exists and is checked out in that worktree.
     - `scripts/validate-session-setup.sh` returns success in the new worktree.
2. **Cleanup Test**:
   - Run `python scripts/session.py clean --session XX`
   - Verify:
     - Worktree is removed.
     - Branch is deleted (or warned if unmerged).

### Manual Verification
1. User can run `python scripts/session.py status` to see all current active worktrees.

## Related Vault Notes

- [[cohezion]]
