---
title: "Emu3: Multimodal Learning via Next-Token Prediction"
date: 2026-02-07
tags: [AI-architecture, multimodal, next-token-prediction, vision-language]
source: "https://www.nature.com/articles/s41586-025-10041-x"
---

# Emu3: Multimodal Next-Token Prediction

## Summary

Published in Nature, Emu3 is a family of multimodal models trained solely with next-token prediction that matches the performance of specialized task-specific models across perception and generation, without requiring diffusion or compositional architectures.

## Key Findings

- Unified next-token prediction approach across text, images, and video
- Matches flagship systems for vision-language tasks without diffusion models
- Demonstrates coherent, high-fidelity video generation
- Supports interleaved vision-language generation
- Enables vision-language-action modeling for robotic manipulation
- Addresses fundamental challenge of learning from and generating across multiple modalities

## Relevance to Cohezion

Unified multimodal architecture directly relevant to `lab_agent.py` design. The next-token prediction paradigm as a universal learning objective across modalities could inform how Cohezion agents handle diverse input/output types., [[ai-agents]]
