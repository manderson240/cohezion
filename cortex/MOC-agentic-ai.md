---
title: "MOC — Agentic AI"
date: 2026-03-04
tags: [moc, navigation, agentic-ai]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 11
  synapse_out: 35
---

# Map of Content — Agentic AI

## Overview

Agentic AI is the foundation of the Cohezion framework: autonomous systems that perceive, reason, plan, and act through tool use and multi-agent coordination. This map covers agent design patterns, loop architectures, context window management, orchestration strategies, and the MCP protocol that wires it all together. It is the single most interconnected topic area in the vault.

## Core Concepts

- [[agentic-ai]] — Umbrella definition covering autonomous perception-reasoning-action loops
- [[agent-architecture]] — Structural design of agents: memory, planning, tool invocation layers
- [[agent-loop-architecture]] — The observe-think-act cycle that drives each agent turn
- [[multi-agent-systems]] — Coordinating multiple specialized agents toward shared goals
- [[agent-context]] — How agents acquire, compress, and prioritize context within token limits
- [[tool-use]] — Agent invocation of external tools via structured function calls
- [[workflow-orchestration]] — Sequencing and parallelizing agent tasks across pipelines
- [[mcp-model-context-protocol]] — Anthropic's open protocol for standardized tool and context access
- [[context-management]] — Strategies for fitting relevant knowledge into finite context windows
- [[prompt-engineering]] — Crafting instructions that reliably steer agent behavior
- [[cybernetics]] — The original science of feedback, control, and governance in complex systems; foundational theory for agent loops

## Key Decisions

- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation]] — Hot/warm/cold model tiers for cost-efficient agent orchestration
- [[2026-02-10-canvas-driven-compound-engineering]] — Canvas-based visual orchestration of multi-agent pipelines

## Patterns

- [[role-based-multi-agent-coordination]] — Assigning specialist roles (researcher, reviewer, implementer) to agents
- [[pattern-compound-engineering]] — Layered approach to building agentic workflows from composable primitives
- [[agent-logs-vault-schema]] — Schema for capturing agent execution context as vault notes with structured frontmatter linking sessions to decisions and lessons
- [[implementation_plan|Cohezion Crystal Protocol]] — Antigravity agent's energy-based model integration: energy descent loop for deterministic, verified agentic reasoning

## Agent Execution Records

- [[Agents/_index|Agents Directory]] — 427 auto-generated execution traces from Antigravity and future agent runtimes

## Research Papers

- [[scaling-agent-systems]] — Google Research on scaling laws and coordination bottlenecks in multi-agent systems
- [[openai-codex-agent-loop]] — Inside the Codex agent loop: prompt caching, sandboxing, and iterative refinement
- [[agentic-ai-foundation-mcp-linux-foundation]] — MCP and agent standards moving under Linux Foundation governance
- [[langchain-deep-agents-context-management]] — LangChain's approach to deep agent context and memory hierarchies
- [[group-evolving-agents-gea-framework]] — Self-improving agent groups that evolve through competitive selection
- [[agentic-ai-memory-hierarchies]] — Memory tiers (working, episodic, semantic) for long-lived agents
- [[llm-in-sandbox-agentic-intelligence]] — Sandboxed execution environments for safe agentic code generation
- [[testing-agent-skills-with-evals]] — Evaluation frameworks for measuring agent skill reliability
- [[anthropic-disempowerment-patterns]] — Patterns where agents inadvertently disempower human oversight
- [[gemini-cli-ai-employees-agent-factory]] — Gemini CLI as a factory for producing task-specific AI employees

## Related Concepts

- [[agentic-system-failure-taxonomy]] — Classification of agent failure modes: hallucination, tool misuse, context loss, etc.
- [[ai-safety-alignment]] — Ensuring agent behavior stays within intended boundaries
- [[token-efficiency]] — Minimizing token spend while preserving agent effectiveness
- [[non-blocking-observability]] — Async telemetry that does not interrupt the agent loop
- [[agent-journey-tracking]] — Recording and replaying full agent decision traces
- [[experience-feedback-loop]] — Closed-loop learning where agent outcomes improve future behavior
- [[adversarial-review]] — Challenger agents that stress-test plans and implementations
- [[cloud-vault-mcp]] — The MCP server that gives agents programmatic vault access
- [[troubleshooting-mcp-infrastructure]] — Diagnosing and resolving MCP server failures that block agent access
- [[session-retrospective]] — Structured reflection at the end of each agent session
- [[prompt-optimization-hypotheses]] — Pilot study of 98 sessions: context inheritance and explicit task definition as success enablers; vague prompts as primary failure root cause
- [[extraction-pipeline-spec]] — 12D extraction pipeline bridging vault SurrealDB graph to FLUME VAE training data using unified physics model

## Start Here

- **New to this topic?** Start with [[agentic-ai]] for the foundational definition, then [[agent-loop-architecture]] for the core loop
- **Looking for patterns?** See [[role-based-multi-agent-coordination]] for practical multi-agent design
- **Recent work:** [[agentic-ai-foundation-mcp-linux-foundation]] covers the latest MCP standardization under Linux Foundation

## Related Maps

- [[MOC-machine-learning]] — The ML foundations that underpin agent intelligence
- [[MOC-vault-architecture]] — The knowledge graph infrastructure agents read from and write to
