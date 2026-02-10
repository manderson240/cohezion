---
title: Unrolling the Codex Agent Loop
date: 2026-02-07
tags: 
connectivity: 0.27
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (4/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.50
conceptual_label: Balanced
similar_papers: ["runaway-stars-milky-way", "few-shot-prompting-agentic-coding", "2026-02-09-unique-investment-opportunities-research", "axion-dark-matter-quantum-sensors", "woh-g64-dust-obscured-companion"]
dim_conceptual_depth: 0.5
source: https://openai.com/index/unrolling-the-codex-agent-loop/
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
