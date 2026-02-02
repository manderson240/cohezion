# RETROSPECTIVE: Phase 31 - The Great Purification

**Date**: 2026-02-01
**Event**: Removal of 17 Million Ghost Files (8.6M from Index).
**Severity**: CRITICAL (System Paralysis).

## 1. The Incident
The system reached a state of "Unruly Bloat" where `git status` commands would hang, and the index size exceeded 800MB.
- **Symptom**: "Still have >10k pending changes" loops.
- **Cause**: Autonomous Agents (`ShadowScripter`, `ExpansionLoop`) generating high-frequency artifacts (logs, traces, jsonl) directly into the `src/` tree, which were inadvertently tracked by a permissive `.gitignore`.

## 2. Root Cause Analysis (The "Why")
1.  **Placement**: Agents defaulted to writing data relative to their execution path (`src/cohezion/...`) rather than a dedicated `data/` or `tmp/` sink.
2.  **Permissiveness**: The `.gitignore` was reactive (ignoring specific files) rather than proactive (allowing only source).
3.  **Visibility**: We lacked a "Fuel Gauge". We didn't know we had 17M files until the engine stalled.

## 3. The Fix (Compound Engineering)
We did not just "clean up"; we built a **Immune System**.

### A. The Cure (Surgical Prune)
- **Tool**: `scripts/maintenance/surgical_prune.py`.
- **Action**: Iteratively removed files from the index while keeping the workspace intact.
- **Result**: Reduced index from >800MB to Clean.

### B. The Shield (GitSentinel)
- **Tool**: `src/cohezion/system/git_sentinel.py`.
- **Function**: Runs daily/pre-flight checks.
- **Logic**: If files > 100k, **HALT** operation. This prevents the "Death Spiral" of 17M files.

### C. The Law (Lockdown)
- **Policy**: "Source Only".
- **Implementation**: Updated `.gitignore` to whitelist code and blacklist everything else (`*`).

## 4. Key Learnings (The "Remember this")
> [!IMPORTANT]
> **Data Gravity Kills Autonomy.**
> If an autonomous agent can write files, it *will* fill the disk.
> 
> **Protocol 31**:
> 1.  **NEVER** write generated data to `src/`. Always use `data/` or SurrealDB.
> 2.  **ALWAYS** have a `Sentinel` watching the file count.
> 3.  **COMMIT** often. Huge pending changelists paralyze the git tools.

## 5. Future Prevention
- **Agent Instruction**: All new agents must have a "Write Constraint" prompt injected (e.g., "You may only write to `data/`").
- **CI/CD**: The `GitSentinel` check is now a requirement for the `ExpansionLoop` to run.
