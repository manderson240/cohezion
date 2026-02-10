---
title: "Humanity's Last Exam - Expert-Level AI Benchmark"
date: 2026-02-07
tags: [AI-evaluation, benchmarks, LLM, expert-knowledge]
connectivity: 0.07
cross_domain: 0.50
completion: 0.67
temporal: 1.00
recency: 1.00
connectivity_summary: ☆☆☆☆☆ (1/5 links)
completion_summary: 2/3 sections (66%)
source: "https://www.nature.com/articles/s41586-025-09962-4"
---

# Humanity's Last Exam (HLE) Benchmark

## Summary

Published in Nature, HLE is a multi-modal benchmark of 2,500 expert-level questions across dozens of subjects designed to push beyond current AI evaluation limits, where state-of-the-art LLMs achieve over 90% on existing benchmarks.

## Key Findings

- 2,500 questions across mathematics, humanities, and natural sciences
- Developed globally by subject-matter experts with known, unambiguous, verifiable solutions
- ~14% of questions require comprehending both text and image (multimodal)
- 24% multiple-choice, remainder exact-match
- State-of-the-art LLMs demonstrate low accuracy and poor calibration
- Highlights marked gap between current LLM capabilities and expert human frontier

## Relevance to Cohezion

Directly relevant to `lab_agent.py` for designing evaluation frameworks. HLE's approach to multi-domain expert-level testing could inform how Cohezion agents are benchmarked across diverse knowledge domains., [[ai-agents]]
