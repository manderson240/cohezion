# Design Thinking Session: Cohezion

**Date:** 2026-03-04
**Facilitator:** Mike
**Design Challenge:** How might we transform Cohezion from a complex research system into a confident, accessible platform that developers, operators, users, and AI agents can all navigate with clarity and trust?

---

## 🎯 Design Challenge

**Challenge:** Redesign the Cohezion experience to serve all stakeholders—developers, operators, end users, and AI agents—with a cohesive, intuitive, and well-documented system.

---

## 👥 EMPATHIZE: Understanding Users

### User Groups Identified

| User Type | Description | Key Needs |
|-----------|-------------|-----------|
| **Developers** | Engineers extending/building on Cohezion | Clear onboarding, consistent patterns, debuggable code |
| **Operators** | People running Cohezion infrastructure | Deployment guides, monitoring, incident response |
| **End Users** | Those interacting via API/dashboard | Intuitive interfaces, clear feedback, documentation |
| **AI Agents** | The autonomous components themselves | Clear interfaces, consistent APIs, self-documentation |

### Empathy Map: Developers

| | | |
|---|---|---|
| **SAYS** | **THINKS** | |
| "761 untracked files is overwhelming" | "Where do I even start?" | |
| "Security review found issues I didn't know existed" | "Is the codebase healthy?" | |
| "The BMAD workflow is complex" | "How do all these epics connect?" | |
| **DOES** | **FEELS** | |
| Struggles to commit large changes | Overwhelmed by scope | |
| Hunts through 15 epics for context | Frustrated by fragmented docs | |
| Fixes security issues reactively | Uncertain about architecture decisions | |

### Empathy Map: Operators

| | | |
|---|---|---|
| **SAYS** | **THINKS** | |
| "Git push times out" | "Is this maintainable?" | |
| "CI fails on Python version mismatch" | "What's the deployment story?" | |
| **DOES** | **FEELS** | |
| Debugs repository size issues | Frustrated by slow operations | |
| Works around CI problems | Concerned about production readiness | |

### Key Observations

1. **Scale is overwhelming** - 15 epics, 761+ untracked files, complex history
2. **Security was reactive** - Issues found during review, not built-in
3. **Documentation fragmented** - BMAD workflows, AGENTS.md, story files in different places
4. **No clear entry point** - New users/contributors lack "start here" guidance
5. **CI/CD gaps** - Python version mismatches, timeout issues

---

## 🎨 DEFINE: Frame the Problem

### Point of View Statement

**Developers, operators, and users** need **a clear entry point and maintainable structure** because **the current scale and fragmentation create overwhelm and uncertainty.**

### How Might We Questions

1. **How might we** provide a single "start here" path for all stakeholders?
2. **How might we** make technical debt visible and manageable?
3. **How might we** ensure security is built-in, not discovered?
4. **How might we** help AI agents self-document their capabilities?

### Key Insights

- The system works technically but lacks confidence-building infrastructure
- Documentation exists but is fragmented
- Security should be proactive, not reactive
- Onboarding is the highest-impact improvement

---

## 💡 IDEATE: Generated Solutions

### Top Concepts

| Concept | Description | Impact |
|---------|-------------|--------|
| Daily Health Check | CI script that scans for issues | Prevents accumulation |
| Onboarding Flow | `make onboard` + QUICKSTART.md | Reduces time-to-productive |
| Architecture Diagram | Visual navigation of system | Mental model clarity |
| Triage Strategy | Batch untracked files by category | Reduces overwhelm |

---

## 🛠️ PROTOTYPE: Proposed Solutions

### Prototype 1: Daily Health Check Script

```python
# scripts/ci/daily-health-check.py
# Runs: security scan, lint check, identifies untracked files
# Reports: health-score, action items
# Runs daily in CI, posts results to PR/badge
```

### Prototype 2: QUICKSTART.md

```markdown
# Cohezion Quick Start

## Prerequisites
- Python 3.13+
- UV package manager

## Get Started
1. `uv sync` - Install dependencies
2. `make lint` - Check code quality
3. `make test-fast` - Run fast tests
4. `make onboard` - Full setup + health check

## What's Next?
- [Architecture Overview](docs/architecture.md)
- [Epic Progress](docs/epics.md)
- [Contributing](CONTRIBUTING.md)
```

---

## ✅ TEST: Validation Criteria

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Untracked files | 761 | <50 |
| New developer onboarding time | Unknown | <15 min |
| CI pass rate (main) | ~60% | 95% |
| Security scan HIGH issues | 4 → 0 | 0 |
| Time to first contribution | Unknown | <1 day |

---

## 🚀 Next Steps

### Immediate Actions (This Week)

| # | Action | Priority |
|---|--------|----------|
| 1 | Create `daily-health-check.py` CI script | HIGH |
| 2 | Update CI to Python 3.13+ | HIGH |
| 3 | Create `QUICKSTART.md` | MEDIUM |
| 4 | Triage untracked files in batches | HIGH |

### Short-Term (This Month)

| # | Action | Priority |
|---|--------|----------|
| 5 | Generate architecture diagram | MEDIUM |
| 6 | Create `make onboard` target | MEDIUM |
| 7 | Expand forbidden patterns list | HIGH |
| 8 | Add healing audit logging | MEDIUM |

### Long-Term (Ongoing)

| # | Action | Priority |
|---|--------|----------|
| 9 | Consolidate documentation into `docs/` | LOW |
| 10 | Implement capability negotiation for agents | MEDIUM |

---

_Generated using BMAD Creative Intelligence Suite - Design Thinking Workflow_
_Merged PR #29: Security hardening complete_