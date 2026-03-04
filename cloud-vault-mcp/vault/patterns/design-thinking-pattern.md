# Design Thinking Pattern: Project Health Transformation

**Date:** 2026-03-04  
**Pattern Type:** Health Score Improvement  
**Applied To:** Cohezion

---

## Problem Context

### Empathize Findings

| User Group | Pain Point |
|------------|------------|
| **Developers** | 761 untracked files, fragmented docs, no clear entry point |
| **Operators** | CI failures (Python version mismatch), push timeouts, deployment gaps |
| **End Users** | Complex API surface (72+ routes), unclear documentation |
| **AI Agents** | Limited self-documentation, need capability negotiation |

### Key Observations

1. **Scale is overwhelming** - 15 epics, complex history
2. **Security was reactive** - Issues found during review, not built-in
3. **Documentation fragmented** - Multiple sources, no single source of truth
4. **No clear entry point** - Missing "start here" guidance

---

## Define Phase

### POV Statement

**Developers, operators, and users** need **a clear entry point and maintainable structure** because **the current scale and fragmentation create overwhelm and uncertainty.**

### How Might We Questions

1. How might we provide a single "start here" path for all stakeholders?
2. How might we make technical debt visible and manageable?
3. How might we ensure security is built-in, not discovered?
4. How might we help AI agents self-document their capabilities?

---

## Ideate Phase

### Selected Methods

| Method | Rationale |
|--------|-----------|
| **SCAMPER Design** | Apply existing patterns in new ways |
| **Daily Health Check** | Visible metrics dashboard |
| **Onboarding Flow** | Single entry point |

### Top Concepts

1. **Daily Health Check Script** - Automated CI script for visibility
2. **QUICKSTART.md** - Single entry point for onboarding
3. **Architecture Diagram** - Visual navigation of complex system
4. **`make onboard`** - Automated setup + health check

---

## Prototype Phase

### Artifacts Created

| Artifact | Location | Purpose |
|----------|----------|---------|
| **daily_health_check.py** | `scripts/ci/` | Automated health visibility |
| **QUICKSTART.md** | Project root | Single entry point |
| **architecture.md** | `docs/` | Visual navigation |
| **`make onboard`** | `Makefile` | Automated setup |
| **test.yml** | `.github/workflows/` | CI Python 3.13 fix |

### Vault Persistence

| Record | Location |
|--------|----------|
| **Design Thinking Session** | `_bmad-output/design-thinking-2026-03-04.md` |
| **Health Pattern** | `cloud-vault-mcp/vault/patterns/design-thinking-pattern.md` |
| **Daily Health** | `cloud-vault-mcp/vault/daily/health-check-*.md` |

---

## Test Phase

### Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Untracked files | 761 | <50 |
| Onboarding time | Unknown | <15 min |
| CI pass rate (main) | ~60% | 95% |
| Security HIGH issues | 4 | 0 |
| Time to first contribution | Unknown | <1 day |

### Validation Approach

1. **Health Check Runs** - Verify daily in CI
2. **New User Test** - Time onboarding from fresh clone
3. **CI Metrics** - Track pass rates over time

---

## Implementation Pattern

### Sequence

```
1. Create health check script
2. Fix CI (Python version)
3. Create QUICKSTART.md
4. Add `make onboard` target
5. Generate architecture diagram
6. Save to vault for persistence
```

### Reusable Steps

1. **Empathize**: Survey all user groups, map empathy
2. **Define**: Craft POV statement + HMW questions
3. **Ideate**: Generate 15+ solutions, cluster by impact
4. **Prototype**: Create minimal viable artifacts
5. **Test**: Define success metrics upfront
6. **Implement**: Prioritize by impact/effort

---

## Lessons Learned

- **Security as foundation**: Include security checks in daily health
- **Vault persistence**: Design thinking sessions should auto-save to vault
- **SurrealDB trends**: Store health scores for trend analysis
- **Visual navigation**: ASCII diagrams work better than complex SVG for quick comprehension

---

_Apply this pattern to new projects by following the Empathize → Define → Ideate → Prototype → Test sequence._