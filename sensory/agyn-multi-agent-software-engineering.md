---
title: Agyn — Multi-Agent Software Engineering Platform
date: 2026-02-26
tags: [multi-agent, software-engineering, coding-agents, organizational-ai, open-source]
similar_papers:
- scaling-agent-systems
- group-evolving-agents-gea-framework
- openai-codex-agent-loop
- llm-in-sandbox-agentic-intelligence
source: https://search.app/wug46
aspect: knower
neural:
  activation: 0.9
  stage: mature
  synapse_in: 16
  synapse_out: 19
---

## Summary
Agyn is an open-source multi-agent platform modeling software engineering as a team-based organizational process. Four specialized agents — manager, researcher, engineer, reviewer — each with isolated sandboxes, role-specific tools, and separate LLM configurations. The manager coordinates dynamically based on intermediate outcomes rather than fixed pipelines.

## Key Concepts
- Role-based agent specialization with isolated execution environments
- Dynamic coordination vs fixed pipeline orchestration
- Organizational metaphor for software engineering AI
- Four-role architecture: manager, researcher, engineer, reviewer

## COHEZION Integration
- **lab_agent.py**: Direct architectural pattern for COHEZION's own multi-agent orchestration — Agyn's four-role model maps well to COHEZION's research/decision/implementation/validation phases
- **TODO**: Adopt Agyn's dynamic manager pattern for COHEZION's agent orchestration layer — replace sequential pipelines with outcome-driven coordination
- **TODO**: Extract pattern to vault/patterns/ as "Role-Based Multi-Agent Coordination"
- **compound engineering**: This is a compound engineering pattern — agent teams that improve with each session via captured learnings

## Related Papers

- [[scaling-agent-systems]] — Agyn's dynamic manager coordination directly addresses the centralized vs decentralized orchestration trade-offs quantified in the scaling science paper
- [[group-evolving-agents-gea-framework]] — GEA takes Agyn's multi-role model further by enabling the agent group itself to evolve through collective experience sharing
- [[llm-in-sandbox-agentic-intelligence]] — Agyn's isolated execution sandbox per agent applies the same sandbox-based intelligence elicitation pattern
- [[openai-codex-agent-loop]] — Agyn's manager agent implements an inner/outer loop pattern structurally analogous to the Codex agent loop
- [[testing-agent-skills-with-evals]] — Agyn's reviewer agent role mirrors the eval-driven "measure → improve" loop for agent quality

## Related Concepts

- [[multi-agent-systems]] — Agyn exemplifies multi-agent systems with role specialization and dynamic coordination
- [[compound-engineering]] — Agyn's captured learnings across sessions embody compound engineering principles applied to agent teams

## Engineering Grounding

- [[lesson-11-team-agent-efficiency]] — the observed "5 parallel agents + sequential-deps leader = 20 files in ~15 min" directly validates Agyn's four-role model. The leader (manager) handles sequential dependencies; workers parallelize. This is a measured real-world data point for the Agyn architecture pattern.
- [[multi-session-compound-engineering-workflow]] — Agyn's isolated sandbox per agent maps directly onto the git-worktree-per-session pattern: both achieve task isolation by giving each agent its own filesystem state while sharing the upstream repository
- [[lesson-adversarial-review-before-execution]] — Agyn's reviewer role is a formalization of the adversarial review principle; dedicated reviewer agents provide the structured skeptical review that the lesson shows prevents 90% wasted effort


## Additional Linkages

- [[agent-architecture]] — four-role architecture as a design pattern for agent systems
- [[tool-use]] — role-specific tool access per agent
- [[context-management]] — manager coordinates based on intermediate outcomes, requiring context passing between roles

- [[gemini-cli-ai-employees-agent-factory]] — Agent Factory's orchestrator+worker model uses the same organizational metaphor; Agyn is the open-source implementation of the pattern Google demonstrates
- [[data-engineering-ai-era-2026]] — Agyn's organizational model requires the agent-native data infrastructure described here to feed each specialized role
- [[python-314-free-threaded-gil-removal]] — Agyn's parallel isolated agents currently use subprocess isolation; Python 3.14 free threading could enable in-process parallelism
- [[nvidia-nemotron-3-nano-nemo-gym]] — Nemotron 3 Nano's cost/capability balance makes it suitable as the LLM backbone for Agyn's parallel worker agents
- [[agentic-ai-foundation-mcp-linux-foundation]] — AAIF's MCP standard enables Agyn's agents to use interoperable tool interfaces across vendors
- [[research-integration-todos]] — Agyn's four-role dynamic coordination pattern is referenced as a HIGH PRIORITY agent architecture TODO for COHEZION adoption