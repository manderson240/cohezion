---
title: "Compound Engineering"
date: "2026-02-07"
tags: [concept, methodology, knowledge-management]
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

## Related Concepts

### Methodology Layer
- [[meta-learning]] — Learning from learning (strategic optimization)
- [[roi-analysis]] — Measuring compound returns (investment framework)
- [[token-efficiency]] — Token optimization (tactical execution)
- [[template-reuse]] — Reusable implementations (87% savings)

### Technical Layer
- [[agentic-ai]] — AI agents as compound engineering contributors
- [[context-management]] — Managing context windows for compound knowledge

## Relevance to Cohezion

Compound engineering is the foundational philosophy of Cohezion itself, formalized through the Cloud Vault MCP Server's three operation layers: VaultOps (read/write), CompoundOps (structured logging), and ObsidianOps (cross-linking). The CompoundExecutor leverages this accumulation by reading prior decisions via log_decision, extracting patterns through extract_pattern, and using find_relevant_context to surface institutional knowledge that compounds value over time.

## Key Patterns

- [[implementation-first-infrastructure-later]] — Validate before scaling infrastructure
- [[session-retrospective]] — Capture lessons from each engineering session

## Decisions & Experiments

- 📋 [[2026-02-10-kyutai-token-waste-postmortem]] — Critical lesson: 61K token waste from infrastructure-first approach
- 📋 [[2026-02-08-bmad-framework-removal]] — Removing unused framework patterns
- 📋 [[2026-02-07-event-driven-inbox-processor]] — Event-driven inbox processing
- 🔬 [[2026-02-07-ai-research-agent-for-vault-notes]] — AI research agent validation
- 📋 [[decisions/2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — end-to-end run of the compound engineering spec workflow; real-world validation of the full decision→experiment→pattern cycle
- 🔬 [[experiments/2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop|Recursive Challenger Session 68]] — applying compound engineering recursively to improve the compound engineering loop itself
- 📋 [[decisions/2026-02-20-session-59-autonomous-compound-engineering-foundation|Session 59: Autonomous Compound Engineering Foundation]] — the implementation that operationalizes autonomous compound engineering with TaskDecomposer and skill infrastructure
