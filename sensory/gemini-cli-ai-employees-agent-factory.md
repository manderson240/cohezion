---
title: Build AI Employees with Gemini CLI - Agent Factory
date: 2026-02-26
tags: [ai, gemini, cli, agents, workflow-automation, compound-engineering]
similar_papers:
- openai-codex-agent-loop
- agyn-multi-agent-software-engineering
- anthropic-mcp-apps-claude-integrations
- scaling-agent-systems
source: https://cloud.google.com/blog/topics/developers-practitioners/agent-factory-recap-build-an-ai-workforce-with-gemini-3
aspect: knower
neural:
  activation: 0.88
  stage: mature
  synapse_in: 5
  synapse_out: 18
---

## Summary
Google's Agent Factory demo shows building "AI employees" using Gemini CLI + Agent Development Kit (ADK): treat prompts as Standard Operating Procedures in markdown files, run parallel agents via Python scripts, and use filesystem-as-state for transparent orchestration.

## Key Abstractions
Key pattern: Gemini 3 Pro for high-level reasoning/orchestration, Gemini 2.5 Flash for worker-bee execution tasks. SOP-in-markdown approach (just like COHEZION's SKILL.md system) creates reusable agent instructions. Parallel CLI execution via Python subprocess enables multi-city/multi-task concurrent workloads without complex infrastructure.

## COHEZION Integration
- `lab_agent.py`: Direct parallel — COHEZION's SKILL.md pattern is architecturally identical to Gemini CLI's agent skills system. Consider cross-compatibility
- Teleportation system: COHEZION's filesystem-as-state teleport tasks mirror exactly the pattern described here
- COHEZION could expose its compound engineering methodology as a downloadable skills pack compatible with both Claude Code and Gemini CLI

## TODO
- [ ] Create COHEZION Skills Pack compatible with both Claude Code and Gemini CLI SKILL.md format
- [ ] Benchmark parallel agent execution via subprocess vs COHEZION's teleport system

## Related Papers

- [[openai-codex-agent-loop]] — the Codex agent loop is the analogous OpenAI implementation of the AI coding agent architecture that Gemini CLI's Agent Factory demonstrates
- [[karpathy-claude-code-skills]] — Karpathy's 80% AI-driven workflow is operationalized by exactly this kind of "AI employee" factory pattern using SOP-in-markdown files
- [[few-shot-prompting-agentic-coding]] — SOP markdown files serve as structured few-shot examples that guide worker-bee Gemini Flash agents on execution tasks
- [[agyn-multi-agent-software-engineering]] — Agyn's manager/researcher/engineer/reviewer roles map closely to the orchestrator/worker model described in Agent Factory
- [[anthropic-mcp-apps-claude-integrations]] — MCP Apps embeds workplace tools in Claude the same way Agent Factory embeds them in Gemini; parallel architectures from competing ecosystems

## Related Concepts

- [[compound-engineering]] — SOP-in-markdown is a direct implementation of compound engineering: reusable agent instructions that compound value across repeated tasks
- [[multi-agent-systems]] — parallel subprocess agents for multi-city/multi-task workloads demonstrate horizontal scaling of multi-agent systems
- [[adversarial-review]] — Agent Factory deployment should include adversarial review of SOP instructions before production use
- [[cohezion]] — Cohezion's SKILL.md system is architecturally identical to Gemini CLI's SOP-in-markdown pattern
- [[token-efficiency-patterns]] — the reasoning/execution model split (Pro for orchestration, Flash for workers) is a token efficiency pattern


## Additional Linkages

- [[tool-use]] — filesystem-as-state for transparent tool orchestration
- [[agent-architecture]] — orchestrator+worker model with reasoning/execution split
- [[prompt-engineering]] — SOP-in-markdown as structured prompt engineering
- [[mcp-model-context-protocol]] — MCP as the protocol layer for tool integration across agent ecosystems

- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF's governance of MCP and A2A creates the interoperability layer that allows Agent Factory-built agents to communicate with MCP-native Claude agents
- [[claude-code-community-skills]] — the 36 Claude Code community skills and Gemini CLI's SOP-in-markdown are structurally identical patterns from competing ecosystems, both converging on "instructions-as-files" as the agent skills paradigm
- [[python-314-free-threaded-gil-removal]] — Agent Factory's parallel subprocess execution via Python could migrate to true threading with Python 3.14's GIL removal, reducing overhead
- [[scaling-agent-systems]] — Agent Factory's orchestrator+worker pattern directly addresses the scaling trade-offs: centralized orchestrator coordinates, workers parallelize