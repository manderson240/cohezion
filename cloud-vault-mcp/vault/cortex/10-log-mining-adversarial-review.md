---
title: "10 Log Mining Adversarial Review"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.95
  stage: growing
  synapse_in: 14
  synapse_out: 17
---
## Definition

Log mining adversarial review is the quality-assurance step applied to insights extracted from Claude Code session logs before they become permanent vault content. The [[adversarial-review]] pattern is applied specifically to mined lessons: assume the extracted insight is wrong, overfitted to a single session, or misleadingly framed, and verify it against independent evidence. This prevents the vault from accumulating plausible-sounding but incorrect knowledge.

The review process checks three dimensions: **accuracy** (does the lesson accurately describe what happened?), **generalizability** (does this pattern recur, or was it a one-off?), and **actionability** (can an agent use this lesson to make better decisions?).

## Key Properties

- **Assume-wrong posture**: Start by trying to disprove the mined insight rather than confirm it.
- **Cross-session validation**: Check whether the pattern appears in multiple sessions, not just one.
- **Root cause verification**: Confirm the lesson identifies the actual root cause, not a symptom or coincidence.
- **Actionability check**: A lesson that cannot change future agent behavior is not worth storing.
- **Deduplication**: Verify the insight is not already captured by an existing lesson or concept.

## Examples

- A mined insight claims "ruff auto-formats on save" but adversarial review reveals the real issue is that the editor, not ruff, triggers reformatting -- the lesson is reframed (see [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]])
- A pattern found in one session ("YAML folded scalars cause parsing failures") is confirmed across three sessions before becoming [[lesson-24-yaml-folded-scalar-trap]]
- A candidate lesson about "slow CI" is rejected because the slowness was caused by a network outage, not a repeatable architectural issue

## Related Papers

- [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]]
- [[lesson-09-ruff-hook-fights]]
- [[lesson-16-pre-commit-hooks-stage-override]]
- [[lesson-17-stale-branch-mining]]
- [[lesson-20-ci-scope-discipline]]
- [[lesson-21-runtime-json-pollution]]
- [[lesson-24-yaml-folded-scalar-trap]]
- [[lesson-27-hook-file-revert]]
- [[lesson-32-concurrent-pytest-contention]]
- [[lesson-33-skill-keyword-matching-is-broad]]
- [[lesson-34-test-hang-unmocked-live-service]]
- [[lesson-37-experience-guided-execution-works-new]]
- [[lesson-38-singleton-executor-for-sessions-new]]

## Related Concepts

- [[10-claude-log-mining-architecture]] -- the mining system whose output this review validates
- [[adversarial-review]] -- the general adversarial review pattern applied to all vault content
- [[concept-testing]] -- analogous validation applied to concept notes
- [[concept-validation]] -- the formal validation process for knowledge accuracy

## Relevance to Cohezion

Without adversarial review, log mining would fill the vault with noise -- single-session flukes, misattributed causes, and overly specific lessons that mislead agents. This review step is what distinguishes the Cohezion vault from a raw log dump. Every numbered lesson in the vault has passed through adversarial review, which is why agents can trust them as reliable context.
