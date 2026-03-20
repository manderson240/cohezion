---
title: "MOC — Compound Engineering"
date: 2026-03-04
tags: [moc, navigation, compound-engineering, methodology]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 13
  synapse_out: 35
---

# Map of Content — Compound Engineering

## Overview

Compound engineering is the foundational methodology of the Cohezion framework: every decision, experiment, and pattern is systematically captured so knowledge compounds across sessions rather than being lost when context windows close. This topic covers the execute-observe-extract-index-inject cycle, session retrospectives that transform ephemeral experience into durable vault knowledge, token efficiency strategies that maximize output per token spent, and the meta-learning feedback loops that make each session smarter than the last.

## Core Concepts

- [[compound-engineering]] — Knowledge management approach where decisions and patterns compound into reusable knowledge over time
- [[experience-feedback-loop]] — The cycle that converts session experience into permanent vault knowledge
- [[session-retrospective]] — Structured end-of-session reflection to extract reusable knowledge before context is lost
- [[meta-learning]] — Learning from the process of learning itself to improve future efficiency
- [[token-efficiency]] — Optimization of LLM token consumption to maximize functional output per token spent
- [[token-efficiency-patterns]] — Concrete patterns for reducing token waste across agent workflows
- [[context-management]] — Strategies for optimizing information payloads delivered to AI systems
- [[agent-context]] — The information payload an agent accesses at a given moment in its execution cycle
- [[agent-journey-tracking]] — Observability of agent workflows for debugging and knowledge extraction
- [[concept-caching]] — Storing computed results for reuse across sessions without recomputing
- [[concept-modularity]] — Principle that knowledge nodes should be self-contained and independently reusable
- [[concept-testing]] — Validating that knowledge concepts are accurate before they become permanent graph nodes
- [[concept-validation]] — Ensuring concept notes are correct, complete, and genuinely useful
- [[implementation-first-infrastructure-later]] — Build working features before abstracting infrastructure
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] — Mandatory knowledge extraction before any destructive operation
- [[skill-taxonomy-7-layer-architecture]] — Classification of capabilities across 7 source layers for routing clarity
- [[honest-metrics-over-inflated-claims]] — Ground truth verification before claiming improvement
- [[non-blocking-observability]] — Telemetry that never interrupts the primary agent workflow

## Key Decisions

- [[2026-02-10-compound-engineering-meta-learning]] — Expanding log mining into a continuous meta-learning feedback loop
- [[2026-02-10-token-efficient-compound-engineering-roadmap]] — One-month roadmap for systematizing token-efficient compound engineering
- [[2026-02-10-compound-linking-plan-adversarial-review]] — Adversarial review rejecting a compound linking plan due to critical flaws
- [[2026-03-07-skill-pruning-consolidation-plan]] — Prune ~60 redundant/dormant skills to reduce routing noise and token waste
- [[2026-02-10-framework-driven-prioritization]] — ROI framework applied to prioritize SurrealDB queries, Sheets pipeline, and Ollama MCP against each other; 144x compound ROI over 1 year

## Patterns

- [[pattern-compound-engineering]] — The meta-pattern: execute, observe, extract, index, inject
- [[session-retrospective-notes]] — Automating session knowledge capture to prevent context loss
- [[mini-adversarial-review-checkpoints]] — Lightweight quality gates inserted at key implementation milestones
- [[honest-time-tracking-all-costs]] — Track all work categories (setup, debugging, reviews, docs) for accurate compression metrics; Session 57 audit revealed 44% hidden costs
- [[vault-first-session-protocol]] — Strict per-session protocol for persisting artifacts to vault before context fills; prevents knowledge loss at context limits
- [[parallel-session-coordination-via-vault-registry]] — Vault-as-registry for multi-session coordination; prevents file conflicts in parallel agent runs
- [[github-actions-as-autonomous-claude-code-scheduler]] — Scheduled GitHub Actions workflows that run compound engineering maintenance (vault audits, research scouting) autonomously

## Research Papers

- [[scaling-agent-systems]] — Toward a science of scaling multi-agent systems (Google Research)
- [[few-shot-prompting-agentic-coding]] — Few-shot prompting techniques for agentic coding workflows
- [[testing-agent-skills-with-evals]] — Systematic skill evaluation using structured evals
- [[langchain-deep-agents-context-management]] — Deep agents and context management patterns in LangChain

## Lessons Learned

- [[lesson-adversarial-review-before-execution]] — Adversarial review before execution prevents wasted effort
- [[lesson-35-non-blocking-observability-pattern-new]] — Synchronous telemetry stalls workflows; must be async
- [[lesson-04-surgery-lesson]] — Modify only what is required; surgical edits prevent regressions
- [[lesson-03-critical]] — Critical operations require explicit verification before proceeding

## Experiments

- [[2026-02-11-session-56-retrospective-and-plan-refinement]] — Session retrospective experiment proving structured reflection improves planning
- [[2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop]] — Recursive challenger loop for autonomous improvement via adversarial self-review
- [[2026-02-10-phase4-universe-simulation-complete]] — Phase 4 complete: Decision Fork Simulator, Task Optimizer, and Knowledge Gap Explorer (1,800+ LOC, 73% gap-prediction accuracy)
- [[2026-02-16-phases-4b-7-completion-summary]] — Phases 4B-7 completion summary: 8 deliverables, 18 adversarial review findings, three execution option paths

## Session Checkpoints (Entire.io)

- [[_index|Entire.io Checkpoint Timeline]] — 127 nightly session checkpoints (Feb–Mar 2026) synced from Entire.io, with 8 milestone checkpoints linking to ADRs, patterns, and concept notes

## Start Here

- **New to this topic?** Start with [[compound-engineering]]
- **Looking for patterns?** See [[pattern-compound-engineering]]
- **Recent work:** [[experience-feedback-loop]]

## Related Maps

- [[MOC-platform-infrastructure]]
- [[MOC-safety-alignment]]
- [[MOC-astrophysics]]
