---
description: "Mandatory proactive subagent delegation and persistent local inference execution"
globs: ["**/*"]
alwaysApply: true
---

# Rule: Proactive Subagent Delegation & Local Inference Discipline

## Triggers
- Multi-step tasks, competition pipelines, research synthesis, complex refactors, and diagnostic loops.
- Ambiguous execution paths, branch points, or performance optimizations.

## Enforced Behavior
1. **Subagent Delegation First**:
   - Deconstruct complex workflows into modular, concurrent subagent tasks via `invoke_subagent`.
   - Use role-specialized subagents:
     - `oma-researcher`: Deep mathematical and literature grounding, metric deconstruction, competitive intelligence.
     - `oma-executor`: Focused implementation, refactoring, test harness execution, and kernel packaging.
     - `oma-reviewer`: Adversarial code review, invariant checking, AST static analysis.
     - `oma-architect`: System topology, memory governance, and pipeline design.
2. **Local Inference Hardware Standards**:
   - Always route local inference through **Lemonade admission proxy on port 13305** (never bypass to internal ports).
   - Enforce a minimum **300.0s timeout SLA** (`connect=15.0, read=300.0, write=60.0, pool=10.0`) to allow local thinking models sufficient time to render complex reasoning chains ("Leave plenty of time for the fat to render").
   - Default NPU model: `qwen3.5-4b-FLM` on AMD XDNA2 NPU (<2W power, 0 UMA RAM footprint).
   - Coding/agentic tool lane: `Qwen3-Coder-30B-A3B-Instruct-GGUF` on Radeon 8060S iGPU.
3. **Local Next-Step Consultation Mandate**:
   - When encountering branching choices or ambiguous optimization paths, query port 13305 before committing to high-compute paths.
4. **Persistent Multi-Store Logging**:
   - All delegations, findings, and experiment milestones must persist to both SurrealDB (`http://localhost:8001/sql`, NS `cohezion`, DB `main`) and the Obsidian Vault (`~/vaults/cohezion-vault/`).
