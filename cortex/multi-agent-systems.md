---
title: "Multi Agent Systems"
date: 2026-02-07
tags: [concept, agentic-ai, agent-loop-architecture, mcp-model-context-protocol]
related_concepts: [agentic-ai, agent-architecture, workflow-orchestration, mcp-model-context-protocol, compound-engineering]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 57
  synapse_out: 37
---

## Definition

Systems comprising multiple autonomous AI agents that collaborate to solve complex problems through real-time communication and coordinated action. Unlike single-agent systems, multi-agent systems reduce hallucinations and improve reliability through cross-checking and collective problem-solving, with applications from healthcare coordination to legal compliance.

## Key Properties

- Agents operate independently or coordinately, adapting strategies through collective learning
- Real-time inter-agent communication enables conflict avoidance and synergistic problem-solving
- Reduce hallucinations by 40-60% vs single agents through cross-verification
- Scalable architectures support dynamic agent addition/removal based on workload
- Enable mitigation of single-agent failure modes through redundancy and consensus

## Examples

- Healthcare coordination: multi-agent networks for patient care planning and collaborative medical diagnosis
- Legal compliance: specialized agents handling document processing, regulatory checking, and fraud detection

## Primary Sources

- Multiple authors (2024). *A Survey of Multi-AI Agent Collaboration: Theories, Technologies and Applications*. [https://dl.acm.org/doi/full/10.1145/3745238.3745531](https://dl.acm.org/doi/full/10.1145/3745238.3745531)
- Multiple authors (2025). *A multi-agent reinforcement learning framework for exploring dominant strategies*. [https://www.nature.com/articles/s41467-025-67178-6](https://www.nature.com/articles/s41467-025-67178-6)

## Related Papers

- [[scaling-agent-systems]]
- [[llamaagents-builder]]
- [[langchain-deep-agents-context-management]]
- [[llm-in-sandbox-agentic-intelligence]] — sandbox-based agentic intelligence is a building block for multi-agent systems where each agent uses code execution for tool access
- [[operational-data-ai-agents]] — multi-agent systems require high-quality operational data pipelines as their shared "senses"; data quality failures amplify across agents
- [[testing-agent-skills-with-evals]] — evaluating multi-agent systems requires the same four-category eval taxonomy (outcome, process, style, efficiency) applied at the system level
- [[agyn-multi-agent-software-engineering]] — Agyn's four-role organizational model (manager, researcher, engineer, reviewer) is a reference architecture for role-specialized multi-agent software engineering
- [[group-evolving-agents-gea-framework]] — GEA advances multi-agent systems to collective evolution: treating the group as the evolutionary unit, achieving 71% SWE-bench with zero additional inference cost
- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF provides the governance and interoperability standards that make heterogeneous multi-agent systems possible across vendor boundaries

## Navigation

- [[MOC-agentic-ai]] — Map of Content for the agentic AI topic area

## Related Concepts

- [[agentic-ai]]
- [[agent-loop-architecture]]
- [[mcp-model-context-protocol]]
- [[agentic-ai-memory-hierarchies]] — memory hierarchy designs enable multi-agent systems to share context efficiently across agents
- [[cohezion]] — the framework implementing multi-agent orchestration through compound engineering
- [[reinforcement-learning]] — multi-agent RL uses reinforcement signals to train coordination and competition across agent populations
- [[federated-learning]] — distributed coordination model parallels multi-agent architectures with decentralized training
- [[data-pipelines]] — multi-agent data flows follow pipeline patterns with specialized processing stages
- [[agents-as-exotic-vacuum-objects]] — multi-agent = EVO fission-fusion: one agent splits into parallel subagents and reunites

## Related Missions

- [[2026-03-05-night-council-validate-not-plan]] — directive redirecting the night council from planning to execution, producing validated FLUME diagnostics

## Related Lessons

- [[lesson-11-team-agent-efficiency]] — CRITICAL: coordination overhead exceeds benefits below task complexity threshold; single agents outperform teams for tasks under ~2 hours
- [[lesson-38-singleton-executor-for-sessions-new]] — singleton executor per session prevents resource leaks when multiple agent sessions run concurrently
- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams|Graph Densification via Parallel Agent Teams]] — 4 specialist agent teams (Alpha/Beta/Gamma/Delta) densified the vault graph in 15 min wall time, a concrete multi-agent coordination success

- [[2026-02-09-phase-5b-production-readiness-validation|Phase 5B Production Readiness Validation]] — validated the multi-agent coordination framework with 955+ tests and 4 independent reviewers converging on identical findings
- [[2026-02-20-session-59-autonomous-compound-engineering-foundation|Session 59: Autonomous Compound Engineering]] — parallel agent orchestration (Learning 128) demonstrates multi-agent coordination efficiency
- [[2026-02-20-session-59-compound-engineering-complete|Session 59: Compound Engineering Complete]] — specialist agents executing independent tasks in parallel demonstrate effective multi-agent coordination

