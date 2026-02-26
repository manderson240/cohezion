---
title: "Operational Principle - No Destructive Operations Without Learning"
date: 2026-02-09
status: approved
tags: [decision, operational-governance, learning, principles]

decision_reasoning:
  chosen_option: "Establish 6-step process: Document → Analyze → Extract Learning → Create Abstraction → Preserve Context → Execute"
  rationale: "Ad-hoc cleanup lost institutional knowledge; mandatory learning extraction preserves patterns and prevents repeated mistakes"
  confidence_score: 0.98
  alternatives_rejected:
    - "No process (lost institutional knowledge, repeated mistakes)"
    - "Lightweight process (insufficient extraction of learnings)"
  reasoning_chain:
    - "Observed lost context when deleting or restructuring files"
    - "Realized patterns were discovered but not abstracted"
    - "Found repeated mistakes across sessions due to knowledge silos"
    - "Decided to mandate 6-step learning extraction before any destructive operation"

metrics:
  estimated_cost: 0.0  # Operational governance
  estimated_time_hours: 40.0  # Implementation of process across all teams
  actual_cost: 0.0  # Established as principle
  actual_time_hours: 6.0  # Session 41-42 codification
  tokens_used: 0  # Internal process
  cost_per_lesson: 0.0
  lessons_generated:
    - patterns/data-discipline-prevent-generated-data-in-git
    - patterns/compound-engineering-investigation-retrospection-before-destructive-operations
---

# Decision: Operational Principle - No Destructive Operations Without Learning

**Date**: 2026-02-09 (Session 41 established, Session 42 codified)
**Category**: Operational Governance
**Status**: APPROVED & CODIFIED IN MEMORY.md
**Confidence**: HIGH

## Decision

Establish mandatory operational principle: **"No destructive operations without learnings and abstractions applied."**

This principle applies to all:
- File deletions
- Branch resets or force-pushes
- Database cleanup or data migrations
- Repository restructuring
- Configuration removal
- Deprecation of features

## Problem Statement

Previous approach: Ad-hoc cleanup and repository management led to:
- Lost context about why files were created
- Inability to recover patterns or architectural decisions
- Repeated mistakes across sessions
- Institutional knowledge loss
- Difficulty debugging issues that required understanding historical context

## Solution

Implement 6-step process before ANY destructive operation:

1. **DOCUMENT**: Capture current state
   - What exists and how it's structured
   - Dependencies and relationships
   - Who uses it and how
   - Historical context if available

2. **ANALYZE**: Understand the problem
   - Why is the change needed?
   - What problem does it solve?
   - What alternatives were considered?
   - What are the risks?

3. **EXTRACT LEARNING**: Preserve knowledge
   - Write findings to vault/MEMORY as pattern or decision
   - Document lessons learned
   - Note what worked and what didn't
   - Identify reusable insights

4. **CREATE ABSTRACTION**: Build for future
   - If pattern is reusable, implement as utility/template/helper
   - Document the abstraction for team access
   - Make it easy for future sessions to avoid repeating work

5. **PRESERVE CONTEXT**: Backup before cleanup
   - Create snapshots or archives
   - Document migration path
   - Implement rollback procedures
   - Ensure recoverability

6. **EXECUTE SAFELY**: Perform the operation
   - Only after all above steps complete
   - With full backup in place
   - Verify safety conditions met
   - Document what changed and why

## Examples

### Example 1: File Consolidation
**Destructive Action**: Consolidate 49 Phase 5B documentation files

**Process Applied**:
1. ✅ DOCUMENT: Catalogued all 49 files, their purposes, and relationships
2. ✅ ANALYZE: Root cause was "documentation forest" - users lost in volume
3. ✅ EXTRACT LEARNING: Created master index pattern, documented navigation hierarchy
4. ✅ CREATE ABSTRACTION: Implemented SESSION_40_MASTER_INDEX.md template for future sessions
5. ✅ PRESERVE CONTEXT: Created docs/session-40-sprint/ archive with all original files
6. ✅ EXECUTE: Safely consolidated with full recoverability

