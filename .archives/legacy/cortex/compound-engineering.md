---
title: "Compound Engineering"
date: "2026-02-07"
tags: [concept, methodology, knowledge-management]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 286
  synapse_out: 69
---

## Definition

**Compound engineering** is a knowledge management approach where decisions, experiments, and patterns are systematically captured and accumulated so they compound into reusable knowledge over time. Rather than treating each engineering session as isolated work, compound engineering treats every decision, failed experiment, and discovered pattern as an asset that makes future work faster and better-informed.

## How It Works

The approach rests on three pillars, each with a corresponding vault directory:

1. **Decisions** (`decisions/`) — Architecture Decision Records (ADRs) capture the *why* behind choices. When a similar question arises later, the prior reasoning is available — including the alternatives that were considered and rejected. See the [[2026-02-07-event-driven-inbox-processor]] ADR for an example.

2. **Experiments** (`experiments/`) — Hypothesis-driven logs capture what was tried, what happened, and what was learned. Failed experiments are as valuable as successful ones — they prevent repeating dead ends. See [[2026-02-07-ai-research-agent-for-vault-notes]] for an example.

3. **Patterns** (`patterns/`) — Reusable solutions extracted from project work. When a problem is solved well, the solution is generalized and stored for future use, including code examples and guidance on when to apply it.

## The Compounding Effect

The value of the vault grows nonlinearly:

- **Session 1** produces a few notes. The vault is a simple record.
- **Session 10** has enough prior decisions that new work starts by checking what was already decided. Redundant research is eliminated.
- **Session 100** has a rich web of cross-linked decisions, experiments, and patterns. New projects begin with relevant context automatically surfaced. The vault becomes an institutional memory that survives context windows, session boundaries, and team changes.

## Role in the Cohezion Vault

The Cohezion vault is built around compound engineering. The Cloud Vault MCP Server exposes this workflow programmatically through three operation layers:

- **`VaultOps`** — Core read/write/search operations on the vault filesystem
- **`CompoundOps`** — Structured logging of decisions, experiments, and patterns with enforced frontmatter schemas
- **`ObsidianOps`** — Cross-linking via backlinks, tags, and wiki-links that connect knowledge across directories

The `inbox/` directory serves as the entry point: raw ideas are captured quickly, then processed into the appropriate permanent directory. The proposed [[2026-02-07-event-driven-inbox-processor|inbox processor daemon]] would automate this flow, using AI to classify and structure incoming notes.

## Relationship to AI-Assisted Engineering

Compound engineering is especially powerful when combined with AI agents:

- Agents can **read** prior decisions and patterns before starting new work, avoiding known pitfalls
- Agents can **write** structured records of their own decisions and discoveries, contributing to the vault
- The vault provides **persistent memory** that spans across context windows and sessions — solving the "blank slate" problem where each AI conversation starts from zero

The [[2026-02-07-ai-research-agent-for-vault-notes|research agent experiment]] demonstrated that AI agents can autonomously produce vault-quality content, validating the compound engineering workflow end-to-end.

## Primary Sources

