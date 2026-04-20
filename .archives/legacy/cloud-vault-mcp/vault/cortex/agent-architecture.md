---
title: "Agent Architecture"
date: 2026-02-19
tags: [concept, agentic-ai, multi-agent-systems, agent-loop-architecture]
related_concepts: [agent-loop-architecture, agentic-ai, multi-agent-systems, mcp-model-context-protocol, tool-use]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 36
  synapse_out: 46
---
## Definition

Agent architecture defines the structural design of an autonomous AI agent — how it perceives inputs, maintains state, reasons about actions, and executes against external systems. The canonical pattern is the observe-reason-act loop (see [[agent-loop-architecture]]), but production architectures extend this with memory hierarchies, tool registries, role specialization, and inter-agent communication protocols.

Architectures span a spectrum: single-agent systems where one LLM completes an entire workflow, to multi-agent systems where specialized sub-agents handle distinct domains (researcher, planner, executor, reviewer). The key design decisions are role boundaries, shared context strategy, and failure isolation — poorly designed agents amplify errors rather than containing them.

In Cohezion, the agent architecture centers on the CompoundExecutor, which orchestrates an 11-step pipeline. Specialized agents (domain experts, skill refiners, retrospection engines) communicate through a shared [[mcp-model-context-protocol]] interface rather than direct coupling, enabling hot-swappable components and independent scaling.

## Key Properties

- **Role specialization**: Each agent is optimized for a narrow task type (research, code, review)
- **Memory hierarchy**: Short-term (context window), mid-term (session cache), long-term (vault)
- **Tool registry**: Agents access external systems through a standardized [[tool-use]] interface
- **Failure isolation**: Sub-agent failures should not cascade; circuit breakers and fallbacks are essential
- **Communication protocol**: Agents exchange structured messages, not raw text

## Related Papers

- [[2026-02-09-phase1-completion]]
- [[2026-02-09-phase1-results]]
- [[2026-02-09-research-gaps-analysis]]
- [[agentic-ai-memory-hierarchies]]
- [[claude-code-community-skills]]
- [[langchain-deep-agents-context-management]]
- [[llamaagents-builder]]
- [[openai-codex-agent-loop]]
- [[scaling-agent-systems]]
- [[agyn-multi-agent-software-engineering]] — Agyn's four-role (manager, researcher, engineer, reviewer) architecture is a reference design for role-specialized agent teams
- [[group-evolving-agents-gea-framework]] — GEA introduces a new architecture class beyond the five canonical types: collectively-evolving agent groups selected by performance+novelty scoring
- [[nvidia-nemotron-3-nano-nemo-gym]] — NeMo Gym's agentic safety dataset and environment design directly inform agent architecture decisions around tool-use safety
- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF's interoperability standards (MCP, A2A, AGENTS.md) are the cross-cutting architectural substrate that any production agent architecture must conform to

## Decisions

- [[2026-03-06-adopt-meridian-concierge-agent-over-mcp-infrastructure-prd]] — Meridian concierge agent architecture: single intelligence layer over N platforms × M tools
- [[2026-03-05-github-issues-as-remote-claude-code-terminal]] — GitHub Issues as a zero-latency remote command interface for agent orchestration

## Navigation

- [[MOC-agentic-ai]] — Map of Content for the agentic AI topic area

## Related Concepts

