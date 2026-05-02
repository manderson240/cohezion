---
title: "Concept Automation"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 51
  synapse_out: 45
---
## Definition

Concept automation refers to the programmatic creation, maintenance, and enrichment of concept notes in the Cohezion vault. Rather than manually writing every concept note, automation pipelines generate stub notes from structured data (papers, lessons, agent logs), populate frontmatter fields, create initial wiki-links, and flag notes for human review. The goal is to scale vault coverage without sacrificing quality -- automation handles the mechanical work while humans and [[concept-testing]] ensure accuracy.

Automation in the Cohezion vault operates at multiple levels: **generation** (creating stubs from imported data), **linking** (detecting and creating wiki-links between related notes), **validation** (schema-checking frontmatter and link integrity), and **enrichment** (expanding stubs with content from primary sources).

## Key Properties

- **Stub generation**: Auto-create concept notes with correct frontmatter from import pipelines.
- **Link inference**: Detect concept references in papers and lessons, create bidirectional links.
- **Schema enforcement**: Validate that generated notes follow the vault's frontmatter schema.
- **Human-in-the-loop**: Automation generates candidates; humans verify before concepts become permanent.
- **Hook integration**: Pre-commit hooks validate note structure before changes enter version control.

## Examples

- Importing 38 lesson notes and auto-generating concept stubs for referenced topics
- Running a bidirectional link pass to add ~500 wiki-links across vault layers
- Pre-commit hooks that validate YAML frontmatter tags are arrays, not strings

## Related Papers

- [[2026-02-09-lessons-integration-complete]]
- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]]
- [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]]
- [[lesson-03-critical]]
- [[lesson-04-surgery-lesson]]
- [[lesson-05-surrealdb]]
- [[lesson-06-ollama-latency]]
- [[lesson-07-gtt-carveout-illusion]]
- [[lesson-08-import-graph]]
- [[lesson-09-ruff-hook-fights]]
- [[lesson-10-gitlab-ci-runner]]
- [[lesson-11-team-agent-efficiency]]
- [[lesson-12-layered-validation]]
- [[lesson-13-8-6m-file-incident]]
- [[lesson-14-cleanup-is-multi-pass]]
- [[lesson-15-system-lockup-2026-01-27]]
- [[lesson-16-pre-commit-hooks-stage-override]]
- [[lesson-17-stale-branch-mining]]
- [[lesson-18-mock-live-services-in-tests]]
- [[lesson-19-session-awareness-protocol]]
- [[lesson-20-ci-scope-discipline]]
- [[lesson-21-runtime-json-pollution]]
- [[lesson-22-gitignore-ordering]]
- [[lesson-23-stash-branch-switch-hazard]]
- [[lesson-24-yaml-folded-scalar-trap]]
- [[lesson-25-uv-venv-contention]]
- [[lesson-26-never-print-credentials]]
- [[lesson-27-hook-file-revert]]
- [[lesson-28-non-critical-tracking-pattern]]
- [[lesson-29-batch-cache-two-phase]]
- [[lesson-30-holographic-projection-fallback]]
- [[lesson-31-operation-specific-modulation]]
- [[lesson-32-concurrent-pytest-contention]]
- [[lesson-33-skill-keyword-matching-is-broad]]
- [[lesson-34-test-hang-unmocked-live-service]]
- [[lesson-35-non-blocking-observability-pattern-new]]
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]]
- [[lesson-37-experience-guided-execution-works-new]]
- [[lesson-38-singleton-executor-for-sessions-new]]

## Related Concepts

- [[concept]] -- the atomic knowledge unit that automation produces
- [[concept-testing]] -- the validation step applied to auto-generated concepts
- [[concept-optimization]] -- improving the output of concept automation
- [[workflow-orchestration]] -- the broader pipeline that concept automation plugs into
- [[non-blocking-observability]] -- automation should log telemetry without blocking vault operations
- [[inbox-triager]] -- a specific concept automation agent that processes inbox notes into structured vault entries

## Key Lesson Links

- [[lesson-16-pre-commit-hooks-stage-override]] -- pre-commit hooks that modify and re-stage files can commit unintended changes; review staged content after hooks run
- [[lesson-09-ruff-hook-fights]] -- ruff with --fix in pre-commit hooks must be followed by git add of modified files or the hook fights itself in a loop

## Relevance to Cohezion

Concept automation is what makes the vault scalable. The Cohezion framework generates dozens of lessons and paper references per session; without automation, the vault would accumulate unlinked, unstructured notes faster than humans can curate them. The automation pipeline -- stub generation, link inference, schema validation -- ensures the knowledge graph grows structured even at high velocity.

## Skills

- adaptive_template_engine — Automated code generation from templates
- ADAPTIVE_TEMPLATE_PRIME — Dynamic blueprint refinement
