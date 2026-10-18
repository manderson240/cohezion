---
name: coordinate-agents-bus
metadata:
  version: "1.0.0"
description: >-
  Local-first recoverable file-based Agent Bus, task graph DAG execution, and git worktree isolation protocol (hogancv/coordinate-agents abstraction).
---

# SKILL: COORDINATE_AGENTS_BUS_PRIME

## DOMAIN EXPERTISE
Expertise in operating and integrating local-first, crash-recoverable, multi-agent orchestration buses based on the `coordinate-agents` architecture. Employs filesystem-as-queue conventions (`new/`, `processing/`, `processed/`, `evidence/`), schema-validated append-only Event Journals (`runtime.jsonl`), DAG-based subtask dependency frontier resolution, isolated Git worktrees (`.agent-bus/worktrees/<taskId>/<subtaskId>`), deterministic cherry-pick branch integration, and strict separation between internal review approvals (`REVIEW_APPROVED`) and production release gates (`RELEASE_APPROVED`).

## KEY TEXTS & CONCEPTS
- **Local-First Crash Recoverability**: State lives deterministically on disk in `.agent-bus/`. If an agent process, host, or terminal crashes, all pending tasks, processing claims, and journaled events are recoverable via atomic renames and lease timeouts.
- **Atomic File Transitions**: State changes use atomic filesystem renames (`os.replace`) to guarantee no message corruption or race conditions across concurrent processes:
  - `inbox/<agent>/new/<id>.json` $\to$ `processing/<id>.json` (Claiming with lease)
  - `processing/<id>.json` $\to$ `processed/<id>.json` (Completion)
  - `quarantine/<id>.json` (Schema or validation failure)
- **Git Worktree Isolation**: Autonomous agent actions (especially speculative code changes) must NEVER dirty or touch the human developer's active working tree. Each subtask executes on its own branch in an isolated git worktree:
  - Branch: `coordinate-agents/<taskId>/<subtaskId>`
  - Worktree: `.agent-bus/worktrees/<taskId>/<subtaskId>`
- **Deterministic Integration**: When all subtasks in a task graph pass verification, subtask commits are sequentially cherry-picked onto an aggregate integration branch (`coordinate-agents/<taskId>/__integration__`) in topological order. Merge conflicts are surfaced deterministically before PR creation.
- **Release Gating Boundary**:
  - `REVIEW_APPROVED`: Internal verification pass by reviewer agent (e.g. Codex/Antigravity adversarial review). Does NOT touch production or remote repos.
  - `RELEASE_APPROVED`: Explicit user or production promotion authorization required for git pushes, PR merges, or releases.

## INSTRUCTION
1. Initialize Local Agent Bus and Safeguard Git:
   ```python
   from cohezion.swarm.coordinate_bus import LocalAgentBus

   bus = LocalAgentBus(bus_root=".agent-bus")
   # Automatically ensures .agent-bus/.gitignore contains "*" to prevent repository bloat
   ```

2. Publish and Claim Messages:
   ```python
   # Publish task to Antigravity / Codex inbox
   msg_id = bus.publish(
       recipient="antigravity",
       sender="planner",
       subject="Implement D4 Equivariance Harness",
       body={"task_id": "arc2_v16", "priority": "high"},
   )

   # Atomic claim with 600s lease
   claimed = bus.claim_next("antigravity", lease_seconds=600)
   if claimed:
       # Process message...
       bus.complete(claimed, evidence={"tests_passed": 4, "runtime_ms": 120})
   ```

3. Manage Worktree Task Graphs:
   ```python
   from cohezion.swarm.coordinate_bus import TaskGraphWorktreeCoordinator

   coordinator = TaskGraphWorktreeCoordinator(repo_root=".", bus=bus)
   frontier = coordinator.get_ready_subtasks(task_graph)
   for subtask in frontier:
       worktree_path, branch = coordinator.setup_worktree_for_subtask("TASK-001", subtask["id"])
       # Execute agent within worktree_path...
   ```

## VERSION
v1.0

## SEE ALSO
- `autoharness-multi-day-rotation`
- `first-principles-invariant-science`
- `harness2-recursive-harnessing`
- `using-git-worktrees`
