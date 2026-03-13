---
title: 'PRIME Skill Quick Reference (Session 56)'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.81
  stage: growing
  synapse_in: 5
  synapse_out: 4
---
# PRIME Skill Quick Reference (Session 56)

**Status**: Quick guide for creating governance skills
**For**: Teams implementing PRIME skills or referencing REPOSITORY_HEALTH_PRIME
**Time**: 5 minutes to read | 45 minutes to create a skill

---

## One-Sentence Definition

**PRIME Skills** = Executable specifications + team documentation + automation foundation for governance procedures.

---

## When to Create a PRIME Skill

✅ **Create when**:
- Procedure repeated across 3+ sessions/projects
- Multiple team members need to know how to execute
- Procedure is important enough to automate (CI/CD, scheduled tasks)
- Current implementation is scattered (pre-commit + CI + manual docs)

❌ **Skip when**:
- One-off manual procedure
- Only creator needs to know
- Procedure unlikely to change

**Question to ask**: "Would 3+ people benefit from knowing this in a reusable form?" → YES = Create PRIME skill

---

## 7-Section Template

### 1. Metadata (50 lines)
```markdown
# {{SKILL_NAME}}: {{DOMAIN}}
**PRIME Skill ID**: {{ID}}
**Domain**: {{Domain}}
**Charter Alignment**: {{Principles}}
**Status**: [Draft | Validated | Production]
**Version**: 1.0.0
**Created**: {{Date}}
**Validated**: {{Date}}
```
**Time**: 10 min

### 2. Concepts (30 lines)
```markdown
## Key Concepts
| Concept | Definition | Charter Link |
|---------|-----------|--------------|
| {{Term}} | {{Def}} | {{Section}} |
```
**Time**: 5 min | **Purpose**: Team speaks same language

### 3. Instructions (100-200 lines)
```markdown
## Instructions
### Phase 1: {{Name}}
**Objective**: {{What}}
**Steps**:
1. {{Step}}
2. {{Step with branching}}
   - If {{condition}}, then {{action}}
3. {{Step}}
**Success Criteria**: {{Measurable}}
**Error Handling**: {{Recovery actions}}
```
**Time**: 15 min | **Purpose**: Executable procedure

### 4. Examples (50-100 lines)
```markdown
## Examples
### Example 1: {{Real scenario}}
**Result**: {{Outcome with metrics}}
**Time**: {{Actual duration}}
**Cost**: {{Cost}}
```
**Time**: 10 min | **Purpose**: Validation proof

### 5. Evolution History (20-30 lines)
```markdown
## Evolution History
### Session {{N}}: {{Change}}
- What changed: {{Desc}}
- Why: {{Rationale}}
- Impact: {{Metrics}}
```
**Time**: 5 min | **Purpose**: Track improvements

### 6. Validation Results (30 lines)
```markdown
## Validation Results
| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| {{Metric}} | {{Target}} | {{Actual}} | ✅ |
```
**Time**: 5 min | **Purpose**: Proof skill works

### 7. Charter Alignment (50 lines)
```markdown
## Charter Alignment
### SPIN Principle: {{Aspect}}
- How skill embodies: {{Desc}}
- Evidence: {{Metric}}

### HIHO Stability
- Coherence impact: {{How}}
- Observable: {{What we measure}}
```
**Time**: 5 min | **Purpose**: Constitutional grounding

---

## Total Time Estimate

| Section | Time | Cumulative |
|---------|------|-----------|
| Metadata | 10 min | 10 min |
| Concepts | 5 min | 15 min |
| Instructions | 15 min | 30 min |
| Examples | 10 min | 40 min |
| Evolution | 5 min | 45 min |
| Validation | 5 min | 50 min |
| Charter | 5 min | 55 min |

**Total: 45-55 minutes for comprehensive skill**

(Can be faster if you have good examples and execution logs already)

---

## Example: REPOSITORY_HEALTH_PRIME (Session 56, Task #9)

### Template Applied
```
Section 1: Metadata
- ID: skill-0012-repository-health
- Domain: Repository Management
- Alignment: Observable AI, Deterministic Responsibility, HIHO Stability
- Status: Production
- Created: 2026-02-12 (Session 56)
- Validated: 2026-02-12 (13GB→5.9GB, zero data loss)

Section 2: Concepts
- HIHO Stability Range: 4-8GB optimal
- Git Object Database: 73% of repo size
- Pack Files: Compressed object storage

Section 3: Instructions
- Phase 1: Assess (du -sh, git gc status)
- Phase 2: Cleanup (if >8GB: filter-repo, repack)
- Phase 3: Monitor (set 8GB warning threshold)

Section 4: Examples
- Example 1: Session 55 cleanup (13GB→5.9GB, 5 min, zero loss)

Section 5: Evolution
- Session 56: Creation + validation

Section 6: Validation
- Production: Tested on 13GB repo, zero data loss, 5 min
- Metric: HIHO range (4-8GB) restored

Section 7: Charter
- Observable AI: Full transparency in cleanup steps
- HIHO Stability: 4-8GB maintains 0.5 coherence baseline
- Deterministic: Idempotent, reproducible, zero data loss
```

---

## Creation Workflow

**Step 1: Gather** (10 min)
- [ ] Find 2-3 real executions of procedure
- [ ] Collect metrics (time, cost, success rate)
- [ ] Identify domain terminology
- [ ] Note which Charter principles apply