**Result**: Could reuse consolidation pattern in future, prevented knowledge loss

### Example 2: Git Cleanup
**Destructive Action**: Delete obsolete feature branches

**Process**:
1. ✅ DOCUMENT: Record branch purpose, when created, what work was done
2. ✅ ANALYZE: Determine if work should be merged, archived, or discarded
3. ✅ EXTRACT LEARNING: Note patterns in branch lifecycle
4. ✅ CREATE ABSTRACTION: Document branch naming conventions and lifecycle procedures
5. ✅ PRESERVE CONTEXT: Create stash record of final commit before deletion
6. ✅ EXECUTE: Delete with full audit trail

**Result**: Future branches can follow proven lifecycle pattern

### Example 3: Data Migration
**Destructive Action**: Migrate from JSONL to SurrealDB for session persistence

**Process**:
1. ✅ DOCUMENT: Schema of current JSONL format
2. ✅ ANALYZE: Why migration needed (performance, consistency, etc.)
3. ✅ EXTRACT LEARNING: Document data model decisions
4. ✅ CREATE ABSTRACTION: Implement migration utilities as reusable components
5. ✅ PRESERVE CONTEXT: Keep JSONL export for recovery
6. ✅ EXECUTE: Migrate with rollback procedures in place

**Result**: Migration pattern available for future data structure changes

## Enforcement

**Code Review Gate**:
- All destructive operations require review
- Reviewer checks: Are all 6 steps documented?
- No approval until process followed

**CI/Pre-commit Hooks**:
- Warn on file deletions
- Require commit message mentioning learning
- Block force-pushes to main/develop without approval

**Documentation**:
- All decisions preserved in vault/MEMORY
- Patterns available for future team members
- Learnings contribute to institutional knowledge

## Exception Criteria

Operations authorized by explicit prior approval:
- "Delete these 5 files" authorizes only those 5 files in that scope
- Approval does NOT extend to similar files
- Scope must be explicit and bounded

## Anti-Patterns

🚫 **NEVER**: "Just delete this code, it looks unused"
- Might have been deliberately preserved for pattern reuse
- Loss of context prevents future learning
- No extraction of architectural decision

🚫 **NEVER**: Force-push to fix branch issues without analysis
- Loses commit history
- Prevents future developers from learning from mistakes
- No abstraction of underlying problem

🚫 **NEVER**: Drop database without export
- Loss of data structure and relationships
- Cannot recover if migration goes wrong
- No learning extracted about what data was important

## Implementation Status

✅ **Codified**: MEMORY.md section 1 (CRITICAL OPERATIONAL PRINCIPLE)
✅ **Approved**: All 14 team agents unanimous
✅ **Applied**: Session 42 consolidation followed process
✅ **Documented**: This decision + supporting patterns
✅ **Enforcement**: Code review gates implemented

## Related Patterns

- `vault/patterns/non-blocking-knowledge-persistence-pattern.md` (preserve learning)
- `vault/patterns/selective-stash-recovery.md` (preserve context)
- `docs/git-workflow-rules` (branch lifecycle procedures)

## Team Impact

**Benefits**:
- Prevents institutional knowledge loss
- Creates reusable patterns and abstractions
- Reduces repeated mistakes
- Improves debugging and troubleshooting
- Makes codebase changes auditable

**Cost**:
- Requires discipline (6-step process)
- Takes more time initially
- Requires documentation discipline

**Recommendation**: Cost is worth it - prevents far greater costs from lost knowledge and repeated mistakes.

---

**Decision Owner**: User (Session 41)
**Implementation**: Sessions 40-42 team
**Status**: ACTIVE ACROSS ALL FUTURE WORK
**Review Date**: End of Phase 6

## Related
**Domains**: data
**Categories**: operational, strategic


[[workflow-orchestration]]

## Relevance to Cohezion

[[agentic-ai]]

## Related Patterns

- [[log-lifecycle-management]] — the log lifecycle and extraction pattern that operationalizes this principle's "Extract Learning" step

## Related Lessons

- [[lesson-11-team-agent-efficiency]] (operational validation)

- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]] (operational validation)

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
