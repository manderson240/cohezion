---
date: 2026-06-04
source: github
tags: [paper, research, gaia, lemonade]
---
# Research on GitHub: AMD GAIA & Lemonade Server Community Patterns

## Abstract
This page synthesizes the usage, configuration, and API specifications for AMD GAIA and the Lemonade Server based on public codebase analysis.

## Key Findings
- **Framework Structure**: `amd-gaia` provides base agent modules (`gaia.agents.base`) and conversation modules (`gaia.agents.chat`).
- **Lemonade Backend**: Lemonade serves as the unified runtime, managing multiple models across NPU (FLM), iGPU (ROCWMMA), and CPU (AVX) layers.
- **Default Paths**: Configuration defaults to `config.json` inside the platform's cache directory (e.g., `~/.cache/lemonade/config.json`) and handles ports (default 13305).
- **Custom Tools**: Tools are declared cleanly using the `@tool` decorator, enabling automatic schema synthesis for LLMs.

## References
- [[2026-06-04-local-inference-validation]]
- [[2026-06-04-gaia-adapter-swarms]]
