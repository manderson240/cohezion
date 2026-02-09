---
title: "TongGeometry: Neuro-Symbolic Olympiad Geometry via Guided Tree Search"
date: 2026-02-07
tags: [AI-architecture, neuro-symbolic, geometry, theorem-proving, tree-search]
source: "https://www.nature.com/articles/s42256-025-01164-x"
---

# TongGeometry: Olympiad Geometry with Guided Tree Search

## Summary

Published in Nature Machine Intelligence, TongGeometry is a neuro-symbolic system that both discovers and proves olympiad-level geometry theorems using guided tree search, establishing a repository of 6.7 billion geometry theorems.

## Key Findings

- 6.7 billion theorems requiring auxiliary constructions, including 4.1 billion with geometric symmetry
- Three discoveries selected for regional mathematical olympiads (China national qualifying exam, top US civil olympiad)
- Combines neural network guidance with symbolic tree search
- Operates within same computational budget as existing state-of-the-art systems but produces far more results

## Relevance to Cohezion

Neuro-symbolic approach combining neural guidance with structured search directly relevant to `lab_agent.py` reasoning architecture. Tree search with neural pruning is a powerful pattern for agent problem-solving., [[agentic-ai]]
