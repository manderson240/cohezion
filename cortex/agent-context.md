---
title: "Agent Context"
date: 2026-02-19
tags: [concept, context-management, agentic-ai, agent-architecture]
related_concepts: [context-management, agent-architecture, agent-loop-architecture, token-efficiency, semantic-search]
aspect: knower
neural:
  activation: 0.92
  stage: mature
  synapse_in: 16
  synapse_out: 44
---
## Definition

Agent context is the information payload an AI agent has access to at a given moment in its execution cycle. It encompasses the system prompt, task instructions, conversation history, retrieved documents, tool outputs, and injected memories. Context quality is the primary determinant of agent output quality — well-constructed context reduces hallucination, prevents repeated mistakes, and grounds reasoning in relevant prior work.

Effective agent context management involves three challenges: what to include (relevance), how much to include (token budget), and when to refresh (session boundaries). Context is not automatically inherited between sessions; agents must explicitly load prior decisions, patterns, and lessons at startup (see [[lesson-19-session-awareness-protocol]]).

In Cohezion, the [[cloud-vault-mcp]] server's `find_relevant_context` and `pull_session_context` tools handle context assembly — surfacing vault decisions, experiment results, and patterns that are semantically relevant to the current task. The [[semantic-search]] layer ensures only high-signal context is injected, staying within [[token-efficiency]] constraints.

## Key Properties

- **Session-bounded**: Context resets at session boundaries; must be explicitly reloaded
- **Token-constrained**: Context window limits require careful prioritization of high-signal content
- **Multi-source**: Combines system instructions, conversation history, retrieved vault notes, and tool results
- **Dynamic**: Grows as tools execute and new information becomes available during a session
- **Semantic retrieval**: Relevant context is found via embedding similarity, not keyword matching

## Related Papers

- [[langchain-deep-agents-context-management]] — LangChain's three-tier context strategy (offload/truncate/summarize) is a production implementation of agent context management for long-horizon tasks
- [[agentic-ai-memory-hierarchies]] — hardware and software memory hierarchy designs that underpin agent context persistence across sessions
- [[openai-codex-agent-loop]] — OpenAI's agent loop architecture demonstrates context management at the tool-use level
- [[2026-02-11-phase1-step1-schema-complete]]
- [[2026-02-11-surrealdb-agent-context-schema-design]]
- [[ai_for_good]]
- [[benchmarking]]
- [[conclusion]]
- [[data_engineering]]
- [[dl_primer]]
- [[dnn_architectures]]
- [[efficient_ai]]
- [[frameworks]]
- [[frontiers]]
- [[hw_acceleration]]
- [[introduction]]
- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]]
- [[lesson-11-team-agent-efficiency]]
- [[lesson-31-operation-specific-modulation]]
- [[ml_systems]]
- [[ondevice_learning]]
- [[ops]]
- [[optimizations]]
- [[phase1-mcp-tool-reference]]
- [[privacy_security]]
- [[responsible_ai]]
- [[robust_ai]]
- [[sustainable_ai]]
- [[training]]
- [[workflow]]

## Related Concepts

- [[context-management]] — the broader discipline of optimizing information payloads for AI systems
- [[agent-architecture]] — the structural design within which agent context operates
- [[semantic-search]] — the retrieval mechanism for finding relevant context from vault
- [[token-efficiency]] — the constraint that forces disciplined context selection
- [[cloud-vault-mcp]] — the MCP server providing context assembly tools
- [[Autonomous-Context-Hooks-Guide]] — autonomous hooks that auto-load vault context before agent prompts and save results after

## Related Lessons

- [[lesson-29-batch-cache-two-phase]] — batch cache two-phase pattern reduces redundant computation in context retrieval pipelines
- [[lesson-19-session-awareness-protocol]] — agents must explicitly load prior context at session start; context is not inherited automatically
- [[lesson-21-runtime-json-pollution]] — debug output on stdout corrupts JSON-based context pipelines; always use stderr for logs

- [[safe-persistent-storage-lifecycle]] — agent context data must follow safe storage lifecycle policies to prevent accidental loss
- [[surrealdb-sync-pattern]] — the sync pattern governs how agent context data is batched and written to SurrealDB

## Related Projects

- [[2026-03-03-vault-as-platform-memory-recommendations|Vault as Platform Memory Recommendations]] — strategic assessment of vault-as-memory architecture with 6 prioritized recommendations

## Relevance to Cohezion

Cohezion's context management is implemented through the Cloud Vault MCP's `vault_find_relevant_context` and `vault_pull_session_context` tools. At session start, agents load vault decisions, patterns, and experiments relevant to their current task — grounding execution in accumulated institutional knowledge. The SurrealDB agent context schema (see [[surrealdb]]) stores structured context about agent sessions, enabling retrospective analysis and context injection in future sessions via the [[experience-feedback-loop]].

## Agent Outputs

- **Walkthrough: Recovering from Initial Memory Loss** — `Agents/Antigravity/30480d59-daec-4ea2-a981-eb404e8f78c5/walkthrough.md`