## Related Assessments

- [[2026-03-04-vault-assessment-v3]] — third vault assessment identifying portfolio deadline as forcing function for memory architecture improvements

## Related Patterns & Projects

- [[role-based-multi-agent-coordination]] — pattern for assigning specialized roles (manager, researcher, engineer, reviewer) to agents in a coordinated team
- [[research-integration-todos]] — specialist teams (Alpha-Epsilon) demonstrate multi-agent coordination for research processing
- [[research-pipeline-mission-2026-02-26]] — five parallel teleport agent teams processing 900 rows as a concrete multi-agent deployment
- [[local-agent-orchestration-roadmap]] — roadmap for building a fully autonomous local multi-agent swarm on Strix Halo hardware

- [[lab-agent]] — the lab agent is a specialized agent within the multi-agent architecture focused on experimental pipeline execution

## Relevance to Cohezion

Cohezion's architecture is inherently multi-agent, with CompoundExecutor orchestrating task execution across specialized agents that communicate through the Cloud Vault MCP Server. The VaultExecutionLogger tracks cross-agent decision dependencies, while the Knowledge Graph's universe nodes and debate structures model multi-agent consensus-building and conflict resolution in complex reasoning tasks.

## Missions

- [[research-pipeline-2026-02-26]] — Five parallel agent teams (Alpha-Epsilon) processing 900 research rows
- COHEZION_CHARTER — Quadrature Nexus Orchestration coordinating expert streams

## Session References

- [[SESSION-43-PHASE-6-LAUNCH]] — 16-engineer team coordinating across 9 Phase 6 tasks with dependency DAG

## Agent Outputs

- CONNECTIVITY_GUIDE_PRIME — Connectivity Guide Prime (swarm architecture)
- CONNECTIVITY_MANAGEMENT_PRIME — Connectivity Management Prime
- high_complexity_targets — High Complexity Targets Analysis
- GAIA_LEVEL_3_STRATEGY — GAIA Level 3 Benchmarking Strategy (Research Squad swarm)
- implementation_plan_mycelium — Implementation Plan: Mycelium network
- implementation_plan_pulse — Implementation Plan: Pulse system
- implementation_plan_sensors — Implementation Plan: Sensor network
- SWARM_EVOLUTION_PROTOCOL — Swarm evolution protocol (v1.2)
- MULTIAGENT_ADVERSARIAL_REVIEW — Multiagent adversarial review: experience persistence
- PARTY_MODE_CONCENSUS — Party mode: midnight innovation consensus session
- omega_skill_crystallizer_design — Omega skill crystallizer design
- RETROSPECTIVE_CONNECTIVITY_SQUAD_S1 — Retrospective: connectivity squad sprint 1
- task_sensors — Task: sensor network implementation
- task_pulse — Task: pulse system implementation
- task_mycelium — Task: mycelium network implementation
- task_dataset — Task: dataset curation
- task_bluequbit — Task: BlueQubit quantum integration
- task_anthropic — Task: Anthropic integration

## Skills

- COMPOUND_ENGINEERING_PRIME — Agentic swarm orchestration
- CONSTITUTION_PRIME — Autonomous swarm governance
- controller_agent — LangGraph multi-agent orchestration
- democratic_debate — Multi-agent consensus building
- JOURNEY_TRACKING_PRIME — Debate workflow tracking
- LOCAL_OFFLOAD_PRIME — Context harness for task delegation
- MODEL_POOL_MANAGEMENT_PRIME — Model pool management for agents
- parallel_orchestration — Process-level concurrency for agents
- QUADRATURE_PRIME — Swarm consensus mechanism
- QUANTUM_LINK_PRIME — IPC for distributed agent swarms
- QUARTER_ON_A_STRING_PRIME — SLM-cortex orchestration pattern
- REDUNDANCY_SUPPRESSION_PRIME — Suppressing repetitive swarm behaviors
- resource_management — Swarm resource governance
- smart_routing — Multi-model task routing
- swarm_orchestration — Local SLM swarm coordination
- swarm_synthesis — Swarm consensus and outlier detection
- TEAM_ORCHESTRATION_PRIME — Multi-agent team planning
- THROTTLED_SCOUT_PRIME — Resource-aware swarm scouting

## Teleport Execution
- [[e5c2b46123b7|Agent Beta: AI/ML Research]] — parallel agent research execution (rows 251-400)
- [[bmad-analysis|BMAD Analysis]] — multi-agent analysis of BMAD framework patterns
- [[2026-02-20-autonomous-compound-engineering-spec|Autonomous Compound Engineering Spec]] — spec for parallel agent orchestration in compound engineering
