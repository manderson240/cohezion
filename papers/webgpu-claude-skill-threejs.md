---
title: WebGPU Claude Skill for Three.js Development
date: 2026-02-07
tags: [webgpu-claude-skill-threejs, claude-code-community-skills, anthropic-mcp-apps-claude-integrations, karpathy-claude-code-skills, _claude-code-metrics-2026-02-14]
connectivity: 0.07
cross_domain: 0.62
completion: 1.0
temporal: 1.0
recency: 1.0
connectivity_summary: ☆☆☆☆☆ (1/5 links)
completion_summary: 3/3 sections (100%)
conceptual_depth: 0.0
conceptual_label: Pure Applied
similar_papers:
- openai-applied-compute-startup
- beyond-the-quantum-pilot-wave-theory
- mcl1-myc-cancer-metabolism
- amorphous-materials-3d-atomic-structure
- llamaagents-builder
dim_conceptual_depth: 0.0
source: https://github.com/dgreenheck/webgpu-claude-skill
dimensions:
  connectivity: 0.05
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.667
  algorithm_complexity: 0.3
  implementation_difficulty: 0.7
  interdisciplinary_transfer: 0.5
  impact_score: 0.082
---
## Abstract

A comprehensive Claude Code skill created by dgreenheck provides documentation, templates, and best practices for developing WebGPU applications with Three.js. The skill covers core GPU concepts, materials, compute shaders, post-processing effects, WGSL integration, and device loss handling with practical code examples.

## Key Findings

- Installable directly as Claude Code skill from GitHub repository with standard skill installation path
- Includes extensive documentation on WebGPU core concepts and Three.js GPU integration patterns
- Provides TSL (Three Shading Language) material examples with animated shader effects and real-time rendering
- Features compute shader templates and post-processing pipeline examples for advanced GPU programming
- Demonstrates practical skill/plugin architecture for extending Claude Code with specialized development domain knowledge

## Source

https://github.com/dgreenheck/webgpu-claude-skill

# WebGPU Claude Skill

## Summary

A Claude Code skill by dgreenheck that provides documentation and templates for developing WebGPU applications with Three.js. Covers core concepts, materials, compute shaders, post-processing, WGSL integration, and device loss handling.

## Key Features

- Installable as a Claude Code skill: `git clone https://github.com/dgreenheck/webgpu-claude-skill ~/.claude/skills/webgpu`
- Documentation on WebGPU core concepts and Three.js integration
- TSL (Three Shading Language) material examples with animated effects
- Compute shader and post-processing templates
- WGSL integration guides

## Relevance to Cohezion

Demonstrates the skill/plugin pattern for Claude Code agents. Could be used as a template for creating Cohezion-specific Claude skills, or directly used for WebGPU-based visualization of simulation outputs from `lab_agent.py`., [[prompt-engineering]]

## Related Concepts

- [[anthropic-mcp-apps-claude-integrations]]
- [[anthropic-view-universe-nyas]]
- [[claude-code-community-skills]] — the WebGPU skill is an example of the specialized domain skills collected in the 36-skill community initiative
- [[karpathy-claude-code-skills]] — the WebGPU skill embodies the Karpathy-style workflow: domain experts package their knowledge as AI-assistable Claude Code skills
- [[claude-code-swiftui-skill-patterns]] — SwiftUI and WebGPU skills are parallel examples of the same pattern: wrapping platform-specific expert knowledge as Claude Code skills
