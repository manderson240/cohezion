---
title: "Compound Engineering Investigation Retrospection Before Destructive Operations"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.92
  stage: mature
  synapse_in: 12
  synapse_out: 12
---
## Definition

Investigation-retrospection before destructive operations is a sub-principle of [[compound-engineering]] that mandates a structured investigation and knowledge extraction phase before any operation that destroys, replaces, or irreversibly alters existing state. The principle ensures that before deleting files, truncating logs, restructuring schemas, or replacing infrastructure, the agent first examines what exists, extracts any learnings or diagnostic value, and documents what will be lost.

This principle is the knowledge-preservation counterpart to the software engineering principle of "measure twice, cut once." In traditional engineering, destructive operations are expensive to undo. In knowledge systems, they are often impossible to undo -- once diagnostic data is deleted, the root-cause analysis opportunity is permanently lost.

## The Investigation-Retrospection Protocol

The protocol follows a strict sequence before any destructive operation:

1. **Survey**: Enumerate what exists in the target scope (files, records, logs, schemas)
2. **Analyze**: Read and understand the current state -- look for patterns, errors, diagnostic value
3. **Extract**: Capture any knowledge, learnings, or diagnostic data that will be lost
4. **Document**: Record what will be destroyed and why, creating an audit trail
5. **Review**: For large-scale operations, submit to [[adversarial-review]] before execution
6. **Execute**: Perform the destructive operation in staged, reversible steps with checkpoints
7. **Verify**: Confirm the operation completed correctly and no unintended data was lost

## Key Properties

- **Investigate before destroying**: Read, analyze, and document current state before any destructive operation
- **Extract learnings**: Capture diagnostic data, patterns, or errors from what is about to be removed. Logs, error traces, and configuration state often contain valuable information about system behavior.
- **Staged execution**: Break destructive operations into reversible steps with checkpoints. Each stage should be independently verifiable before proceeding to the next.
- **Escalation protocol**: Large-scale destructive operations require [[adversarial-review]] before execution. The adversarial review explicitly challenges assumptions about what is safe to delete.
- **Panic-mode prevention**: The principle specifically guards against reactive deletion during incidents. Under stress, the temptation to "just delete everything and start fresh" is strongest -- and most dangerous.
- **Audit trail**: Every destructive operation must leave a record of what was destroyed, when, why, and by whom (or which agent).

## Related Papers

- [[2026-02-11-session-55-adversarial-review-blockers-identified]]
- [[2026-02-11-session-55-compound-engineering-approach-for-universe-simulation-preservation]]
- [[2026-02-11-session-55-pause-push-conduct-retrospective-before-github-deployment]]
- [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]

## Related Concepts

- [[compound-engineering]] -- the parent methodology; this concept specifies the investigation/retrospection sub-step that must precede destructive operations
- [[adversarial-review]] -- the review mechanism that challenges assumptions before large-scale destructive operations
- [[2026-02-19-block-destructive-system-operations-from-ai-tools|Block Destructive System Operations from AI Tools]] -- the enforcement decision that implements this principle at the AI tool layer
- [[2026-02-09-operational-principle-no-destructive-operations-without-learning|Operational Principle: No Destructive Operations Without Learning]] -- the predecessor principle that established the mandate
- [[log-lifecycle-management|Log Lifecycle Management Pattern]] -- a concrete instance of this principle applied to log vacuum operations
- [[session-retrospective]] -- the retrospective process that captures learnings from each session, including destructive operations
- [[non-blocking-observability]] -- observability data is the primary target of destructive operations (log rotation, truncation)

## Relevance to Cohezion

This concept captures the pre-condition for any destructive operation in the Cohezion framework: before deleting, restructuring, or replacing knowledge or infrastructure, the agent must investigate current state, retrospect on what will be lost, and extract learnings. This prevents the pattern failure seen in the Feb 2026 SurrealDB incident where panic-mode log deletion destroyed diagnostic data needed for root cause analysis.

The principle is enforced at multiple layers: AI agent tools are blocked from executing destructive system operations without escalation, the [[adversarial-review]] process challenges assumptions before large-scale deletions, and the [[session-retrospective]] process captures learnings from any session that involved destructive operations. Together, these mechanisms ensure that knowledge is preserved even when infrastructure is replaced.