- [[agent-loop-architecture]] — the observe-reason-act cycle that defines agent execution flow
- [[agentic-ai]] — the broader class of autonomous AI systems built on agent architectures
- [[multi-agent-systems]] — architectures composed of multiple collaborating agents
- [[mcp-model-context-protocol]] — the protocol enabling agents to call external tools
- [[tool-use]] — how agents interact with external APIs and services
- [[Ouroboros-Loop]] — the autonomic Sense/Feel/Act feedback cycle for real-time agent stability monitoring
- [[FLUME-Architecture]] — the VAE architecture providing latent space perception for agent trajectory analysis
- [[2026-02-11-use-event-driven-daemon-for-entire-io|Event-Driven Daemon for IO]] — daemon-based IO handling as an architectural choice for low-latency agent communication
- [[error-handling-with-dlq]] — DLQ provides failure isolation within the agent architecture, preventing cascade failures across pipeline stages
- [[reinforcement-learning]] — RL policies train agent decision-making within architectures that define the action and observation spaces
- [[cognitive-science]] — agent architectures implement cognitive loops (observe-reason-act) inspired by cognitive science models of intelligent behavior
- [[cybernetics]] — the original science of feedback, control, and governance in complex systems; agent architectures are cybernetic systems (Wiener's feedback loop, Ashby's requisite variety, Beer's Viable System Model)
- [[agents-as-exotic-vacuum-objects]] — agent architecture = the dielectric surface through which computational EVOs propagate

## Related Lessons

- [[lesson-38-singleton-executor-for-sessions-new]] — singleton executor pattern prevents resource leaks across agent sessions; critical for multi-agent architectures
- [[lesson-37-experience-guided-execution-works-new]] — past session context materially improves current session quality; architecture must support context injection
- [[lesson-11-team-agent-efficiency]] — coordination overhead exceeds benefits below a task complexity threshold; informs when to use single vs. multi-agent designs

## Related Patterns & Projects

- [[role-based-multi-agent-coordination]] — role specialization pattern for assigning researcher/planner/executor/reviewer roles to agent teams
- [[local-agent-orchestration-roadmap]] — phased roadmap refining agent architecture from cloud-dependent to fully local orchestration

## Missions

- COHEZION_CHARTER — Expert Domain Lattice and recursive capability evolution
- README — Ouroboros Ganglion and biological nervous system design
- [[session_12_hardening_1770737305]] — Infrastructure hardening and API decoupling
- [[session_12_hardening_1770737831]] — Infrastructure hardening and API decoupling
- [[session_12_hardening_1770737898]] — Infrastructure hardening and API decoupling
- [[session_12_hardening_1770737305_milestone_2]] — Hardening milestone
- [[session_12_hardening_1770737305_milestone_3]] — Hardening milestone
- [[session_12_hardening_1770737831_milestone_2]] — Hardening milestone
- [[session_12_hardening_1770737831_milestone_3]] — Hardening milestone
- [[session_12_hardening_1770737831_milestone_4]] — Hardening milestone
- [[session_12_hardening_1770737898_milestone_2]] — Hardening milestone
- [[session_12_hardening_1770737898_milestone_3]] — Hardening milestone
- [[session_12_hardening_1770737898_milestone_4]] — Hardening milestone

## Relevance to Cohezion

Cohezion's agent architecture is layered: the CompoundExecutor acts as the orchestrating agent, delegating to domain-specialist agents (researcher, engineer, reviewer) via the [[mcp-model-context-protocol]]. The 11-step execution pipeline enforces role separation — alignment analysis, metrics aggregation, degradation detection, and journey tracking each run as distinct architectural concerns. The [[experience-feedback-loop]] closes the architecture by feeding retrospection outputs back into skill refinement, making the architecture self-improving over time.

## Agent Outputs

- BMAD_COHEZION_BRIDGE_DESIGN — BMAD-Cohezion Bridge Design
- COHEZION_BMAD_AUDIT — Cohezion Codebase Audit (BMAD Integration)
- ARCHITECTURE_MICROSERVICES_DRAFT — Architecture Microservices Draft
- CONNECTIVITY_GUIDE_PRIME — Connectivity Guide Prime (swarm architecture)
- high_complexity_targets — High Complexity Targets Analysis
- **Task: Holographic Interface Implementation (Phase 11)** — `Agents/Antigravity/7bba44ce-6ae2-4ddd-af67-824f717d45eb/task.md`
- **Microservices Architecture Draft** — `Agents/Antigravity/d9c1fcdb-69db-458c-b64a-f26e49625c33/ARCHITECTURE_MICROSERVICES_DRAFT.md`

## Skills

- AGENTIC_DESIGN_PRIME — System architecture communication
- bmad_workflow — Agent personas and menu-driven interaction
- CAPABILITY_REGISTRY_PRIME — Capability registration for agents
- CONNECTIVITY_MANAGEMENT_PRIME — Swarm connectivity orchestration
- controller_agent — Quadrature Nexus routing pattern
- gateway_architecture — Exponential capability gateway design
