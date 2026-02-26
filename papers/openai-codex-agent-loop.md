---
title: Unrolling the Codex Agent Loop
date: 2026-02-07
tags: [openai-codex-agent-loop, surrealdb-agent-context-quick-reference, surrealdb-agent-context-visual-guide, surrealdb-agent-context-phase1-step3-query-testing, agentic-ai-memory-hierarchies]
connectivity: 0.27
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (4/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.5
conceptual_label: Balanced
similar_papers:
- runaway-stars-milky-way
- few-shot-prompting-agentic-coding
- 2026-02-09-unique-investment-opportunities-research
- axion-dark-matter-quantum-sensors
- woh-g64-dust-obscured-companion
dim_conceptual_depth: 0.5
source: https://openai.com/index/unrolling-the-codex-agent-loop/
dimensions:
  connectivity: 0.2
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.667
  algorithm_complexity: 0.0
  implementation_difficulty: 0.333
  interdisciplinary_transfer: 0.0
  impact_score: 0.322
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

## Related Concepts

- [[langchain-deep-agents-context-management]]
- [[scaling-agent-systems]]
- [[llamaagents-builder]]
- [[llm-training-methodology-changes]]
- [[testing-agent-skills-with-evals]]
- [[llm-in-sandbox-agentic-intelligence]]
- [[agentic-ai-memory-hierarchies]]
- [[few-shot-prompting-agentic-coding]] — few-shot examples in the Codex prompt assembly phase are a key mechanism for the 5x performance gains in agentic coding tasks
- [[karpathy-claude-code-skills]] — the Codex agent loop architecture powers the AI-driven coding workflow Karpathy describes shifting to 80% AI-generated code
- [[anthropic-mcp-apps-claude-integrations]] — MCP Apps extend the same MCP server list pattern in the Codex prompt assembly to interactive UI embedding
- [[gemini-cli-ai-employees-agent-factory]] — Agent Factory's orchestrator/worker model with parallel CLI execution is Google's implementation of the same agent loop architecture described here
- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF governs MCP, which is the tool integration layer in Codex's prompt assembly step; AAIF standardizes the protocol Codex depends on
- [[lesson-15-system-lockup-2026-01-27]] — the Codex inner loop's deterministic exit conditions (tool call resolved → output appended → next iteration or stop) prevent the unbounded accumulation that caused the system lockup; explicit loop termination is architectural in Codex, not optional
