---
title: LLM-in-Sandbox Elicits General Agentic Intelligence
date: 2026-02-07
tags: [agentic-ai, sandbox-execution, reinforcement-learning, code-generation, generalization]
connectivity: 0.13
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (2/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.5
conceptual_label: Balanced
similar_papers:
- openai-codex-agent-loop
- langchain-deep-agents-context-management
- scaling-agent-systems
- few-shot-prompting-agentic-coding
dim_conceptual_depth: 0.5
source: https://arxiv.org/abs/2601.16206
dimensions:
  connectivity: 0.1
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.0
  algorithm_complexity: 0.0
  implementation_difficulty: 0.333
  interdisciplinary_transfer: 0.0
  impact_score: 0.158
aspect: knower
neural:
  activation: 0.638
  stage: growing
  cluster: papers
---
# LLM-in-Sandbox: General Agentic Intelligence via Code Sandbox

## Summary

This paper introduces LLM-in-Sandbox, a framework enabling LLMs to explore within a code sandbox (virtual computer) to elicit general intelligence in non-code domains. The approach demonstrates that strong LLMs can generalize sandbox capabilities to diverse tasks without additional training.

## Key Findings

- LLMs can leverage code sandboxes for non-code tasks: accessing external resources, managing long contexts via file systems, executing formatting scripts
- LLM-in-Sandbox-RL uses only non-agentic data to train models for sandbox exploration
- Achieves robust generalization across mathematics, physics, chemistry, biomedicine, long-context understanding, and instruction following
- No additional task-specific training needed for strong LLMs

## Relevance to Cohezion

Directly relevant to `lab_agent.py` - demonstrates that giving AI agents a sandbox environment with code execution capabilities enables emergent agentic behaviors across diverse domains. This pattern could inform Cohezion's agent architecture for tool use and environment interaction., [[agentic-ai]], [[ai-agents]]

## Related Papers

- [[ai-anomaly-detection-hubble-archive]]
- [[langchain-deep-agents-context-management]] — LangChain's Deep Agents use similar filesystem offloading and context strategies as the LLM-in-Sandbox framework's file system access pattern
- [[few-shot-prompting-agentic-coding]] — few-shot prompting is the primary technique through which LLM-in-Sandbox generalizes to non-code domains
- [[emoticons-llm-silent-failures]] — tokenization edge cases that cause silent coding failures are amplified in sandbox environments where LLMs autonomously execute code
- [[agyn-multi-agent-software-engineering]] — Agyn's isolated execution sandbox per agent is a direct production application of the LLM-in-Sandbox elicitation framework
- [[nvidia-nemotron-3-nano-nemo-gym]] — NeMo Gym's standardized RL environments are the next-generation evolution of the sandbox pattern: structured training environments built on the same code-execution-as-environment insight

## Related Concepts

- [[agentic-ai]] — sandbox as an environment for emergent agentic behavior
- [[agent-architecture]] — sandbox-based architecture pattern for tool use
- [[agent-loop-architecture]] — the sandbox provides the execution environment for each iteration of the agent loop
- [[ai-safety-alignment]] — sandbox containment is an alignment strategy: bounding agent actions within safe execution boundaries
- [[tool-use]] — code execution as the universal tool interface
- [[context-management]] — filesystem access extends context beyond window limits
- [[machine-learning]] — RL training without task-specific agentic data
- [[compound-engineering]] — sandbox isolation maps to Cohezion's worktree-per-session pattern

## Engineering Implementations

- [[lesson-git-worktrees-multi-session-isolation]] — git worktrees are a production implementation of the sandbox isolation principle: each agent session receives an isolated filesystem (worktree) with full write access, sharing only the underlying git object store. This is the LLM-in-Sandbox pattern applied to multi-session compound engineering.
- [[multi-session-compound-engineering-workflow]] — the full workflow built on worktree sandboxes as the isolation foundation for multi-agent coordination
- [[async-singleton-lock-isolation]] — singleton lock isolation is the in-process equivalent: per-event-loop primitives prevent cross-context state contamination, just as sandbox filesystems prevent cross-session contamination
