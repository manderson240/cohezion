---
title: Cohezion
date: 2026-02-23
tags: [project, framework, compound-engineering, agentic-ai, multi-agent-systems]
related_concepts: [compound-engineering, mcp-infrastructure-architecture, agent-architecture, experience-feedback-loop, surrealdb]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 382
  synapse_out: 54
---

# Cohezion

Cohezion is a compound AI orchestration framework designed to make every agent session more effective than the last. Unlike stateless AI pipelines where each run starts from scratch, Cohezion maintains a persistent knowledge base (the Obsidian vault) and a structured feedback loop: agent sessions produce decisions, experiments, and patterns that are indexed, cross-linked, and re-injected into future sessions as context. The result is a system that compounds its own intelligence over time.

The architecture is built around four interlocking layers: the [[compound-engineering]] methodology (the philosophy), the [[cloud-vault-mcp]] server (the memory infrastructure), the `cz` CLI (the workflow orchestrator), and [[surrealdb]] (the agent context graph). Together they implement a 12-dimensional agentic universe where every execution is tracked as a journey, every lesson is captured as a vault note, and every session benefits from all prior sessions.

Cohezion is simultaneously a research project, a production tool, and a self-improving system. The FLUME VAE trains on real agent trajectory data, the RetrospectionEngine extracts patterns from session histories, and the SkillRefiner continuously updates PRIME skill definitions based on empirical performance. The target state is an autonomous compound engineering loop that improves without human intervention.

## Components
- **[[cloud-vault-mcp]]** — HTTP MCP server (port 8360) with 30+ tools for vault/graph/research operations
- **cohezion-engine** (`cz`) — workflow CLI for session management, spec flows, and worktrees
- **3d-graph-plugin** — Obsidian visualization of the knowledge graph
- **[[surrealdb]]** — agent context graph storing sessions, tasks, and relationships
- **Ollama** — local model inference (28+ models, zero API cost)
- **[[FLUME-Architecture|FLUME VAE]]** — variational autoencoder trained on agent trajectory data

