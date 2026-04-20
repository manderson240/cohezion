---
title: "Session Retrospective Notes"
date: "2026-02-07"
tags: [pattern, workflow, knowledge-capture, vault-automation]
aspect: thinker
neural:
  activation: 0.74
  stage: growing
  synapse_in: 10
  synapse_out: 12
---

## Problem

At the end of an AI-assisted engineering session, valuable context — architectural decisions made, experiments run, concepts clarified — exists only in the conversation transcript. Once the session ends and the context window is gone, that knowledge is lost unless explicitly captured. Manually writing up session notes is tedious and often skipped.

## Solution

Before ending a session, run a **structured retrospective pass** that creates permanent vault notes for each significant accomplishment. For each item:

1. **Classify** — Is it a decision, experiment, pattern, or concept?
2. **Match the template** — Use the target directory's `_template.md` frontmatter schema
3. **Cross-link** — Add `[[wiki-links]]` between related notes from the same session and to existing vault content
4. **Write from what happened** — Use the actual session transcript as source material, not aspirational descriptions

A single session typically produces 2-5 notes across directories. Creating them in one batch at session end is more efficient than writing incrementally.

## Code Example

Prompt pattern for the retrospective pass:

```markdown
Create session retrospective notes for the following accomplishments:

1. [Decision] We chose X architecture because Y → `decisions/YYYY-MM-DD-slug.md`
2. [Experiment] We tested hypothesis X, result was Y → `experiments/YYYY-MM-DD-slug.md`
3. [Pattern] We discovered reusable approach X → `patterns/slug.md`
4. [Concept] We defined/clarified X → `concepts/slug.md`

Requirements:
- Match each directory's _template.md frontmatter schema
- Cross-link notes with [[wiki-links]]
- Content reflects what actually happened (reference transcript if needed)
```

## When to Use

- **End of every non-trivial session** — If the session produced decisions, discoveries, or reusable approaches, capture them
- **After multi-step work** — Sessions involving exploration → decision → implementation are prime candidates
- **When the [[compound-engineering]] vault would benefit** — Ask: "Would future-me or future-agents benefit from knowing what happened here?"
- **Skip for trivial sessions** — Quick bug fixes or single-file edits don't need retrospectives

## Related Patterns

- [[pattern-compound-engineering]] — session retrospectives are the "Extract" phase of the compound engineering cycle
- [[automated-concept-extraction]] — automated concept extraction can accelerate the classification step of retrospectives
- [[vault-completion-retrospective]] — the vault-level retrospective pattern that aggregates session-level findings
- [[multi-session-compound-engineering-workflow]] — retrospectives bridge individual sessions into multi-session compound workflows

## Related Decisions

- [[2026-02-10-canvas-driven-compound-engineering]] — canvas-driven compound engineering relies on session retrospectives to populate the knowledge graph
- [[2026-02-14-phases-1-3-retrospective-key-learnings]] — example of a retrospective that extracted key learnings across multiple phases
- [[2026-02-20-session-59-compound-engineering-complete]] — session completion record that was produced by this retrospective pattern

## Related Concepts

- [[experience-feedback-loop]] — retrospectives are the human-visible layer of the experience feedback loop
- [[meta-learning]] — retrospective extraction is a form of meta-learning applied to engineering sessions
- [[knowledge-graph-systems]] — retrospective notes feed into the knowledge graph as structured nodes
