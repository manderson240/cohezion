# Specification: ARC-AGI-3: Frontier Agentic Intelligence Challenge

## Overview
This track targets the newly released ARC-AGI-3 benchmark (March 2026), focusing on agentic adaptive efficiency in abstract, turn-based environments. Unlike its predecessors, ARC-AGI-3 requires exploration, goal inference, and planning without explicit instructions.

## Core Objectives
1.  **Agentic Exploration**: Implement agents capable of building internal models of environment dynamics via interaction.
2.  **Recursive Reasoning**: Integrate LoopViT-inspired weight-tied recurrence for iterative chain-of-thought.
3.  **Adaptive Efficiency**: Minimize actions taken to achieve goals in novel environments.

## SOTA Alignment
- **LoopViT Architecture**: Use 18M weight-tied blocks for efficient reasoning depth.
- **Dynamic Exit**: Implement entropy-based inference halting.
- **FLUME Latent Vectors**: Map interactive states into 2048D manifold for trajectory prediction.

## Hardware & Quotas
- **Local Compute**: Ollama (Qwen3-Coder:30b) for code synthesis.
- **Cloud Fallback**: Gemini 2.5 Pro for complex strategy planning.
