---
title: "Safe Handoff Protocol"
date: 2026-03-15
status: complete
tags: [infinity, handoffs, gpu-optimization]
aspect: thinker
---

# Safe Handoff Protocol

## If Tokens Run Out

### Immediate Actions
1. **Save current state** to vault
2. **Document blockers** in coordination/handoffs/
3. **Checkpoint** all active work

### Handoff File Location
`/opencode_infinity/coordination/handoffs/HANDOFF_YYYY-MM-DD.md`

### Handoff Template
```markdown
# Handoff - [DATE]

## Orchestrator Status
- Model: [model name]
- Session: [session ID]
- Tokens remaining: [estimate]

## Team Status
### Team MoE
- Status: [active/blocked/completed]
- Current task: [description]
- Blockers: [if any]
- Next action: [what to do next]

### Team GEMM
- Status: [active/blocked/completed]
- Current task: [description]
- Blockers: [if any]
- Next action: [what to do next]

### Team MLA
- Status: [active/blocked/completed]
- Current task: [description]
- Blockers: [if any]
- Next action: [what to do next]

## Critical Information
- Active submissions: [IDs]
- Queue status: [busy/clear]
- Current rankings: [ranks]

## Resume Instructions
1. Check vault for latest updates
2. Review team handoff files
3. Resume from last checkpoint
4. Continue parallel development

## Contact
- Primary: [user]
- Workspace: /opencode_infinity/
```

## Recovery Procedure
1. New session reads HANDOFF file
2. Checks vault for updates
3. Resumes team coordination
4. Continues from checkpoint

## Vault Sync Points
Sync to vault every 30 minutes:
- Team progress
- Submission results
- Key learnings
- Next actions