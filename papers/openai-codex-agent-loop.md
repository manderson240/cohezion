---
title: "Unrolling the Codex Agent Loop"
date: 2026-02-07
tags: [ai-architecture, agent-design, openai, codex]
source: "https://openai.com/index/unrolling-the-codex-agent-loop/"
---

# Unrolling the Codex Agent Loop

## Summary

OpenAI published a technical deep-dive on the core agent loop architecture powering Codex, their AI coding agent. The article describes the orchestration between user, model, and tools within a single conversation turn.

## Key Findings

- **Prompt Assembly**: Each turn begins by assembling a prompt with instructions (system message), tools (MCP servers list), and input (text, images, files).
- **Inner Loop**: Some events trigger tool calls, others produce reasoning outputs. Both are appended to the prompt for further LLM iterations in an "inner loop."
- **Quadratic to Linear**: LLM inference is quadratic in prompt size sent to the Responses API. Prompt caching is the key optimization that makes inference performance linear instead of quadratic.
- **CLI Design Patterns**: OpenAI shared their CLI architecture and lessons as transferable patterns for anyone building agents on the Responses API.

## Relevance to Cohezion

Directly applicable to [[lab_agent.py]] agent loop design. The inner/outer loop pattern, prompt caching strategy, and MCP tool integration approach are all relevant architectural patterns for Cohezion's agentic workflows., [[mcp-model-context-protocol]], [[agent-architecture]], [[tool-use]]
