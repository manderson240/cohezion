---
type: antigravity-artifact
session_id: 5b09f172-914b-4c11-b27a-91c5aa920ed3
date: 2026-03-04
title: "Automated Repo Health Management Plan"
tags: [agent-output, antigravity, repository-management, automation]
aspect: doer
neural:
  activation: 0.464
  stage: growing
  cluster: Agents
---

# Automated Repo Health Management & Branching

This plan addresses the recurring git bloat and "too many active changes" issue by introducing automated hygiene and a structured branching manager.

## Proposed Changes

### [Repo Hygiene]

#### [NEW] [repo_janitor.py](file:///home/mike-anderson/dev/cohezion/scripts/repo_janitor.py)
A specialized script to keep the repository lean.
- **`purge_history_candidates()`**: Identifies files that match `.gitignore` but are still tracked. Runs `git rm --cached`.
- **`cleanup_artifacts()`**: Safely removes untracked large logs (`*.log`), temp data (`*.jsonl`, `*.sst`), and build artifacts not needed for active work.
- **`check_git_vitals()`**: Monitors `.git` directory size and warns if it exceeds a threshold (e.g., 5GB).
- **`enforce_limits()`**: Hard limit on file sizes (e.g., no files > 5MB) and total pending changes.
- **`extract_db_wisdom()`**: Runs `db_lens.py` to capture insights before pruning.
- **`prune_database()`**: Triggers SurrealDB cleanup for old simulation logs and transient state.

### [SurrealDB Hygiene]

#### [NEW] [db_lens.py](file:///home/mike-anderson/dev/cohezion/scripts/db_lens.py)
A specialized script for feature extraction and learning.
- **`extract_knowledge()`**: Samples transient data (velocity, pulse, journeys) to identify architectural patterns and common failure modes.
- **`summarize_drift()`**: Generates a report for `KEY_LEARNINGS.md`.

#### [NEW] [db_pruning.py](file:///home/mike-anderson/dev/cohezion/scripts/db_pruning.py)
A specialized script for database maintenance.
- **`prune_simulation_logs(days=7)`**: Removes simulation records older than a specific threshold.
- **`compact_tables()`**: Triggers database optimization if supported by the client/backend.
- **`report_stats()`**: Provides a breakdown of record counts per table.

### [Guardrails & Defensive Systems]

#### [NEW] [pre-commit](file:///home/mike-anderson/dev/cohezion/.git/hooks/pre-commit)
A git hook to block bloat at the source.
- **Large File Detection**: Prevents committing files over 5MB.
- **Ignore Check**: Ensures files matching `.gitignore` patterns are not accidentally staged.
- **Structure Check**: Verifies that new files follow the project's organization rules.

#### [NEW] [health_monitor.py](file:///home/mike-anderson/dev/cohezion/scripts/health_monitor.py)
A background system (daemon) that periodically runs the janitor.
- **Auto-Cleanup**: Automatically purges old logs and temporary simulation artifacts.
- **Vitals Alert**: Notifies the user/system if git health degrades (e.g., entropy spikes or index bloat).

### [Batch & Cache Optimization]

#### [MODIFY] [repo_janitor.py](file:///home/mike-anderson/dev/cohezion/scripts/repo_janitor.py)
- **Batch Deletion**: Implement chunked deletion of files (e.g., 1000 at a time) to prevent `Argument list too long` errors.
- **Status Caching**: Cache the results of `git status` when the pending count is high (>100k) to avoid redundant heavy IO.

#### [MODIFY] [work_manager.py](file:///home/mike-anderson/dev/cohezion/scripts/work_manager.py)
- **Task Batching**: Allow grouping multiple small commits or savepoints into focused batches.
- **Cache-Aware Status**: Check the janitor's cache before running full git commands if in a high-bloat state.

### [Autonomic Integration & Local Routing]

#### [MODIFY] [health_monitor.py](file:///home/mike-anderson/dev/cohezion/scripts/health_monitor.py)
- **Healing Hook**: Register the health monitor with `cohezion.healing.get_healing_system()`.
- **Autonomous Action**: Allow the monitor to trigger `repo_janitor.py` and `work_manager.py checkpoint` automatically when drift or bloat thresholds are exceeded.

#### [NEW] [maintenance_config.json](file:///home/mike-anderson/dev/cohezion/config/maintenance_config.json)
- Define a policy that forces all maintenance/hygiene agents to use local Ollama models (e.g., `qwen3-coder:32b` or `deepseek-r1:70b`).

#### [MODIFY] [BaseAgent](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/base.py)
- **Routing Logic**: Implement a "Local First" policy for agents tagged with `maintenance` or `reliability` capabilities.

#### [MODIFY] [.gitignore](file:///home/mike-anderson/dev/cohezion/.gitignore)
- Add more aggressive patterns for the knowledge graph logs and temporary simulation results.

### [Workflow Management]

#### [NEW] [work_manager.py](file:///home/mike-anderson/dev/cohezion/scripts/work_manager.py)
A CLI tool to manage active tasks and prevent bloat.
- **`start-task <name>`**: Automates the creation of a clean feature branch.
- **`checkpoint`**: Stashes or commits current work in small, logical chunks to keep the working set manageable.
- **`status`**: Integrates with `git_health.py` to give a high-level view of repo weight and pending changes.

---

## [Security Stabilization]
This mission applies the same autonomic rigor to system security, focusing on secret management, injection defense, and audit integrity.

### [Hardened Guardrails]

#### [MODIFY] [pre-commit.py](file:///home/mike-anderson/dev/cohezion/scripts/hooks/pre-commit.py)
- **Secret Scanning**: Implement entropy-based and regex-based detection for API keys, tokens, and private keys.
- **Dependency Audit**: (Optional) Run a lightweight scan for known vulnerabilities in `uv.lock`.

#### [NEW] [security_scout.py](file:///home/mike-anderson/dev/cohezion/scripts/security_scout.py)
A diagnostic script for system-wide security auditing.
- **`audit_vulnerabilities()`**: Scans for OWASP LLM Top 10 indicators.
- **`verify_vault_integrity()`**: Ensures all sensitive configurations are stored in `BitwardenVault`, not in `.env` or hardcoded.
- **`check_log_entropy()`**: Analyzes `audit.jsonl` for anomalous failure patterns.

### [Autonomous Security Monitoring]

#### [MODIFY] [health_monitor.py](file:///home/mike-anderson/dev/cohezion/scripts/health_monitor.py)
- **Security Pulse**: Periodically triggers `security_scout.py`.
- **Anomaly Response**: Automatically flags suspicious auth failures or blocked prompt injections for retrospective analysis.

### [Security Intelligence Routing]

#### [MODIFY] [maintenance_config.json](file:///home/mike-anderson/dev/cohezion/config/maintenance_config.json)
- Add `security` and `audit` capabilities to the local-first routing list, ensuring sensitive audits never leave the local environment.

---

## Verification Plan

### Automated Tests
- `pytest tests/unit/test_repo_janitor.py`: Verify that the janitor correctly identifies tracked-but-ignored files without deleting important code.
- `pytest tests/unit/test_work_manager.py`: Verify branch creation and checkpointing logic.

### Manual Verification
1. Run `python scripts/repo_janitor.py --dry-run` to see what files would be removed/uncached.
2. Run `python scripts/work_manager.py start-task repo-fix` and verify a new branch is created.
3. Observe `git status` performance after running the janitor to ensure responsiveness is restored.

## Related Vault Notes

- [[surrealdb]]
- [[cohezion]]
