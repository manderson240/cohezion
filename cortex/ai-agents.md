---
title: "Ai Agents"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.91
  stage: growing
  synapse_in: 7
  synapse_out: 21
---
## Definition

AI agents are autonomous software systems that use large language models (LLMs) to perceive their environment, make decisions, and take actions to achieve goals. Unlike simple chatbots that respond to single prompts, agents operate in loops -- observing state, reasoning about next steps, executing tool calls, and evaluating results -- often across multiple turns without human intervention. Agents combine LLM reasoning with tool use (file systems, APIs, code execution, databases) to accomplish complex tasks.

The key distinction between an AI agent and a prompted LLM is the **agent loop**: the ability to take an action, observe the result, and decide what to do next iteratively until a goal is met or a stopping condition is reached.

## Key Properties

- **Tool use**: Agents invoke external tools (shell commands, APIs, file operations) to act on the world.
- **Memory**: Effective agents maintain context across sessions via persistent memory, session state, or knowledge graphs.
- **Planning**: Agents decompose complex tasks into sub-tasks and execute them in dependency order.
- **Self-correction**: Agents detect errors in their own output and retry or adjust their approach.
- **Delegation**: Multi-agent systems can spawn sub-agents for parallel work, though single agents often outperform teams for tasks under ~2 hours.

## Examples

- Claude Code operating as a coding agent: reading files, writing code, running tests, fixing errors in a loop
- A research agent that searches the web, reads papers, and synthesizes findings into a vault note
- A CI/CD agent that monitors build failures, diagnoses root causes, and submits fix PRs

## Related Papers

- [[2026-02-09-12d-graph-refined-plan]]
- [[2026-02-09-phase1-completion]]
- [[2026-02-09-phase1-results]]
- [[emu3-multimodal-next-token-prediction]]
- [[grok4-ai-benchmarks]]
- [[humanitys-last-exam-benchmark]]
- [[llm-in-sandbox-agentic-intelligence]]
- [[mistral-open-source-ai-strategy]]
- [[openai-applied-compute-startup]]
- [[operational-data-ai-agents]]
- [[testing-agent-skills-with-evals]]
- [[theorem-ai-formal-verification]]

## Related Concepts

- [[agentic-ai]] -- the broader paradigm of AI systems that act autonomously
- [[agent-architecture]] -- structural patterns for building agent systems
- [[agent-loop-architecture]] -- the observe-reason-act loop at the core of agents
- [[multi-agent-systems]] -- coordination patterns when multiple agents collaborate
- [[agent-context]] -- how agents manage and consume contextual information
- [[tool-use]] -- the mechanism agents use to interact with external systems

## Related Lessons

- [[lesson-37-experience-guided-execution-works-new]] -- AI agents that load prior session context outperform cold-start agents; memory is a first-class agent capability
- [[lesson-38-singleton-executor-for-sessions-new]] -- AI agents sharing a singleton executor per session prevent resource exhaustion in concurrent deployments
- [[lesson-11-team-agent-efficiency]] -- empirical finding: single agents outperform teams for tasks under ~2 hours estimated duration

## Relevance to Cohezion

AI agents are the primary consumers of the Cohezion vault. The framework is built around the premise that agents perform better when they have access to structured, verified knowledge -- concept notes, lessons learned, decision records -- rather than relying solely on their training data. Every layer of Cohezion (the vault, MCP servers, the knowledge graph, session management) exists to make agents more effective.