- Andrew S. Grove (1983). *High Output Management*. [https://www.amazon.com/High-Output-Management-Andrew-Grove/dp/0679762884](https://www.amazon.com/High-Output-Management-Andrew-Grove/dp/0679762884) — Grove's principle that strategic decisions made early disproportionately affect organizational leverage; early planning pays off 10x
- Communications of the ACM (2024). *Knowledge Management with Patterns*. [https://cacm.acm.org/research/knowledge-management-with-patterns/](https://cacm.acm.org/research/knowledge-management-with-patterns/)
- Lifecycle Insights (2024). *Engineering Knowledge Management*. [https://lifecycleinsights.com/tech-guide/engineering-knowledge-management](https://lifecycleinsights.com/tech-guide/engineering-knowledge-management)

## Core Principles

1. **Validate Before Scaling**: [[implementation-first-infrastructure-later]] — Prove concepts with minimal tokens before investing in infrastructure
2. **Token Efficiency**: [[token-efficiency]] — Optimize LLM token consumption to maximize output per token spent
3. **Template Reuse**: [[template-reuse]] — Copy working patterns (87% token savings) instead of building from scratch
4. **Meta-Learning**: [[meta-learning]] — Extract lessons from failures (7.6x → 757x ROI over 100 projects)
5. **ROI Analysis**: [[roi-analysis]] — Measure compound returns to prioritize high-reuse investments
6. **Structured Capture**: Use CompoundOps to enforce frontmatter schemas for decisions/experiments/patterns

## Navigation

- [[MOC-compound-engineering]] — Map of Content for compound engineering, sessions, retrospectives, and token efficiency

## Related Concepts

### Methodology Layer
- [[meta-learning]] — Learning from learning (strategic optimization)
- [[roi-analysis]] — Measuring compound returns (investment framework)
- [[token-efficiency]] — Token optimization (tactical execution)
- [[template-reuse]] — Reusable implementations (87% savings)

### Technical Layer
- [[agentic-ai]] — AI agents as compound engineering contributors
- [[context-management]] — Managing context windows for compound knowledge
- [[FLUME-Architecture]] -- FLUME embeddings enable compound engineering by making prior session knowledge retrievable
- [[Ouroboros-Loop]] -- the autonomic loop that automates compound engineering's capture-and-reuse cycle
- [[agyn-multi-agent-software-engineering]] — Agyn's captured-learnings model applies compound engineering to multi-agent teams: each session's learnings compound into improved future coordination
- [[gemini-cli-ai-employees-agent-factory]] — SOP-in-markdown is compound engineering for agent instructions: reusable SOPs capture proven workflows and compound value across repeated tasks
- [[python-314-free-threaded-gil-removal]] — free-threaded Python enables true parallel compound engineering sessions without the process isolation overhead of subprocess-based parallelism
- [[knowledge-graph-densification]] — the systematic process that compounds knowledge graph value over time
- [[bidirectional-linking]] — the linking convention enabling compound knowledge discovery
- [[inbox-triager]] — automated note processing tool in the compound engineering pipeline
- [[decision-linker]] — automated decision linking tool creating typed semantic edges
- [[research-lineage]] — the provenance chain tracking how knowledge compounds across sessions

## Relevance to Cohezion

Compound engineering is the foundational philosophy of Cohezion itself, formalized through the Cloud Vault MCP Server's three operation layers: VaultOps (read/write), CompoundOps (structured logging), and ObsidianOps (cross-linking). The CompoundExecutor leverages this accumulation by reading prior decisions via log_decision, extracting patterns through extract_pattern, and using find_relevant_context to surface institutional knowledge that compounds value over time.

- [[CascadeTimeline]] — the cascade timeline makes visible how compound engineering decisions influence downstream outcomes over time
- [[DecisionHealthDashboard]] — the dashboard monitors decision health within the compound engineering lifecycle

## Key Patterns

- [[implementation-first-infrastructure-later]] — Validate before scaling infrastructure
- [[session-retrospective]] — Capture lessons from each engineering session

## Related Lessons

- [[lesson-stop-assessing-start-changing]] — HIGH severity: assessment without execution is not compounding; each session must change the graph, not just describe it
- [[2026-03-05-lessons-corpus-taxonomy]] — project to extract the 45-lesson corpus as a publishable failure taxonomy
- [[lesson-adversarial-review-before-execution]] — adversarial review before execution prevents 90% wasted effort; 45x ROI on 10-minute review investment
- [[lesson-effective-retrospectives]] — structured retrospective format extracts maximum reusable patterns from session experience; feeds the compound learning loop
- [[lesson-37-experience-guided-execution-works-new]] — experience-guided execution is the engine of compound knowledge growth; context injection replaces re-discovery

## Decisions & Experiments

- 📋 [[2026-02-10-kyutai-token-waste-postmortem]] — Critical lesson: 61K token waste from infrastructure-first approach
- 📋 [[2026-02-08-bmad-framework-removal]] — Removing unused framework patterns
- 📋 [[2026-02-07-event-driven-inbox-processor]] — Event-driven inbox processing
- 🔬 [[2026-02-07-ai-research-agent-for-vault-notes]] — AI research agent validation
- 🔬 [[2026-02-24-sprint-4-end-to-end-integration-compound-execution-flume-cache-pipeline|Sprint 4: Compound Execution FLUME Cache Pipeline]] — end-to-end integration of the compound execution pipeline with FLUME cache
- 📋 [[vault-knowledge-graph-densification|Vault Knowledge Graph Densification]] — systematic cross-linking of papers and concepts to densify the compound knowledge graph
- 📋 [[2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — end-to-end run of the compound engineering spec workflow; real-world validation of the full decision→experiment→pattern cycle
- 🔬 [[2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop|Recursive Challenger Session 68]] — applying compound engineering recursively to improve the compound engineering loop itself
- 📋 [[2026-02-20-session-59-autonomous-compound-engineering-foundation|Session 59: Autonomous Compound Engineering Foundation]] — the implementation that operationalizes autonomous compound engineering with TaskDecomposer and skill infrastructure
- 📋 [[2026-02-20-session-58-cosmic-fire-module-retrospective|Session 58: Cosmic Fire Retrospective]] — parallel agent execution and integration verification exemplifying compound engineering
- 📋 [[2026-02-22-post-crash-venv-recovery-pytest-missing-despite-pyprojecttoml|Post-Crash Venv Recovery]] — crash recovery demonstrates reproducible environment importance in compound workflows
- 📋 [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams|Graph Densification Complete]] — graph densification compounds the value of every future context retrieval

## Related Patterns & Projects

- [[session-55-compound-engineering-learnings]] — Session 55 learnings on data lifecycle governance through compound engineering (13:1 ROI)
- [[daily-cli-tool-update-with-version-comparison]] — automated tool updates compound reliability by preventing version skew across sessions
- [[repo-and-process-debt]] — addressing process debt compounds reliability: each debt item fixed makes all future sessions more productive

## Assessments

- [[2026-03-05-separate-cohezion-a-from-cohezion-b|Two Cohezions Decision]] — proposed: separate the empirically-grounded platform (Cohezion A) from the cosmological framing (Cohezion B) in external materials; vocabulary compounding as barrier
- [[2026-03-05-shoshin-assessment|Shoshin Assessment]] — beginner's mind reading diagnosing vault drift: compounding happening at documentation layer, not knowledge/results layer
- [[2026-03-03-vault-hidden-contributions-assessment|Hidden Contributions Assessment]] — identifies compound engineering as one of three original contributions hiding in the vault, referenced constantly but never formally articulated as a theory

## Session References

- [[session-49-retrospective]] — foundation alone = 0% benefit; activation cascade is the compound multiplier
- [[session-50-handoff]] — single __init__.py change activates 100+ callsites as compound cascade
- [[SESSION-44-FINAL-SUMMARY]] — quality gate discipline compounds across future sessions

## Daily References

- [[SESSION-63-FINAL-SUMMARY-2026-02-15]]
- [[SESSION-57-COMPLETION-SUMMARY]]
- [[SESSION-2026-02-10-WORK-SUMMARY]]
- [[2026-02-23-flume-strategic-roadmap]]
- [[2026-02-23-anthropic-alignment-investigation]]
- [[2026-02-14-wave-1-status-snapshot]]
- [[2026-02-14-wave-1-delivery-complete]]
- [[2026-02-14-phase-6b-final-report]]
- [[2026-02-14-phase-6b-execution-complete]]
- [[2026-02-13-session-173cdb02]]
- [[2026-02-10-canvas-engineering-blueprint]] — canvas-driven compound engineering blueprint using Obsidian Canvas as an analytical engine
- [[2026-02-10-canvas-execution-log]] — canvas-driven compound engineering execution log (Phases 0-5)
- [[2026-02-10-CANVAS-PLAN-SUMMARY]] — executive summary for canvas-driven compound engineering
- [[2026-02-10-strategic-framework-deployment]] — meta-concepts deployed as strategic infrastructure for compound engineering
- [[2026-02-10-phase-a-documentation-complete]] — Phase A documentation: all 8 deliverables for Phase A infrastructure
- [[2026-02-10-phase-a-execution-complete]] — Phase A decision enrichment complete via canvas-driven compound engineering

## Agent Outputs

- implementation_plan — Implementation plans across 87 agent sessions
- implementation_plan_v2 — Implementation Plan V2 (production hardening)
- implementation_plan_v3 — Implementation Plan V3
- implementation_plan_v4 — Implementation Plan V4
- implementation_plan_v5 — Implementation Plan V5
- implementation_plan_v6 — Implementation Plan V6
- implementation_plan_v7 — Implementation Plan V7
- implementation_plan_v8 — Implementation Plan V8
- implementation_plan_phase2 — Implementation Plan Phase 2
- implementation_plan_phase5 — Implementation Plan Phase 5
- implementation_plan_phase9 — Implementation Plan Phase 9
- implementation_plan_phase10 — Implementation Plan Phase 10
- implementation_plan_phase11 — Implementation Plan Phase 11
- implementation_plan_strategic — Implementation Plan: Strategic
- implementation_plan_redundancy — Implementation Plan: Redundancy
- implementation_plan_desperation — Implementation Plan: Desperation (recovery mode)
- implementation_plan_hud — Implementation Plan: HUD interface
- implementation_plan_swapping — Implementation Plan: Model swapping
- progress_report — Progress report on compound engineering execution
- readiness_report — Readiness report for Anthropic MTS
- [[roadmap_phases_4_13]] — Roadmap phases 4-13 planning
- [[roadmap_gateways_33_42]] — Roadmap gateways 33-42 planning

## Skills

- [[compound-engineering]] — Self-extending engineering pipelines
- COMPOUND_ENGINEERING_PRIME — Cross-platform agentic orchestration
- gateway_architecture — Compound effects in AI system design
- RETROSPECTIVE_SKILL — Self-extending pipeline synthesis

## Specs & Meta
- [[2026-02-20-autonomous-compound-engineering-spec|Autonomous Compound Engineering Spec]] — architecture for self-improving compound engineering system
- [[2026-02-20-session-59-enhancement-roadmap|Session 59 Enhancement Roadmap]] — enhancement roadmap for compound engineering, token efficiency, and context awareness
- [[compound-demo-0|Compound Demo Iteration 0]] — initial compound demo recording with performance metrics
