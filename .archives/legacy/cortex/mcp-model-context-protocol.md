---
title: "Mcp Model Context Protocol"
date: 2026-02-07
tags: [concept, agentic-ai, agent-loop-architecture, multi-agent-systems]
related_concepts: [tool-use, agentic-ai, agent-loop-architecture, multi-agent-systems, cloud-vault-mcp]
aspect: knower
neural:
  activation: 0.71
  stage: mature
  synapse_in: 57
  synapse_out: 26
---

## Definition

An open-source standard released by Anthropic in November 2024 providing a universal interface for connecting AI systems to external tools and data sources. Similar to USB-C for AI connectivity, MCP standardizes the N*M integration problem, with SDKs in Python, TypeScript, C#, and Java. Donated to the Agentic AI Foundation in 2025 for community governance.

## Key Properties

- Universal interface eliminates custom connectors for each tool/system
- Bidirectional communication enabling AI clients to read files, execute functions, and handle contextual prompts
- Adopted by OpenAI, Google DeepMind, VS Code, Replit, Sourcegraph
- Security considerations include prompt injection, tool permission exfiltration, and lookalike tool attacks
- Pre-built servers for Google Drive, Slack, GitHub, Postgres, Puppeteer

## Examples

- VS Code integration: Claude accessing codebase context through MCP servers for file reading and code suggestions
- GitHub + Slack integration: AI agent pulling repo changes, analyzing code quality, and posting notifications

## Primary Sources

- Anthropic (2024). *Introducing the Model Context Protocol*. [https://www.anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol)
- MCP Contributors (2025). *Model Context Protocol Specification*. [https://modelcontextprotocol.io/specification/2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- Anthropic (2025). *Anthropic Donates MCP to Agentic AI Foundation*. [https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)

## Related Papers

- [[anthropic-mcp-apps-claude-integrations]]
- [[langchain-deep-agents-context-management]]

## Related Concepts

- [[agentic-ai]]
- [[agent-loop-architecture]]
- [[multi-agent-systems]]

## Navigation

- [[MOC-platform-infrastructure]] — Map of Content for platform infrastructure including MCP, SurrealDB, and CI/CD

## Relevance to Cohezion

MCP is the foundational protocol enabling Cohezion's entire architecture—the Cloud Vault MCP Server exposes VaultOps, CompoundOps, and ObsidianOps through bidirectional MCP communication. CompoundExecutor coordinates with agents through MCP-defined interfaces, ContextEngineeringInfrastructure's tool registry leverages MCP for standardized tool integration, and the framework's ability to connect heterogeneous data sources depends entirely on MCP's universal interface abstraction.

- [[kyutai-project]] — the Kyutai project's MCP server was built using the MCP protocol standard

## Decisions

- [[2026-03-06-adopt-meridian-concierge-agent-over-mcp-infrastructure-prd]] — adopt Meridian concierge agent over MCP infrastructure PRD; intelligence layer scales better than transport layer

## Related Lessons

- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] — MCP servers must be tested end-to-end with a real client connection; unit tests miss transport and protocol negotiation failures

## Decisions & Experiments
- 📋 [[2026-02-09-12d-graph-refined-plan]] - 12D Graph System - Refined Implementation Plan
- 📋 [[2026-02-09-rust-flume-python313-incompatibility|Rust FLUME Incompatibility]] — planned MCP server wrapping the Rust FLUME binary for tool-based encoding access

## Daily References

- [[SESSION-63-FINAL-SUMMARY-2026-02-15]]
- [[SESSION-62-PHASE-3-COMPLETE-FINAL-SUMMARY]]
- [[SESSION-61-COMPLETE-SUMMARY]]
- [[SESSION-60-COMPLETION-SUMMARY]]
- [[SESSION-57-COMPLETION-SUMMARY]]
- [[SESSION-2026-02-10-WORK-SUMMARY]]
- [[PHASE-2-FINAL-COMPLETION-VERIFIED-2026-02-14]]
- [[PHASE-2-DEPLOYMENT-COMPLETION-2026-02-14]]
- [[2026-03-04-anthropic-portfolio-night-session]]
- [[2026-02-14-wave-1-delivery-complete]]

## Agent Outputs

- mcp_audit — MCP server audit: Cohezion ecosystem
- mcp_optimization_plan — MCP optimization plan
- skill_audit — Skill audit
- skill_audit_results — Skill audit results
- web_portal_plan — Web portal plan for Cohezion dashboard

## Skills

- CONNECTIVITY_MANAGEMENT_PRIME — Multi-protocol service discovery
- enterprise_ai_server_mastery — MCP server deployment
- gmail_mcp — Gmail MCP bridge for AI agents
- MEMORY_MCP_PRIME — Memory via MCP
- OBSIDIAN_MCP_INTEGRATION_PRIME — Obsidian MCP server integration
- SURREALDB_MCP_PRIME — SurrealDB MCP protocol

## Research & Benchmarks
- [[kyutai-api-specification|Kyutai API Specification]] — API docs for Kyutai voice AI models used via MCP
- [[kyutai-mcp-server-architecture|Kyutai MCP Server Architecture]] — MCP server architecture design for Kyutai
- [[kyutai-mcp-server-implementation|Kyutai MCP Server Implementation]] — Phase 1 implementation of the Kyutai MCP server
- [[kyutai-obsidian-plugin-architecture|Kyutai Obsidian Plugin Architecture]] — Obsidian plugin architecture calling MCP
- [[README|Benchmarking Guide]] — performance benchmarking for MCP server and plugin
