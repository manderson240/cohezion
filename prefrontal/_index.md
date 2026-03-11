---
title: "Decisions — Directory Index"
purpose: "Architecture Decision Records (ADRs) tracking key technical and design choices"
type: directory-index
aspect: thinker
neural:
  activation: 0.377
  stage: growing
  cluster: decisions
---

# Decisions

**Purpose:** Capture the context, rationale, and consequences of architectural and design decisions.

**Put here when:** A significant technical choice is made that affects system architecture, tooling, process, or strategy. Document the decision with context and alternatives.

**Naming:** Date-prefixed kebab-case: `YYYY-MM-DD-decision-name.md`

**Required frontmatter:**
- `title` — Decision title
- `date` — Decision date (YYYY-MM-DD)
- `status` — One of: `proposed`, `accepted`, `rejected`, `deprecated`
- `tags` — Array of tags (`[decision, topic-area]`)

**Template:** Yes — `_template.md` (includes Context/Decision/Consequences/Alternatives sections)

**Current count:** 151 notes

**Key notes:**
- [[2026-02-17-phase-2-full-verification-plan]] — Phase 2 verification strategy
- [[2026-02-12-claude-code-context-awareness-codification]] — Context awareness engine design
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]] — Repository consolidation

**Related MOC:** [[MOC-platform-infrastructure]], [[MOC-compound-engineering]]
