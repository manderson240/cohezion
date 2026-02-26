---
title: "{{title}}"
date: "2026-02-26"
tags: [pattern]
---

## Problem

## Solution

## Code Example

## When to Use

## Related Decisions

- [[2026-02-14-adversarial-multi-agent-review-protocol|Decision: Adversarial Multi-Agent Review Protocol]] — foundational example: assigns correctness-reviewer, test-quality-reviewer, and architecture-reviewer roles to parallel agents
- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation|Decision: Agent Orchestration Design — 3-Tier Hot/Warm/Cold Model Rotation]] — role-based model selection (routing agent → execution agent tiers)
- [[2026-02-10-compound-linking-plan-adversarial-review|Decision: Adversarial Review Result — Compound Node Linking Plan Rejected]] — example of 4-role adversarial review (cost-critic, QA-expert, infrastructure-skeptic, timeline-skeptic)

## Related Patterns

- [[mini-adversarial-review-checkpoints]] — checkpoint pattern that uses role-based agents (correctness, test quality, architecture) inline during implementation
- [[3-tier-hotwarmcold-model-rotation]] — tier-based model assignment is a form of role-based coordination at the infrastructure layer