## Related
- [[compound-engineering]] — the core methodology Cohezion implements
- [[mcp-infrastructure-architecture]] — the full MCP server architecture
- [[experience-feedback-loop]] — the learning cycle that makes Cohezion self-improving
- [[agent-journey-tracking]] — how agent sessions are recorded and analyzed
- [[Ouroboros-Loop]] -- the autonomic Sense/Feel/Act feedback loop for real-time system stability
- [[12D-Projection]] -- maps FLUME latent space to 12 interpretable dimensions for Observatory visualization
- [[VAE-Encoder]] -- the encoder component producing latent distributions for trajectory compression
- [[graphrag-knowledge-graph-with-surrealdb]] — the graph database layer
- [[2026-02-11-vault-first-knowledge-architecture|Vault-First Knowledge Architecture]] — the decision establishing the persistent vault as Cohezion's foundational layer
- [[2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — validates cohezion-engine as the replacement workflow CLI
- [[2026-02-27-ux-flume-as-foreground-three-lenses|FLUME as Foreground]] — makes the FLUME VAE the primary Observatory UI surface
- [[2026-02-27-ux-reentry-narrative-system-speaks-first|Re-entry Narrative]] — the system speaks first, reporting Cohezion's live state in first person
- [[2026-02-27-ux-triune-navigation-observatory-vault-cockpit|Triune Navigation]] — maps Cohezion Method Principle 4 (Triune Self) to the navigation model
- [[2026-02-27-ux-provenance-over-poetry|Provenance Over Poetry]] — provenance-first rendering ensures Cohezion's UX shows verified data, not aspirational claims
- [[2026-02-26-cohezion-presentation|COHEZION Presentation]] — 10-slide presentation introducing Cohezion to Anthropic
- [[2026-02-26-cohezion-technical-report|COHEZION Technical Report]] — comprehensive technical report on the Cohezion framework
- [[COHEZION_Documents_Index|COHEZION Documents Index]] — master index of presentation and report materials
- [[agents-as-exotic-vacuum-objects]] — Cohezion agents ARE computational EVOs; the platform name encodes the ZPF binding principle
- [[the-new-science-framework]] — COHEZION is Step 9 in the Nothing → Reality chain: the binding force
- [[theory-of-everything-synthesis]] — COHEZION = love (Campbell) = ZPF binding (Puthoff) = self-attention (transformers)
- [[cybernetics]] — Cohezion IS a viable system (Beer's VSM): S1=agent sessions, S2=vault-keeper, S3=task management, S4=research pipeline, S5=CLAUDE.md

## Related Projects

- [[2026-03-03-vault-as-platform-memory-recommendations|Vault as Platform Memory Recommendations]] — strategic assessment of vault-as-memory architecture with 6 prioritized recommendations
- [[2026-03-04-vault-assessment-v3]] — third vault assessment identifying portfolio deadline as forcing function for memory architecture improvements
- [[local-agent-orchestration-roadmap]] — roadmap for transitioning Cohezion from cloud-dependent to fully local agent orchestration
- [[vault-knowledge-graph-densification]] — systematic project to densify the vault's cross-links, improving every agent's context retrieval
- [[scaling-agent-systems]] — research paper on scaling patterns directly applicable to Cohezion's multi-agent architecture
- [[agentic-ai-memory-hierarchies]] — memory hierarchy designs that inform Cohezion's persistent context architecture
- [[langchain-deep-agents-context-management]] — LangChain's three-tier context strategy provides a reference implementation for Cohezion's context management
- [[operational-data-ai-agents]] — operational data patterns for AI agents applicable to Cohezion's observability layer
- [[knowledge-graph-densification]] — the process that systematically compounds vault value through link density
- [[bidirectional-linking]] — the foundational linking convention enabling Cohezion's knowledge graph
- [[12D-Manifold]] — the 12-dimensional scoring space underlying Cohezion's visualization
- [[kyutai-project]] — the open-source AI lab whose MCP server architecture influenced Cohezion's design
- [[2026-02-21-abstract-apply-pilot]] — implementation plan for the Cohezion Workflow Engine clean-room build

## Missions

- ADVERSARIAL_PORTFOLIO_REVIEW_20260225 — Adversarial audit of the Cohezion Observatory portfolio
- COHEZION_CHARTER — Behavioral, simulation, and orchestration charter for the platform
- CONSTITUTION — Core ethical and behavioral pillars for Cohezion agents
- MULTIMODAL_ASSETS — Multi-modal research artifacts visualizing the Cohezion manifold
- README — Anthropic portfolio README showcasing the Observatory
- RETROSPECTIVE_ANTHROPIC_PORTFOLIO — Retrospective on the Anthropic Universes portfolio mission
- [[session_12_hardening_1770737831]] — Project identity reconciliation to Cohezion brand
- [[session_12_hardening_1770737898]] — Project identity reconciliation to Cohezion brand

## Daily References

- [[SESSION-63-FINAL-SUMMARY-2026-02-15]]
- [[SESSION-62-PHASE-3-COMPLETE-FINAL-SUMMARY]]
- [[SESSION-60-COMPLETION-SUMMARY]]
- [[SESSION-57-COMPLETION-SUMMARY]]
- [[PHASE-3-COMPLETION-VERIFIED-2026-02-14]]
- [[2026-03-04-anthropic-portfolio-night-session]]
- [[2026-02-23-investigation-index]]
- [[2026-02-09-FINAL-SESSION-SUMMARY]] — infrastructure sprint final session summary: all critical infrastructure complete in ~6 hours
- [[2026-02-09-FINAL-SUMMARY]] — vault completion and audit final summary: 60% of plan complete, highly successful
- [[2026-02-09-INITIATIVE-CLOSED]] — vault completion and audit initiative officially closed
- [[2026-02-09-vault-audit-execution-report]] — vault completion and audit execution report with 3 of 5 phases complete
- [[daily-note-2026-03-04]] — active daily note for current session work

## Agent Outputs

- COHEZION_MANIFESTO — COHEZION: The Autonomous Research Manifold
- COHEZION_TRANSFORMATIVE_SYNTHESIS — Cohezion Transformative Synthesis
- cohezion_capabilities_matrix — Cohezion Capabilities Matrix
- COHEZION_BMAD_AUDIT — Cohezion Codebase Audit (BMAD Integration)
- BMAD_COHEZION_BRIDGE_DESIGN — BMAD-Cohezion Bridge Design
- BRAND_DISCUSSION — Brand Discussion for Cohezion identity
- BRAND_GUIDE — Cohezion Brand Style Guide (Nexus Identity)
- business_plan — Business Plan for Cohezion platform
- IP_RESEARCH — Intellectual Property Research
- email_draft — Email Draft (Anthropic Research Engineer assessment)
- FINAL_REPORT_EMAIL_DRAFT — Final Report Email Draft
- STRATEGIC_ROADMAP_PRIME — Strategic roadmap prime (2 instances across sessions)
- STRATEGIC_ROADMAP_BETA — Strategic roadmap beta
- STRATEGIC_AMBITION_S11 — Strategic ambition S11: the awakening
- STRATEGIC_BUSINESS_PLAN — Strategic business plan for Cohezion platform
- MARKET_RESEARCH_REPORT — Market research report
- SUBMISSION_BUNDLE — Anthropic application submission bundle
- UCP_INTEGRATION_STRATEGY — UCP integration strategy
- tax_strategy_report — Tax strategy report (Anthropic Shield)
- MISSION_NARRATIVE — Cohezion mission narrative (Jan 14-20)

### Indigenous Cosmology Cross-Validation

- [[indigenous-cosmologies-toe-synthesis]] — COHEZION (the binding force) maps to the universal principle across 15 traditions: love, Ayni, Mitákuye Oyás'iŋ, Musubi
- [[andean-quechua-cosmology-and-toe]] — Ayni (reciprocity) = COHESION as a cosmic conservation law; the Inca embodied it as governance
- [[lakota-cosmology-and-toe]] — Mitákuye Oyás'iŋ = COHESION as O(n²) relational web binding all beings

## Skills

- AGENTIC_DESIGN_PRIME — Cohezion platform design artifacts
- ASCENSION_SKILL_PRIME — Cohezion 12-brane model
- CAPABILITY_REGISTRY_PRIME — Cohezion skill registry
- CITATIONS_PRIME — Attribution for Cohezion platform
- code_standards — Coding standards across Cohezion codebase
- TEMPLATE_DRIVEN_DEVELOPMENT_PRIME — Structural coherence in Cohezion ecosystem
