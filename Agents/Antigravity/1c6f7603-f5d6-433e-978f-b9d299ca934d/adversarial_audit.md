---
type: antigravity-artifact
session_id: 1c6f7603-f5d6-433e-978f-b9d299ca934d
date: 2026-03-04
title: "Adversarial Audit"
aspect: doer
neural:
  activation: 0.65
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Adversarial Audit: Git Worktree Automation (`session.py`)

## 1. Red Team Analysis (Vulnerabilities)

### A. The "Ghost Progress" Risk
**Scenario**: An agent finishes work in a worktree, runs `session.py clean`, but forgot to `git push`.
**Impact**: Permanent loss of uncommitted or unpushed work if the script uses `--force`.
**Vulnerability**: Normal `git worktree remove` prevents deletion of modified files, but does NOT check if the local branch is ahead of the remote.

### B. Database Collision (Shared State)
**Scenario**: Two sessions (Session 47 and Session 48) run `uv run pytest` simultaneously.
**Impact**: Tests fail or corrupt data because they both hit `ws://localhost:8000/rpc` (SurrealDB) on the same namespace/db.
**Vulnerability**: The CI/CD and test scripts lack session-aware isolation.

### C. Dependency Divergence
**Scenario**: Session 47 updates a dependency in `pyproject.toml` and locks it. Session 48 is unaware.
**Impact**: Session 48 code breaks when finally merged because of incompatible dependency versions.
**Vulnerability**: Worktrees naturally isolate `uv.lock`, but this creates a "split brain" for dependencies.

### D. Disk Exhaustion (ZFS Swap Pressure)
**Scenario**: Agent creates 10 sessions and never cleans them up.
**Impact**: The iGPU (Strix Halo) with unified memory hits swap pressure.
**Vulnerability**: No TTL (Time-To-Live) or cleanup reminders for sessions.

---

## 2. Blue Team Countermeasures (Mitigations)

### A. Hardened "Clean" Protocol
- `session.py clean` must run `git cherry -v` to check for unpushed commits.
- It must run `git status` to check for uncommitted changes.
- It should warn if the branch hasn't been merged into `main`.

### B. Session-Aware Test Isolation
- Update `scripts/validate-session-setup.sh` to recommend/export `SURREALDB_DB=session_<ID>`.
- Modify `conftest.py` (if possible) to respect this variable.

### C. Session Registry (The heartbeat)
- `session.py status` should show:
  * Last modified date
  * Branch status (ahead/behind remote)
  * Disk usage

### D. "Force" Gate
- Require `--force` ONLY when the user explicitly acknowledges data loss risks.

## 3. Verdict
The tool is **ESSENTIAL** for compound engineering but requires **HIGH-FIDELITY SAFETY GATES** to prevent "Agentic Amnesia" (losing work during cleanup).

## Related Vault Notes

- [[compound-engineering]]
- [[surrealdb]]
