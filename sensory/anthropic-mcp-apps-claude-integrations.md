---
title: Anthropic Embeds Slack, Figma, and Asana Inside Claude via MCP Apps
date: 2026-02-07
tags: [mcp, anthropic, tool-integration, ai-agents, workplace-ai]
connectivity: 0.2
cross_domain: 0.62
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (3/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.5
conceptual_label: Balanced
similar_papers:
- agentic-ai-foundation-mcp-linux-foundation
- openai-codex-agent-loop
- gemini-cli-ai-employees-agent-factory
- llamaagents-builder
dim_conceptual_depth: 0.5
source: https://venturebeat.com/infrastructure/anthropic-embeds-slack-figma-and-asana-inside-claude-turning-ai-chat-into-a
dimensions:
  connectivity: 0.15
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.0
  algorithm_complexity: 0.0
  implementation_difficulty: 0.0
  interdisciplinary_transfer: 0.0
  impact_score: 0.24
aspect: knower
neural:
  activation: 0.73
  stage: growing
  synapse_in: 8
  synapse_out: 10
---
# Anthropic MCP Apps - Claude as Workplace Command Center

## Summary

Anthropic launched MCP Apps, a new extension to the Model Context Protocol that enables interactive app interfaces within Claude. Nine productivity tools are now embedded directly inside Claude chat: Asana, Canva, Figma, Slack, and others.

## Key Findings

- **MCP Apps** extends the Model Context Protocol to deliver interactive UI within AI products
- Users can draft and preview Slack messages, edit Figma diagrams, update Asana timelines, and manipulate analytics dashboards without leaving Claude
- Available to Claude Pro, Max, Team, and Enterprise subscribers
- Claude acts as the integration layer ("glue") between multiple workplace tools

## Relevance to Cohezion

Demonstrates the trajectory of AI assistants becoming orchestration hubs for tool ecosystems. The MCP Apps pattern is directly relevant to how Cohezion agents could integrate with external services and provide unified interfaces for complex workflows., [[mcp-model-context-protocol]], [[tool-use]], [[api-design]]

## Related Papers

- [[llamaagents-builder]] — both demonstrate natural-language-to-agent workflows; MCP Apps through interactive UI embedding, LlamaAgents Builder through workflow code generation
- [[openai-codex-agent-loop]] — the Codex agent loop architecture is the backend pattern that MCP Apps UI embedding builds on top of
- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF's governance of MCP creates the vendor-neutral standard that MCP Apps products depend on; AAIF is the organizational infrastructure for the MCP ecosystem
- [[gemini-cli-ai-employees-agent-factory]] — Agent Factory is Google's parallel architecture to MCP Apps: both embed workplace tooling into AI assistants, approaching the same goal from competing ecosystems

## Related Concepts

- [[mcp-model-context-protocol]] — MCP Apps extends MCP with interactive UI capabilities
- [[tool-use]] — embedding tool interfaces directly in AI chat
- [[api-design]] — MCP as the API standard for agent-tool integration
- [[agentic-ai]] — Claude evolving from chat to orchestration hub
- [[cloud-vault-mcp]] — Cohezion's MCP server in the same ecosystem
- [[multi-agent-systems]] — MCP Apps enables multi-tool orchestration through a single agent