**Step 2: Structure** (15 min)
- [ ] Write metadata with ID + versioning
- [ ] Define 3-5 key concepts
- [ ] Outline 5-10 logical phases
- [ ] Plan 2 example scenarios

**Step 3: Write** (20 min)
- [ ] Draft instructions with branching logic
- [ ] Add error handling for common failures
- [ ] Write real examples with metrics
- [ ] Map to Charter principles

**Step 4: Validate** (10 min)
- [ ] Execute skill yourself (QA)
- [ ] Have another person execute (validation)
- [ ] Document actual vs estimated metrics
- [ ] Update Examples section

**Step 5: Ship** (5 min)
- [ ] Save to `src/cohezion/skills/` or vault
- [ ] Register in skill_registry.json
- [ ] Add to team MEMORY.md
- [ ] Mark as Production-ready

---

## Checklists

### Pre-Creation Checklist

- [ ] Procedure executed 3+ times?
- [ ] 3+ people would benefit from knowing?
- [ ] Important enough to automate?
- [ ] Scattered across 2+ places currently?
- [ ] Charter principles involved?

**If all YES → Create PRIME skill**

### Quality Checklist (Before Shipping)

- [ ] Metadata complete + version tracked?
- [ ] Concepts clear and Charter-linked?
- [ ] Instructions phased with branching logic?
- [ ] Examples include real metrics (time, cost)?
- [ ] Evolution history shows improvement path?
- [ ] Validation proves skill works?
- [ ] Charter alignment explicit?
- [ ] Total lines: 1,500-2,500 (comprehensive)?
- [ ] Can another person execute from instructions?
- [ ] Ready for automation/scheduling?

**All checked → Ready to ship to Production**

### Quarterly Review Checklist

- [ ] Skill still matches current practice?
- [ ] Any improvements from recent sessions?
- [ ] Update examples with latest metrics?
- [ ] Team feedback incorporated?
- [ ] Charter alignment still valid?
- [ ] Deprecation needed? (sunset with reason)

---

## Integration Points

### Skill Registry
```python
from cohezion.skills.skill_registry import SkillRegistry

registry = SkillRegistry()
skill = registry.get_skill("REPOSITORY_HEALTH_PRIME")
result = skill.execute(repo_path=..., threshold_gb=8)
```

### Team Documentation
```markdown
In MEMORY.md:
| Skill | Domain | Status | Created |
|-------|--------|--------|---------|
| REPOSITORY_HEALTH_PRIME | Repo Governance | Production | 2026-02-12 |
```

### Automation Workflows
- CI/CD: Invoke skill on every commit/push
- Scheduled: Run daily health check (Task #12)
- Event-driven: Trigger on repository size threshold

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **Over-detailed** | 50+ steps, micro-optimizations | Keep to 5-10 phases, variations in error handling |
| **No Charter link** | "How" but not "Why" | Explicitly connect to SPIN, HIHO, Observable AI |
| **Missing examples** | Theory only, no validation | Provide 2-3 worked examples with metrics |
| **No evolution** | Skill becomes stale | Track each session's improvements |
| **Too generic** | Applies to everything | Target specific problem domain |

---

## Success Metrics for PRIME Skills

### Creation Efficiency
- Time to create: 45-55 min (target)
- Lines per skill: 1,500-2,500 (comprehensive)
- ROI: 2,500 tokens = 10:1 return

### Team Adoption
- % of team using skill: 60%+ (after 1 month)
- Confidence in execution: 95%+ (from survey)
- Time to execute (independent): Within 20% of documented

### Automation Impact
- % of procedure automatable: 80%+
- Cost savings: Varies (e.g., repository cleanup: 5 min vs 30+ manual)
- Downtime reduction: Measurable per use case

---

## Next Skills to Create

**Planned PRIME Skills** (Post-Session 56):

1. **PLATFORM_HEALTH_DIGEST_PRIME** (Task #12)
   - Scope: Daily health checks + alerts
   - Estimate: 4 hours
   - Based on: REPOSITORY_HEALTH_PRIME + other observables

2. **DECISION_RETROSPECTIVE_PRIME** (Task #13)
   - Scope: Quarterly retrospections + lessons extraction
   - Estimate: 3 hours
   - Based on: Compound engineering learnings

3. **VAULT_MAINTENANCE_PRIME** (Task #14)
   - Scope: Vault cleanup, archival, organization
   - Estimate: 2 hours
   - Based on: Current vault operations

4. **CI_CD_SKILL_INTEGRATION_PRIME** (Task #15)
   - Scope: Automated skill invocation in workflows
   - Estimate: 3 hours
   - Based on: REPOSITORY_HEALTH_PRIME + platform integration

---

## References

**Full Pattern**: `patterns/prime-skill-creation-governance-pattern.md` (2,200+ lines)
**Example Skill**: `src/cohezion/skills/REPOSITORY_HEALTH_PRIME.md` (production-ready)
**Charter**: `.agent/COHEZION_CHARTER.md` (principles + SPIN)
**Session 56 Recap**: `decisions/2026-02-12-session-56-handoff-complete.md`

---

**Created**: Session 56 (2026-02-12)
**Status**: ✅ Quick Reference Ready
**Next**: Use as guide for Tasks #12, #15 skill creation

## Related

- [[2026-02-12-prime-skill-pattern-as-governance-framework]]
- [[prime-skill-creation-governance-pattern]]
- [[surrealdb-agent-context-quick-reference]]
- [[2026-02-12-repository-health-governance-skill-created]]
