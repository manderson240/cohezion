---
title: LLM-in-Sandbox Elicits General Agentic Intelligence
date: 2026-02-07
tags: 
connectivity: 0.13
cross_domain: 0.5
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (2/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 0.50
conceptual_label: Balanced
similar_papers: ["axion-dark-matter-quantum-sensors", "anthropic-principle-fine-tuning", "ai-anomaly-detection-hubble-archive", "sentinel-1-ice-sheets", "sunspot-ar4366-x-class-flares"]
dim_conceptual_depth: 0.5
source: https://arxiv.org/abs/2601.16206
dimensions:
  connectivity: 0.100
  cross_domain: 0
  completion: 100
  temporal: 0.500
  recency: 0.700
  conceptual_depth: 0.000

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
