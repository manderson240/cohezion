---
title: "MOC — Safety & Alignment"
date: 2026-03-04
tags: [moc, navigation, ai-safety, alignment]
aspect: knower
neural:
  activation: 1.0
  stage: growing
  synapse_in: 8
  synapse_out: 29
---

# Map of Content — Safety & Alignment

## Overview

Safety and alignment are the guardrails that ensure agentic AI systems behave in accordance with human values and do not cause unintended harm. In the Cohezion framework, this manifests as adversarial review protocols that catch flaws before execution, concept validation that prevents bad knowledge from propagating through the graph, and operational safeguards like verification-before-destructive-operations. This topic bridges the academic alignment research captured in vault papers with the practical safety patterns built into Cohezion's daily workflows.

## Core Concepts

- [[ai-safety-alignment]] — The field addressing how to ensure AI systems behave in accordance with human values
- [[ai-safety]] — Domain encompassing the technical and governance challenges of safe AI deployment
- [[alignment]] — Ensuring AI system objectives and behaviors match human intent
- [[adversarial-review]] — Multi-agent review protocol that challenges plans and implementations before execution
- [[concept-validation]] — Ensuring knowledge nodes are correct before they propagate through the graph
- [[concept-testing]] — Validating concept accuracy to prevent compounding errors in agent context
- [[prompt-engineering]] — Crafting AI inputs to elicit desired responses; includes safety-relevant techniques like chain-of-thought
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] — Mandatory knowledge extraction before any irreversible operation

## Key Decisions

- [[2026-02-14-adversarial-multi-agent-review-protocol]] — Accepted: multi-agent review catches critical bugs that single-agent review misses
- [[2026-02-14-3-tier-adversarial-review-protocol-for-code-quality]] — Three-tier review (haiku/sonnet/opus) finding progressively deeper issues
- [[2026-02-10-compound-linking-plan-adversarial-review]] — Adversarial review rejecting a flawed plan, preventing massive rework
- [[2026-02-19-anthropic-job-alignment-benchmarks-and-training]] — Alignment benchmarks and training strategies informed by Anthropic research
- [[2026-02-10-claude-log-mining-architecture]] — Log mining for model alignment patterns and token waste detection

## Patterns

- [[mini-adversarial-review-checkpoints]] — Lightweight adversarial checks at implementation milestones
- [[pattern-compound-engineering]] — The compound loop itself is a safety pattern: extract and preserve before destroying
- [[session-retrospective-notes]] — Capturing safety-relevant decisions and near-misses before context is lost

## Research Papers

- [[anthropic-disempowerment-patterns]] — Disempowerment patterns observed in real-world AI usage (Anthropic research)
- [[emoticons-llm-silent-failures]] — Emoticons causing silent failures in LLM coding responses
- [[cisa-chatgpt-data-leak]] — CISA chief uploading sensitive files to public ChatGPT; data governance failure
- [[llm-in-sandbox-agentic-intelligence]] — Sandbox-based execution as a safety boundary for agentic AI
- [[testing-agent-skills-with-evals]] — Systematic evaluation of agent skills to catch quality regressions
- [[anthropic-principle-fine-tuning]] — Cosmological fine-tuning and the anthropic principle (tangential but related by name)

## Lessons Learned

- [[lesson-adversarial-review-before-execution]] — Adversarial review before execution prevents wasted effort and catches critical flaws
- [[lesson-03-critical]] — Critical operations require explicit verification before proceeding; unverified destructive ops cause data loss
- [[lesson-04-surgery-lesson]] — Surgical edits only; scope creep in changes creates unintended regressions

## Experiments

- [[2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop]] — Recursive adversarial self-review as an autonomous improvement mechanism

## Start Here

- **New to this topic?** Start with [[ai-safety-alignment]]
- **Looking for patterns?** See [[mini-adversarial-review-checkpoints]]
- **Recent work:** [[adversarial-review]]

## Related Maps

- [[MOC-compound-engineering]]
- [[MOC-platform-infrastructure]]
- [[MOC-astrophysics]]
