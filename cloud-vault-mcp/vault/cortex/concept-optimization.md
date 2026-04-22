---
title: "Concept Optimization"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.9
  stage: growing
  synapse_in: 41
  synapse_out: 43
---
## Definition

Concept optimization is the practice of improving existing concept notes in the Cohezion vault for clarity, retrieval quality, and graph connectivity. An optimized concept is one that agents can retrieve and use effectively -- it has a precise definition, accurate links, appropriate tags, and just enough content to be useful without being bloated. Optimization is distinct from [[concept-testing]] (which validates correctness) and [[concept-automation]] (which handles creation at scale).

Optimization targets three dimensions: **content quality** (is the definition clear and accurate?), **structural quality** (are links, tags, and frontmatter well-formed?), and **retrieval quality** (does the concept surface when agents search for it, and does it provide useful context when retrieved?).

## Key Properties

- **Conciseness**: Concept notes should be 15-50 lines of content. Longer notes should be split.
- **Retrieval relevance**: Tags and frontmatter should match the vocabulary agents use in search queries.
- **Link density**: Each concept should have 3-10 outbound links to related concepts and papers.
- **Stub elimination**: Placeholder text like "[Add definition here]" must be replaced with verified content.
- **Deduplication**: Overlapping concepts should be merged or clearly differentiated.

## Examples

- Converting a stub with "[Add definition here]" into a full definition with key properties
- Adding missing bidirectional links between related concepts
- Splitting a 100-line concept note into two focused atomic concepts

## Related Papers

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

- [[concept]] -- the atomic knowledge unit being optimized
- [[concept-testing]] -- validation that precedes or accompanies optimization
- [[concept-automation]] -- automating the optimization pipeline at scale
- [[token-efficiency]] -- optimized concepts reduce wasted tokens in agent context windows
- [[knowledge-graph-systems]] -- the graph whose quality depends on concept optimization

## Key Lesson Links

- [[lesson-06-ollama-latency]] -- Ollama cold-start latency (5-30s) must be budgeted; pre-warm models before pipeline execution
- [[lesson-30-holographic-projection-fallback]] -- dimensionality reduction operations require singular matrix guards and fallback paths

## Relevance to Cohezion

Concept optimization directly impacts agent performance. When agents retrieve a poorly written concept, they waste context tokens on unhelpful text and may make incorrect inferences. Vault enrichment sessions -- where stubs are expanded, links are added, and definitions are sharpened -- are concept optimization in practice. The lessons linked above represent optimization knowledge extracted from real operational experience.

## Skills

- code_simplification — Code refactoring for elegance
