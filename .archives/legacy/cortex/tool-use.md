---
title: "Tool Use"
date: 2026-02-19
tags: [concept, agentic-ai, agent-loop-architecture, mcp-model-context-protocol]
related_concepts: [mcp-model-context-protocol, agent-loop-architecture, agent-architecture, workflow-orchestration, agentic-ai]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 31
  synapse_out: 15
---
## Definition

Tool use is the capability of AI agents to invoke external functions, APIs, and services as part of their reasoning and execution cycles. Rather than relying solely on parametric knowledge baked into model weights, tool-using agents can read files, query databases, call web APIs, execute code, and interact with external systems — dramatically expanding the scope of tasks they can complete accurately.

The tool-use paradigm shifts agents from passive text generators to active participants in computation. A tool call is structured: the agent produces a function name and arguments, the host executes the function, and the result is returned to the agent's context for further reasoning. This cycle can repeat many times within a single session. The [[agent-loop-architecture]] formalizes this as the act phase of the observe-reason-act cycle.

The [[mcp-model-context-protocol]] standardizes how tools are defined, discovered, and called across heterogeneous systems. Rather than each agent needing custom integrations for each tool, MCP provides a universal interface: tools declare their schemas, agents discover them at startup, and calls flow through a standard transport (stdio or HTTP). This eliminates the N×M integration problem and makes tool ecosystems composable.

## Key Properties

- **Schema-driven**: Tools declare input/output schemas; agents use them to form correct calls
- **Stateless invocation**: Each tool call is independent; state must be managed by the agent
- **Latency-aware**: Tool calls add latency; agents should batch and parallelize where possible
- **Error handling**: Tools can fail; agents must handle errors gracefully without aborting
- **Security boundary**: Tool permissions must be scoped; unconstrained tool use is a safety risk

## Related Papers

- [[2026-02-09-phase1-completion]]
- [[2026-02-09-phase1-results]]
- [[anthropic-mcp-apps-claude-integrations]]
- [[openai-codex-agent-loop]]

## Related Concepts

- [[mcp-model-context-protocol]] — the standard protocol for tool definition and invocation
- [[agent-loop-architecture]] — the cycle in which tool calls are the “act” phase
- [[agent-architecture]] — the structural context within which tool use occurs
- [[workflow-orchestration]] — how tool calls are sequenced across multi-step tasks
- [[multi-agent-systems]] — tool registries shared across multiple agents enable team-level tool use
- [[cloud-vault-mcp]] — Cohezion's primary tool provider (30+ tools)
- [[Autonomous-Context-Hooks-Guide]] — hooks that orchestrate vault search and write tool calls as part of the agent lifecycle

## Related Lessons

- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] — tool integration via MCP requires end-to-end tests; unit tests miss the protocol negotiation layer that makes tools actually callable
- [[lesson-18-mock-live-services-in-tests]] — when testing tool-use code, mock external tool calls at the client level for reliable unit tests
- [[2026-02-22-daily-cli-tool-update-via-systemd-timer|Daily CLI Update Timer]] — CLI tool updates ensure agents always have current tool versions available
- [[2026-02-09-session-43-mcp-setup|Session 43: MCP Setup]] — MCP server setup enables agents to use vault tools; the foundation for tool-based vault access

## Relevance to Cohezion

Tool use is the operational core of Cohezion's agent architecture. Every agent interaction with the vault, SurrealDB, Ollama, or Google Sheets happens through MCP tool calls. The [[cloud-vault-mcp]] server exposes 30+ tools across six categories: vault operations (read/write/search notes), compound operations (log decisions, extract patterns), SurrealDB queries, Sheets bridge, Teleport task management, and health checks. The [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] lesson captures the key operational insight: tool availability must be verified end-to-end, not just unit-tested.

## Skills

- compound_prompt — Chaining skill outputs as inputs
