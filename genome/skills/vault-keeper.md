---
title: "Vault Keeper Skill"
date: 2026-03-05
version: 3
last_revised: 2026-03-05
tags: [spec, skill, vault-keeper, vault-architecture]
source: ".claude/skills/vault-keeper/SKILL.md"
status: active
revision_history:
  - {v: 1, date: 2026-03-04, change: "Initial skill creation with 6-phase pipeline"}
  - {v: 2, date: 2026-03-05, change: "Added Read mode (5-min cooldown), canvas nudge"}
  - {v: 3, date: 2026-03-05, change: "Added callout nudge, alias nudge for Write/Edit mode"}
aspect: knower
neural:
  activation: 0.383
  stage: embryo
  cluster: specs
---

# Vault Keeper Skill

> [!abstract] Purpose
> Autonomous maintenance agent that keeps the vault healthy, dense, navigable, and agent-readable. Orchestrates five specialist skills (vault-health, link, flesh-out, triage, note) in a single prioritized workflow.

## Invocation

```
/vault-keeper                    # Full maintenance cycle
/vault-keeper --quick            # Read-only health check (30 seconds)
/vault-keeper --triage           # Process inbox only
/vault-keeper --densify          # Link + flesh-out cycle
/vault-keeper --moc              # Generate/update Maps of Content
/vault-keeper --context "query"  # Load relevant vault context
```

## Proactive Behavior

The vault keeper fires automatically via PostToolUse hooks:

| Trigger | Cooldown | Checks |
|---------|----------|--------|
| Write/Edit on `.md` | 60 seconds | Inbox count, frontmatter, inbound links, canvas nudge, callout nudge, alias nudge |
| Read on `.md` | 5 minutes | Inbox count only (vault-wide pulse) |

## 6-Phase Pipeline

```mermaid
graph LR
    A[Phase 1: TRIAGE] --> B[Phase 2: AUDIT]
    B --> C[Phase 3: HEAL]
    C --> D[Phase 4: DENSIFY]
    D --> E[Phase 5: NAVIGATE]
    E --> F[Phase 6: REPORT]
```

| Phase | Purpose | Actions |
|-------|---------|---------|
| 1. TRIAGE | Zero inbox | Classify → research → structure → move → link |
| 2. AUDIT | Find issues | Broken links, orphans, frontmatter, thin notes, under-connected hubs |
| 3. HEAL | Fix issues | Add frontmatter, connect orphans, fix broken links |
| 4. DENSIFY | Expand + connect | Flesh out thin notes, add missing cross-links |
| 5. NAVIGATE | MOC generation | Create/update Maps of Content |
| 6. REPORT | Metrics | Before/after delta table |

## Quality Invariants

- 0 orphan notes in content directories
- 0 frontmatter issues
- 0 actionable broken links
- < 10% thin notes per directory
- 8+ Maps of Content
- 6+ avg wiki-links per note

## Hook Source

**File:** `.claude/hooks/vault-keeper-check.sh`

6 checks: inbox count, frontmatter validation, inbound link check, canvas nudge (10+ outbound links), callout nudge (decisions/lessons/patterns), alias nudge (concepts without aliases).

## Related

- [[2026-03-05-vault-as-system-of-record]] — Why this spec is in the vault
- [[MOC-vault-architecture]] — Navigation
