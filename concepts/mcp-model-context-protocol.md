---
title: "Mcp Model Context Protocol"
date: 2026-02-07
tags: [concept, agentic-ai, agent-loop-architecture, multi-agent-systems]
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

## Relevance to Cohezion

MCP is the foundational protocol enabling Cohezion's entire architecture—the Cloud Vault MCP Server exposes VaultOps, CompoundOps, and ObsidianOps through bidirectional MCP communication. CompoundExecutor coordinates with agents through MCP-defined interfaces, ContextEngineeringInfrastructure's tool registry leverages MCP for standardized tool integration, and the framework's ability to connect heterogeneous data sources depends entirely on MCP's universal interface abstraction.

## Decisions & Experiments
- 📋 [[2026-02-09-12d-graph-refined-plan]] - 12D Graph System - Refined Implementation Plan
